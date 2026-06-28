import { MediaAssetType, MediaJobStatus, MediaJobType, UsageMetricType, type Prisma } from "@prisma/client";

import { prisma } from "../config/prisma";
import { env } from "../config/env";
import { ApiError } from "../utils/api-error";
import { toOptionalJsonValue } from "../utils/prisma-json";
import { activityService } from "./activity.service";
import { storageService } from "./storage.service";
import { enqueueMediaProcessingJob } from "../queues/media-processing.queue";
import { mediaProcessorService } from "./media-processor.service";
import { usageService } from "./usage.service";

type AssetType = "IMAGE" | "VIDEO";
type OperationType = "BACKGROUND_REMOVAL" | "WATERMARK_REMOVAL" | "ENHANCEMENT";

const getAllowedMimes = (assetType: AssetType) => (assetType === "IMAGE" ? env.imageAllowedMime : env.videoAllowedMime);

const assertAllowedMime = (assetType: AssetType, mimeType: string) => {
  if (!getAllowedMimes(assetType).includes(mimeType)) {
    throw new ApiError(400, `Unsupported ${assetType.toLowerCase()} mime type: ${mimeType}`);
  }
};

const resolveJobType = (assetType: AssetType, operation: OperationType): MediaJobType => {
  if (assetType === "IMAGE" && operation === "BACKGROUND_REMOVAL") {
    return MediaJobType.IMAGE_BACKGROUND_REMOVAL;
  }

  if (assetType === "VIDEO" && operation === "BACKGROUND_REMOVAL") {
    return MediaJobType.VIDEO_BACKGROUND_REMOVAL;
  }

  if (assetType === "IMAGE" && operation === "WATERMARK_REMOVAL") {
    return MediaJobType.IMAGE_WATERMARK_REMOVAL;
  }

  if (assetType === "VIDEO" && operation === "WATERMARK_REMOVAL") {
    return MediaJobType.VIDEO_WATERMARK_REMOVAL;
  }

  if (assetType === "IMAGE" && operation === "ENHANCEMENT") {
    return MediaJobType.IMAGE_ENHANCEMENT;
  }

  if (assetType === "VIDEO" && operation === "ENHANCEMENT") {
    return MediaJobType.VIDEO_ENHANCEMENT;
  }

  throw new ApiError(400, `Unsupported media operation ${operation} for asset type ${assetType}.`);
};

const resolveUsageMetric = (operation: OperationType) => {
  if (operation === "BACKGROUND_REMOVAL") {
    return UsageMetricType.MEDIA_BACKGROUND_REMOVAL;
  }

  if (operation === "WATERMARK_REMOVAL") {
    return UsageMetricType.MEDIA_WATERMARK_REMOVAL;
  }

  return UsageMetricType.MEDIA_ENHANCEMENT;
};

const withResolvedAssetUrl = async <
  T extends { storageKey: string; processedStorageKey: string | null; originalUrl: string; processedUrl: string | null },
>(
  asset: T,
) => ({
  ...asset,
  originalAccessUrl: asset.originalUrl.startsWith("http") ? asset.originalUrl : await storageService.getSignedDownloadUrl(asset.storageKey),
  processedAccessUrl:
    asset.processedStorageKey ? await storageService.getSignedDownloadUrl(asset.processedStorageKey) : asset.processedUrl?.startsWith("http") ? asset.processedUrl : null,
});

const withResolvedJobUrls = async <
  T extends {
    outputStorageKey: string | null;
    outputUrl: string | null;
    asset: {
      storageKey: string;
      processedStorageKey: string | null;
      originalUrl: string;
      processedUrl: string | null;
    };
  },
>(
  job: T,
) => ({
  ...job,
  outputAccessUrl: job.outputStorageKey ? await storageService.getSignedDownloadUrl(job.outputStorageKey) : job.outputUrl?.startsWith("http") ? job.outputUrl : null,
  asset: await withResolvedAssetUrl(job.asset),
});

