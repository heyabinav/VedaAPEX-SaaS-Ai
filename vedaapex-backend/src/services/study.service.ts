import { prisma } from "../config/prisma";

export const studyService = {
  async upsertProgress(userId: string, input: {
    classLevel: number;
    subject: string;
    board: string;
    weakTopics: string[];
    strongTopics: string[];
    scoreAverage: number;
    streakDays: number;
  }) {
    return prisma.userProgress.upsert({
      where: {
        userId_classLevel_subject_board: {
          userId,
          classLevel: input.classLevel,
          subject: input.subject,
          board: input.board,
        },
      },
      update: {
        weakTopics: input.weakTopics,
        strongTopics: input.strongTopics,
        scoreAverage: input.scoreAverage,
        streakDays: input.streakDays,
        lastActivityAt: new Date(),
      },
      create: {
        userId,
        classLevel: input.classLevel,
        subject: input.subject,
        board: input.board,
        weakTopics: input.weakTopics,
        strongTopics: input.strongTopics,
        scoreAverage: input.scoreAverage,
        streakDays: input.streakDays,
        lastActivityAt: new Date(),
      },
    });
  },

  async getStudyDashboard(userId: string) {
    const [studyPlans, progressRecords, mockTests, bookmarks] = await prisma.$transaction([
      prisma.studyPlan.findMany({
        where: { userId },
        take: 5,
        orderBy: { createdAt: "desc" },
      }),
      prisma.userProgress.findMany({
        where: { userId },
        orderBy: { updatedAt: "desc" },
      }),
      prisma.mockTest.findMany({
        where: { userId },
        take: 5,
        orderBy: { createdAt: "desc" },
      }),
      prisma.bookmark.count({
        where: { userId },
      }),
    ]);

    return {
      studyPlans,
      progressRecords,
      mockTests,
      bookmarkedPapers: bookmarks,
    };
  },

  async getStudyPlans(userId: string) {
    return prisma.studyPlan.findMany({
      where: { userId },
      orderBy: { createdAt: "desc" },
    });
  },
};
