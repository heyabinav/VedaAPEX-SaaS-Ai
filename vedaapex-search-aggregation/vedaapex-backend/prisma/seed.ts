import { AnalysisStatus, AuthProvider, MediaAssetType, MediaJobStatus, MediaJobType, PaperStatus, UserRole } from "@prisma/client";
import bcrypt from "bcryptjs";

import { prisma } from "../src/config/prisma";

const currentYear = new Date().getFullYear();

const buildPaperCatalog = () => {
  const classes = [9, 10, 11, 12];
  const boards = ["CBSE", "ICSE"];
  const subjectsByClass: Record<number, string[]> = {
    9: ["Mathematics", "Science", "English"],
    10: ["Mathematics", "Science", "Social Science", "English"],
    11: ["Mathematics", "Physics", "Chemistry", "Biology", "Economics"],
    12: ["Mathematics", "Physics", "Chemistry", "Biology", "Business Studies", "Economics"],
  };

  const papers: Array<{
    slug: string;
    title: string;
    classLevel: number;
    subject: string;
    board: string;
    year: number;
    pdfUrl: string;
    storageKey: string | null;
    aiSummary: string;
    tags: string[];
  }> = [];

  for (const classLevel of classes) {
    for (const board of boards) {
      for (const subject of subjectsByClass[classLevel]!) {
        for (let year = currentYear - 9; year <= currentYear; year += 1) {
          const slug = `${board.toLowerCase()}-class-${classLevel}-${subject.toLowerCase().replace(/\s+/g, "-")}-${year}`;
          papers.push({
            slug,
            title: `${board} Class ${classLevel} ${subject} Previous Year Paper ${year}`,
            classLevel,
            subject,
            board,
            year,
            pdfUrl: `https://cdn.vedaapex.com/papers/${board.toLowerCase()}/class-${classLevel}/${subject.toLowerCase().replace(/\s+/g, "-")}/${year}.pdf`,
            storageKey: `papers/${board.toLowerCase()}/class-${classLevel}/${subject.toLowerCase().replace(/\s+/g, "-")}/${year}.pdf`,
            aiSummary: `Board-focused ${subject} practice paper for Class ${classLevel} with revision-friendly coverage and likely repeat concepts.`,
            tags: ["board-exam", "previous-year", subject.toLowerCase().replace(/\s+/g, "-")],
          });
        }
      }
    }
  }

  return papers;
};

const seed = async () => {
  const refreshTokenHash = await bcrypt.hash("seed-refresh-token", 10);

  const admin = await prisma.user.upsert({
    where: { email: "admin@vedaapex.com" },
    update: {},
    create: {
      email: "admin@vedaapex.com",
      name: "VEDAAPEX Admin",
      role: UserRole.ADMIN,
      provider: AuthProvider.GOOGLE,
      emailVerified: true,
      sessions: {
        create: {
          refreshTokenHash,
          ipAddress: "127.0.0.1",
          userAgent: "seed-script",
          expiresAt: new Date(Date.now() + 1000 * 60 * 60 * 24 * 30),
        },
      },
    },
  });

  const papers = buildPaperCatalog();

  for (const paper of papers) {
    await prisma.paper.upsert({
      where: { slug: paper.slug },
      update: {},
      create: {
        slug: paper.slug,
        title: paper.title,
        classLevel: paper.classLevel,
        subject: paper.subject,
        board: paper.board,
        year: paper.year,
        language: "en",
        tags: paper.tags,
        pdfUrl: paper.pdfUrl,
        storageKey: paper.storageKey,
        status: PaperStatus.PUBLISHED,
        uploadedById: admin.id,
        aiSummary: paper.aiSummary,
        analysis: {
          create: {
            status: AnalysisStatus.PENDING,
            summary: paper.aiSummary,
          },
        },
      },
    });
  }

  const mediaAsset = await prisma.mediaAsset.upsert({
    where: {
      storageKey: "media/originals/image/seed-study-poster.png",
    },
    update: {},
    create: {
      userId: admin.id,
      type: MediaAssetType.IMAGE,
      title: "Seed Study Poster",
      originalUrl: "https://cdn.vedaapex.com/media/seed-study-poster.png",
      storageKey: "media/originals/image/seed-study-poster.png",
      mimeType: "image/png",
      sizeBytes: 128000,
      metadata: {
        createdBy: "seed",
      },
    },
  });

  const existingSeedMediaJob = await prisma.mediaJob.findFirst({
    where: {
      assetId: mediaAsset.id,
      type: MediaJobType.IMAGE_BACKGROUND_REMOVAL,
    },
  });

  if (!existingSeedMediaJob) {
    await prisma.mediaJob.create({
      data: {
        userId: admin.id,
        assetId: mediaAsset.id,
        type: MediaJobType.IMAGE_BACKGROUND_REMOVAL,
        status: MediaJobStatus.COMPLETED,
        provider: "seed-demo",
        progress: 100,
        outputUrl: "https://cdn.vedaapex.com/media/seed-study-poster-bg-removed.png",
        outputStorageKey: "media/processed/image/background-removal/seed-study-poster-bg-removed.png",
        completedAt: new Date(),
      },
    });
  }
};

seed()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (error) => {
    console.error(error);
    await prisma.$disconnect();
    process.exit(1);
  });
