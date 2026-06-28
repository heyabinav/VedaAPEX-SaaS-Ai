import { MediaAssetType, MediaJobType } from "@prisma/client";

import { env } from "../config/env";
import { storageService } from "./storage.service";

type HttpProcessorResponse = {
  provider?: string;
  providerJobId?: string;
  outputUrl?: string;
  outputBase64?: string;
  contentType?: string;
};

type ProcessorInput = {
  assetType: MediaAssetType;
  jobType: MediaJobType;
  storageKey: string;
  mimeType: string;
  options?: Record<string, unknown>;
};

type ProcessorResult = {
  provider: string;
  providerJobId?: string;
  outputUrl?: string;
  outputStorageKey?: string;
};

const resolveSourceUrl = async (storageKey: string) => storageService.getSignedDownloadUrl(storageKey);

const runPassthroughProcessor = async (input: ProcessorInput): Promise<ProcessorResult> => {
  const outputUrl = await resolveSourceUrl(input.storageKey);

  return {
    provider: "passthrough",
    outputUrl,
    outputStorageKey: input.storageKey,
  };
};

const runHttpProcessor = async (input: ProcessorInput): Promise<ProcessorResult> => {
  if (!env.MEDIA_PROCESSOR_BASE_URL) {
    throw new Error("MEDIA_PROCESSOR_BASE_URL is required for HTTP media processing mode.");
  }

  const response = await fetch(`${env.MEDIA_PROCESSOR_BASE_URL.replace(/\/$/, "")}/process`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...(env.MEDIA_PROCESSOR_API_KEY ? { authorization: `Bearer ${env.MEDIA_PROCESSOR_API_KEY}` } : {}),
    },
    body: JSON.stringify({
      sourceUrl: await resolveSourceUrl(input.storageKey),
      assetType: input.assetType,
      jobType: input.jobType,
      mimeType: input.mimeType,
      options: input.options ?? {},
    }),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Media processor failed: ${response.status} ${message}`);
  }

  const data = (await response.json()) as HttpProcessorResponse;

  if (data.outputBase64) {
    const extension = input.storageKey.split(".").pop() ?? "bin";
    const outputStorageKey = storageService.buildProcessedMediaStorageKey(input.assetType, input.jobType, extension);
    await storageService.uploadBuffer(outputStorageKey, Buffer.from(data.outputBase64, "base64"), data.contentType ?? input.mimeType);

    return {
      provider: data.provider ?? "http-processor",
      providerJobId: data.providerJobId,
      outputStorageKey,
      outputUrl: await storageService.getSignedDownloadUrl(outputStorageKey),
    };
  }

  if (!data.outputUrl) {
    throw new Error("Media processor did not return an output URL or base64 payload.");
  }

  return {
    provider: data.provider ?? "http-processor",
    providerJobId: data.providerJobId,
    outputUrl: data.outputUrl,
  };
};

export const mediaProcessorService = {
  async process(input: ProcessorInput): Promise<ProcessorResult> {
    if (env.MEDIA_PROCESSOR_MODE === "http") {
      return runHttpProcessor(input);
    }

    return runPassthroughProcessor(input);
  },
};
