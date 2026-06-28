import { PaperStatus, UserRole } from "@prisma/client";

import { prisma } from "../config/prisma";

export const analyticsService = {
  async getAdminOverview() {
    const [users, admins, papers, publishedPapers, downloads, evaluations, aiUsage] = await prisma.$transaction([
      prisma.user.count(),
      prisma.user.count({ where: { role: UserRole.ADMIN } }),
      prisma.paper.count(),
      prisma.paper.count({ where: { status: PaperStatus.PUBLISHED } }),
      prisma.download.count(),
      prisma.answerEvaluation.count(),
      prisma.aIUsageEvent.count(),
    ]);

    return {
      users,
      admins,
      papers,
      publishedPapers,
      downloads,
      answerEvaluations: evaluations,
      aiUsageEvents: aiUsage,
    };
  },

  async getLeaderboard(scope = "monthly", subject?: string) {
    return prisma.leaderboardEntry.findMany({
      where: {
        scope,
        subject,
      },
      take: 20,
      orderBy: [{ points: "desc" }, { updatedAt: "asc" }],
      include: {
        user: {
          select: {
            id: true,
            name: true,
            avatarUrl: true,
          },
        },
      },
    });
  },

  async getPaperAnalytics() {
    return prisma.paper.findMany({
      select: {
        id: true,
        title: true,
        downloadsCount: true,
        viewsCount: true,
        createdAt: true,
        subject: true,
        board: true,
        classLevel: true,
      },
      orderBy: [{ downloadsCount: "desc" }, { viewsCount: "desc" }],
      take: 50,
    });
  },
};
