import { AnalysisStatus, PaperStatus, Prisma } from "@prisma/client";
import { nanoid } from "nanoid";

import { prisma } from "../config/prisma";
import { ApiError } from "../utils/api-error";
import { buildPagination } from "../utils/pagination";
import { activityService } from "./activity.service";
import { cacheService } from "./cache.service";
import { enqueuePaperAnalysisJob } from "../queues/paper-processing.queue";
import { pdfService } from "./pdf.service";
import { storageService } from "./storage.service";

type ListPaperInput = {
  page: number;
  limit: number;
  search?: string;
  subject?: string;
  board?: string;
  year?: number;
  classLevel?: number;
  featured?: boolean;
};

type CreatePaperInput = {
  title: string;
  classLevel: number;
  subject: string;
  board: string;
  year: number;
  language: string;
  tags: string[];
  status: "DRAFT" | "PROCESSING" | "PUBLISHED" | "ARCHIVED";
};

type PaperManifestInput = CreatePaperInput & {
  pdfUrl: string;
  thumbnailUrl?: string;
  storageKey?: string;
  pageCount?: number;
  summary?: string;
  ocrText?: string;
};

const buildPaperWhere = (query: ListPaperInput): Prisma.PaperWhereInput => ({
  status: PaperStatus.PUBLISHED,
  subject: query.subject ? { equals: query.subject, mode: "insensitive" } : undefined,
  board: query.board ? { equals: query.board, mode: "insensitive" } : undefined,
  year: query.year,
  classLevel: query.classLevel,
  isFeatured: query.featured,
  OR: query.search
    ? [
        { title: { contains: query.search, mode: "insensitive" } },
        { subject: { contains: query.search, mode: "insensitive" } },
        { board: { contains: query.search, mode: "insensitive" } },
        { tags: { has: query.search.toLowerCase() } },
      ]
    : undefined,
});

const buildSlug = (input: Pick<CreatePaperInput, "title" | "year">) =>
  `${input.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}-${input.year}-${nanoid(6)}`;

const buildStableSlug = (input: { title: string; year: number; classLevel: number; subject: string; board: string }) =>
  `${input.board}-${input.classLevel}-${input.subject}-${input.title}-${input.year}`
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

const PAPER_CACHE_PREFIX = "papers:";
const PAPER_LIST_TTL_SECONDS = 300;
const PAPER_DETAIL_TTL_SECONDS = 600;
const PAPER_TRENDING_TTL_SECONDS = 300;
const PAPER_COVERAGE_TTL_SECONDS = 900;

const invalidatePaperCaches = async () => {
  await cacheService.deleteByPrefix(PAPER_CACHE_PREFIX);
};

