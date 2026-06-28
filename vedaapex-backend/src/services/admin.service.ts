import { SessionStatus, UserRole } from "@prisma/client";

import { prisma } from "../config/prisma";
import { ApiError } from "../utils/api-error";

export const adminService = {
  async listUsers(page = 1, limit = 25) {
    const skip = (page - 1) * limit;
    const [items, total] = await prisma.$transaction([
      prisma.user.findMany({
        skip,
        take: limit,
        orderBy: { createdAt: "desc" },
        include: {
          progressRecords: true,
        },
      }),
      prisma.user.count(),
    ]);

    return {
      items,
      total,
      page,
      limit,
    };
  },

  async updateUserRole(userId: string, role: UserRole) {
    return prisma.user.update({
      where: { id: userId },
      data: { role },
    });
  },

  async revokeUserSessions(userId: string) {
    const user = await prisma.user.findUnique({ where: { id: userId } });

    if (!user) {
      throw new ApiError(404, "User not found.");
    }

    await prisma.session.updateMany({
      where: { userId },
      data: {
        status: SessionStatus.REVOKED,
        revokedAt: new Date(),
      },
    });
  },

  async listAiReports() {
    return prisma.paper.findMany({
      include: {
        analysis: true,
      },
      orderBy: [{ createdAt: "desc" }],
      take: 100,
    });
  },
};
