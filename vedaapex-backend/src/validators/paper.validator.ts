import { z } from "zod";

const classLevelSchema = z.coerce.number().int().min(9).max(12);

const tagsSchema = z
  .union([z.array(z.string().min(1)), z.string().min(1)])
  .transform((value) => (Array.isArray(value) ? value : value.split(",").map((tag) => tag.trim())))
  .transform((value) => value.filter(Boolean));

export const paperQuerySchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(12),
  search: z.string().optional(),
  subject: z.string().optional(),
  board: z.string().optional(),
  year: z.coerce.number().int().optional(),
  classLevel: classLevelSchema.optional(),
  featured: z
    .union([z.string(), z.boolean()])
    .optional()
    .transform((value) => {
      if (typeof value === "boolean") {
        return value;
      }

      return value === undefined ? undefined : value === "true";
    }),
});

export const createPaperSchema = z.object({
  title: z.string().min(5).max(180),
  classLevel: classLevelSchema,
  subject: z.string().min(2).max(100),
  board: z.string().min(2).max(100),
  year: z.coerce.number().int().min(2000).max(new Date().getFullYear() + 1),
  language: z.string().min(2).max(20).default("en"),
  tags: tagsSchema.default([]),
  status: z.enum(["DRAFT", "PROCESSING", "PUBLISHED", "ARCHIVED"]).default("PROCESSING"),
});

const paperManifestItemSchema = z.object({
  title: z.string().min(5).max(180),
  classLevel: classLevelSchema,
  subject: z.string().min(2).max(100),
  board: z.string().min(2).max(100),
  year: z.coerce.number().int().min(2000).max(new Date().getFullYear() + 1),
  language: z.string().min(2).max(20).default("en"),
  tags: z.array(z.string()).default([]),
  pdfUrl: z.string().url(),
  thumbnailUrl: z.string().url().optional(),
  storageKey: z.string().optional(),
  pageCount: z.coerce.number().int().positive().optional(),
  summary: z.string().max(5000).optional(),
  ocrText: z.string().max(50000).optional(),
  status: z.enum(["DRAFT", "PROCESSING", "PUBLISHED", "ARCHIVED"]).default("PUBLISHED"),
});

export const bulkImportPapersSchema = z.object({
  papers: z.array(paperManifestItemSchema).min(1).max(500),
});

export const updatePaperSchema = createPaperSchema.partial().extend({
  isFeatured: z.boolean().optional(),
});

export const idParamSchema = z.object({
  paperId: z.string().cuid(),
});
