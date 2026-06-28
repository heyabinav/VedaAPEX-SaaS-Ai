import { z } from "zod";

const assetTypeSchema = z.enum(["IMAGE", "VIDEO"]);
const operationSchema = z.enum(["BACKGROUND_REMOVAL", "WATERMARK_REMOVAL", "ENHANCEMENT"]);

export const createMediaUploadUrlSchema = z.object({
  assetType: assetTypeSchema,
  mimeType: z.string().min(3).max(120),
  extension: z.string().min(1).max(10),
  title: z.string().min(2).max(120).optional(),
});

export const uploadMediaAssetSchema = z.object({
  assetType: assetTypeSchema,
  title: z.string().min(2).max(120).optional(),
});

export const registerMediaAssetSchema = z.object({
  assetType: assetTypeSchema,
  storageKey: z.string().min(5),
  mimeType: z.string().min(3).max(120),
  sizeBytes: z.coerce.number().int().positive(),
  title: z.string().min(2).max(120).optional(),
});

export const createMediaJobSchema = z.object({
  assetId: z.string().cuid(),
  operation: operationSchema,
  options: z.record(z.any()).optional(),
});

export const mediaJobParamSchema = z.object({
  jobId: z.string().cuid(),
});