export const paperService = {
  async listPapers(input: ListPaperInput) {
    const cacheKey = `${PAPER_CACHE_PREFIX}list:${JSON.stringify(input)}`;
    const cached = await cacheService.getJson<{ items: unknown[]; pagination: ReturnType<typeof buildPagination> }>(cacheKey);

    if (cached) {
      return cached;
    }

    const where = buildPaperWhere(input);
    const skip = (input.page - 1) * input.limit;

    const [papers, total] = await prisma.$transaction([
      prisma.paper.findMany({
        where,
        include: {
          analysis: true,
        },
        orderBy: [{ isFeatured: "desc" }, { downloadsCount: "desc" }, { createdAt: "desc" }],
        skip,
        take: input.limit,
      }),
      prisma.paper.count({ where }),
    ]);

    const result = {
      items: papers,
      pagination: buildPagination(input.page, input.limit, total),
    };

    await cacheService.setJson(cacheKey, result, PAPER_LIST_TTL_SECONDS);

    return result;
  },

  async getPaperById(paperId: string) {
    const cacheKey = `${PAPER_CACHE_PREFIX}detail:${paperId}`;
    const cached = await cacheService.getJson<Awaited<ReturnType<typeof prisma.paper.findUniqueOrThrow>>>(cacheKey);

    if (cached) {
      return cached;
    }

    const paper = await prisma.paper.findUniqueOrThrow({
      where: { id: paperId },
      include: {
        analysis: true,
      },
    });

    await cacheService.setJson(cacheKey, paper, PAPER_DETAIL_TTL_SECONDS);
    return paper;
  },

  async getTrendingPapers(limit = 10) {
    const cacheKey = `${PAPER_CACHE_PREFIX}trending:${limit}`;
    const cached = await cacheService.getJson<Awaited<ReturnType<typeof prisma.paper.findMany>>>(cacheKey);

    if (cached) {
      return cached;
    }

    const papers = await prisma.paper.findMany({
      where: {
        status: PaperStatus.PUBLISHED,
      },
      take: limit,
      orderBy: [{ downloadsCount: "desc" }, { viewsCount: "desc" }, { createdAt: "desc" }],
      include: {
        analysis: true,
      },
    });

    await cacheService.setJson(cacheKey, papers, PAPER_TRENDING_TTL_SECONDS);
    return papers;
  },

  async getCoverageMatrix() {
    const cacheKey = `${PAPER_CACHE_PREFIX}coverage`;
    const cached = await cacheService.getJson<{ classes: unknown[]; totalPapers: number }>(cacheKey);

    if (cached) {
      return cached;
    }

    const papers = await prisma.paper.findMany({
      where: {
        status: PaperStatus.PUBLISHED,
        classLevel: {
          in: [9, 10, 11, 12],
        },
        year: {
          gte: new Date().getFullYear() - 9,
        },
      },
      select: {
        classLevel: true,
        year: true,
        subject: true,
        board: true,
      },
      orderBy: [{ classLevel: "asc" }, { year: "desc" }, { board: "asc" }, { subject: "asc" }],
    });

    const byClass = [9, 10, 11, 12].map((classLevel) => {
      const classPapers = papers.filter((paper) => paper.classLevel === classLevel);
      const years = [...new Set(classPapers.map((paper) => paper.year))].sort((left, right) => right - left);
      const boards = [...new Set(classPapers.map((paper) => paper.board))].sort();
      const subjects = [...new Set(classPapers.map((paper) => paper.subject))].sort();

      return {
        classLevel,
        totalPapers: classPapers.length,
        years,
        boards,
        subjects,
      };
    });

    const result = {
      classes: byClass,
      totalPapers: papers.length,
    };

    await cacheService.setJson(cacheKey, result, PAPER_COVERAGE_TTL_SECONDS);
    return result;
  },

  async createPaperUploadUrl(input: CreatePaperInput) {
    const storageKey = storageService.buildPaperStorageKey(input);
    const uploadUrl = await storageService.getSignedUploadUrl(storageKey, "application/pdf");

    return {
      storageKey,
      uploadUrl,
      suggestedSlug: buildSlug(input),
    };
  },

  async createPaperFromUpload(input: CreatePaperInput, file: Express.Multer.File, uploadedById?: string) {
    if (!file) {
      throw new ApiError(400, "PDF file is required.");
    }

    const inspected = await pdfService.inspectPdf(file);
    const storageKey = storageService.buildPaperStorageKey(input);
    const uploaded = await storageService.uploadBuffer(storageKey, file.buffer, file.mimetype);

    const paper = await prisma.paper.create({
      data: {
        slug: buildSlug(input),
        title: input.title,
        classLevel: input.classLevel,
        subject: input.subject,
        board: input.board,
        year: input.year,
        language: input.language,
        tags: input.tags.map((tag) => tag.toLowerCase()),
        pdfUrl: uploaded.url,
        storageKey,
        pageCount: inspected.pageCount,
        status: input.status as PaperStatus,
        uploadedById,
        analysis: {
          create: {
            status: AnalysisStatus.PENDING,
            ocrText: inspected.text || null,
          },
        },
      },
      include: {
        analysis: true,
      },
    });

    await activityService.log({
      userId: uploadedById,
      action: "paper.uploaded",
      entityType: "Paper",
      entityId: paper.id,
      metadata: {
        pageCount: inspected.pageCount,
      },
    });

    await enqueuePaperAnalysisJob(paper.id);
    await invalidatePaperCaches();

    return paper;
  },

  async bulkImportPapers(papers: PaperManifestInput[], uploadedById?: string) {
    const operations = papers.map((paper) =>
      prisma.paper.upsert({
        where: {
          slug: buildStableSlug(paper),
        },
        update: {
          title: paper.title,
          classLevel: paper.classLevel,
          subject: paper.subject,
          board: paper.board,
          year: paper.year,
          language: paper.language,
          tags: paper.tags.map((tag) => tag.toLowerCase()),
          pdfUrl: paper.pdfUrl,
          thumbnailUrl: paper.thumbnailUrl,
          storageKey: paper.storageKey,
          pageCount: paper.pageCount,
          status: paper.status as PaperStatus,
          aiSummary: paper.summary,
          uploadedById,
        },
        create: {
          slug: buildStableSlug(paper),
          title: paper.title,
          classLevel: paper.classLevel,
          subject: paper.subject,
          board: paper.board,
          year: paper.year,
          language: paper.language,
          tags: paper.tags.map((tag) => tag.toLowerCase()),
          pdfUrl: paper.pdfUrl,
          thumbnailUrl: paper.thumbnailUrl,
          storageKey: paper.storageKey,
          pageCount: paper.pageCount,
          status: paper.status as PaperStatus,
          aiSummary: paper.summary,
          uploadedById,
          analysis: {
            create: {
              status: paper.ocrText ? AnalysisStatus.PENDING : AnalysisStatus.COMPLETED,
              ocrText: paper.ocrText,
              summary: paper.summary,
            },
          },
        },
      }),
    );

    const results = await prisma.$transaction(operations);

    await Promise.all(
      results.map((paper, index) => (papers[index]?.ocrText ? enqueuePaperAnalysisJob(paper.id) : Promise.resolve())),
    );

    await activityService.log({
      userId: uploadedById,
      action: "paper.bulk-imported",
      metadata: {
        count: results.length,
      },
    });

    await invalidatePaperCaches();

    return results;
  },

  async updatePaper(paperId: string, input: Partial<CreatePaperInput> & { isFeatured?: boolean }) {
    const paper = await prisma.paper.update({
      where: { id: paperId },
      data: {
        ...input,
        tags: input.tags?.map((tag) => tag.toLowerCase()),
      },
      include: {
        analysis: true,
      },
    });

    await invalidatePaperCaches();
    return paper;
  },

  async featurePaper(paperId: string, isFeatured = true) {
    const paper = await prisma.paper.update({
      where: { id: paperId },
      data: {
        isFeatured,
      },
    });

    await invalidatePaperCaches();
    return paper;
  },

  async deletePaper(paperId: string) {
    const paper = await prisma.paper.findUnique({
      where: { id: paperId },
    });

    if (!paper) {
      throw new ApiError(404, "Paper not found.");
    }

    if (paper.storageKey) {
      await storageService.deleteObject(paper.storageKey);
    }
    await prisma.paper.delete({
      where: { id: paperId },
    });

    await invalidatePaperCaches();
  },

  async bookmarkPaper(userId: string, paperId: string) {
    await prisma.bookmark.upsert({
      where: {
        userId_paperId: {
          userId,
          paperId,
        },
      },
      update: {},
      create: {
        userId,
        paperId,
      },
    });
  },

  async removeBookmark(userId: string, paperId: string) {
    await prisma.bookmark.deleteMany({
      where: {
        userId,
        paperId,
      },
    });
  },

  async recordDownload(paperId: string, userId?: string, ipAddress?: string | null) {
    const paper = await prisma.paper.findUnique({
      where: { id: paperId },
    });

    if (!paper) {
      throw new ApiError(404, "Paper not found.");
    }

    await prisma.$transaction([
      prisma.download.create({
        data: {
          paperId,
          userId,
          ipAddress: ipAddress ?? undefined,
        },
      }),
      prisma.paper.update({
        where: { id: paperId },
        data: {
          downloadsCount: {
            increment: 1,
          },
        },
      }),
    ]);

    await invalidatePaperCaches();

    const downloadUrl = paper.storageKey ? await storageService.getSignedDownloadUrl(paper.storageKey) : paper.pdfUrl;

    return {
      downloadUrl,
    };
  },

  async incrementView(paperId: string) {
    const result = await prisma.paper.update({
      where: { id: paperId },
      data: {
        viewsCount: {
          increment: 1,
        },
      },
    });

    await cacheService.deleteByPrefix(`${PAPER_CACHE_PREFIX}detail:${paperId}`);
    await cacheService.deleteByPrefix(`${PAPER_CACHE_PREFIX}trending:`);
    return result;
  },
};