export const mediaService = {
  async createUploadUrl(input: { assetType: AssetType; mimeType: string; extension: string }) {
    assertAllowedMime(input.assetType, input.mimeType);

    const storageKey = storageService.buildMediaStorageKey(input.assetType, input.extension);
    const uploadUrl = await storageService.getSignedUploadUrl(storageKey, input.mimeType);

    return {
      storageKey,
      uploadUrl,
    };
  },

  async registerUploadedAsset(userId: string, input: { assetType: AssetType; storageKey: string; mimeType: string; sizeBytes: number; title?: string }) {
    assertAllowedMime(input.assetType, input.mimeType);

    const existingAsset = await prisma.mediaAsset.findUnique({
      where: {
        storageKey: input.storageKey,
      },
    });

    if (existingAsset && existingAsset.userId !== userId) {
      throw new ApiError(403, "This uploaded asset belongs to another user.");
    }

    const asset = existingAsset
      ? await prisma.mediaAsset.update({
          where: {
            storageKey: input.storageKey,
          },
          data: {
            title: input.title,
            mimeType: input.mimeType,
            sizeBytes: input.sizeBytes,
          },
        })
      : await prisma.mediaAsset.create({
          data: {
            userId,
            type: input.assetType as MediaAssetType,
            title: input.title,
            originalUrl: `storage://${input.storageKey}`,
            storageKey: input.storageKey,
            mimeType: input.mimeType,
            sizeBytes: input.sizeBytes,
          },
        });

    return withResolvedAssetUrl(asset);
  },

  async uploadDirectAsset(userId: string, input: { assetType: AssetType; title?: string }, file?: Express.Multer.File) {
    if (!file) {
      throw new ApiError(400, "Media file is required.");
    }

    assertAllowedMime(input.assetType, file.mimetype);

    const extension = file.originalname.split(".").pop() ?? (input.assetType === "IMAGE" ? "png" : "mp4");
    const storageKey = storageService.buildMediaStorageKey(input.assetType, extension);
    await storageService.uploadBuffer(storageKey, file.buffer, file.mimetype);

    const asset = await prisma.mediaAsset.create({
      data: {
        userId,
        type: input.assetType as MediaAssetType,
        title: input.title,
        originalUrl: `storage://${storageKey}`,
        storageKey,
        mimeType: file.mimetype,
        sizeBytes: file.size,
      },
    });

    await activityService.log({
      userId,
      action: "media.asset.uploaded",
      entityType: "MediaAsset",
      entityId: asset.id,
      metadata: {
        assetType: input.assetType,
      },
    });

    return withResolvedAssetUrl(asset);
  },

  async createProcessingJob(userId: string, input: { assetId: string; operation: OperationType; options?: Record<string, unknown> }) {
    const asset = await prisma.mediaAsset.findFirst({
      where: {
        id: input.assetId,
        userId,
      },
    });

    if (!asset) {
      throw new ApiError(404, "Media asset not found.");
    }

    const jobType = resolveJobType(asset.type as AssetType, input.operation);

    const job = await prisma.mediaJob.create({
      data: {
        userId,
        assetId: asset.id,
        type: jobType,
        options: toOptionalJsonValue(input.options),
      },
      include: {
        asset: true,
      },
    });

    await enqueueMediaProcessingJob(job.id);

    await activityService.log({
      userId,
      action: "media.job.created",
      entityType: "MediaJob",
      entityId: job.id,
      metadata: {
        operation: input.operation,
        assetType: asset.type,
      },
    });

    return withResolvedJobUrls(job);
  },

  async listAssets(userId: string) {
    const assets = await prisma.mediaAsset.findMany({
      where: { userId },
      orderBy: { createdAt: "desc" },
    });

    return Promise.all(assets.map((asset) => withResolvedAssetUrl(asset)));
  },

  async listJobs(userId: string) {
    const jobs = await prisma.mediaJob.findMany({
      where: { userId },
      include: {
        asset: true,
      },
      orderBy: { createdAt: "desc" },
    });

    return Promise.all(jobs.map((job) => withResolvedJobUrls(job)));
  },

  async getJob(userId: string, jobId: string) {
    const job = await prisma.mediaJob.findFirst({
      where: {
        id: jobId,
        userId,
      },
      include: {
        asset: true,
      },
    });

    if (!job) {
      throw new ApiError(404, "Media job not found.");
    }

    return withResolvedJobUrls(job);
  },

  async processJob(jobId: string) {
    const job = await prisma.mediaJob.findUnique({
      where: { id: jobId },
      include: {
        asset: true,
      },
    });

    if (!job) {
      throw new ApiError(404, "Media job not found.");
    }

    await prisma.mediaJob.update({
      where: { id: jobId },
      data: {
        status: MediaJobStatus.PROCESSING,
        progress: 20,
      },
    });

    try {
      const result = await mediaProcessorService.process({
        assetType: job.asset.type,
        jobType: job.type,
        storageKey: job.asset.storageKey,
        mimeType: job.asset.mimeType,
        options: (job.options as Prisma.JsonObject | null | undefined) as Record<string, unknown> | undefined,
      });

      const updatedJob = await prisma.mediaJob.update({
        where: { id: jobId },
        data: {
          status: MediaJobStatus.COMPLETED,
          provider: result.provider,
          providerJobId: result.providerJobId,
          progress: 100,
          outputUrl: result.outputUrl ?? (result.outputStorageKey ? `storage://${result.outputStorageKey}` : null),
          outputStorageKey: result.outputStorageKey,
          completedAt: new Date(),
        },
        include: {
          asset: true,
        },
      });

      await prisma.mediaAsset.update({
        where: { id: job.assetId },
        data: {
          processedUrl: result.outputUrl ?? (result.outputStorageKey ? `storage://${result.outputStorageKey}` : null),
          processedStorageKey: result.outputStorageKey,
        },
      });

      const operation = updatedJob.type.includes("BACKGROUND")
        ? "BACKGROUND_REMOVAL"
        : updatedJob.type.includes("WATERMARK")
          ? "WATERMARK_REMOVAL"
          : "ENHANCEMENT";

      await usageService.track({
        userId: updatedJob.userId,
        metricType: resolveUsageMetric(operation),
        provider: result.provider,
        metadata: {
          mediaJobId: updatedJob.id,
          mediaAssetId: updatedJob.assetId,
          jobType: updatedJob.type,
        },
      });

      return updatedJob;
    } catch (error) {
      await prisma.mediaJob.update({
        where: { id: jobId },
        data: {
          status: MediaJobStatus.FAILED,
          progress: 100,
          errorMessage: (error as Error).message,
        },
      });

      throw error;
    }
  },
};
