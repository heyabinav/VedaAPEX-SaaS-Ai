import { NotificationStatus } from "@prisma/client";
import { Queue, Worker } from "bullmq";
import IORedis from "ioredis";

import { env } from "../config/env";
import { logger } from "../config/logger";
import { prisma } from "../config/prisma";

const connection = new IORedis(env.REDIS_URL, {
  maxRetriesPerRequest: null,
});

const queueName = "notification-dispatch";

export const notificationQueue = new Queue(queueName, {
  connection,
});

let worker: Worker | null = null;

export const enqueueNotificationJob = async (notificationId: string) => {
  await notificationQueue.add(
    "send-notification",
    { notificationId },
    {
      attempts: 3,
      removeOnComplete: 50,
      removeOnFail: 100,
    },
  );
};

export const startNotificationWorker = async () => {
  if (worker) {
    return worker;
  }

  worker = new Worker(
    queueName,
    async (job) => {
      if (job.name !== "send-notification") {
        return;
      }

      await prisma.notification.update({
        where: { id: job.data.notificationId },
        data: {
          status: NotificationStatus.SENT,
          sentAt: new Date(),
        },
      });
    },
    {
      connection,
      concurrency: 10,
    },
  );

  worker.on("failed", async (job, error) => {
    logger.error({ jobId: job?.id, error }, "Notification job failed");

    if (job?.data.notificationId) {
      await prisma.notification.updateMany({
        where: { id: job.data.notificationId },
        data: {
          status: NotificationStatus.FAILED,
        },
      });
    }
  });

  return worker;
};
