import { NotificationChannel, NotificationStatus } from "@prisma/client";

import { prisma } from "../config/prisma";
import { toOptionalJsonValue } from "../utils/prisma-json";

type CreateNotificationInput = {
  userId: string;
  title: string;
  message: string;
  channel?: NotificationChannel;
  metadata?: Record<string, unknown>;
};

export const notificationService = {
  async create(input: CreateNotificationInput) {
    return prisma.notification.create({
      data: {
        userId: input.userId,
        title: input.title,
        message: input.message,
        channel: input.channel ?? NotificationChannel.IN_APP,
        metadata: toOptionalJsonValue(input.metadata),
      },
    });
  },

  async markRead(userId: string, notificationId: string) {
    return prisma.notification.updateMany({
      where: {
        id: notificationId,
        userId,
      },
      data: {
        status: NotificationStatus.READ,
        readAt: new Date(),
      },
    });
  },

  async list(userId: string) {
    return prisma.notification.findMany({
      where: { userId },
      orderBy: { createdAt: "desc" },
    });
  },
};
