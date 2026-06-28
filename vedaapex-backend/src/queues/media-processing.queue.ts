import { Queue, Worker } from "bullmq";
import IORedis from "ioredis";

import { env } from "../config/env";
import { logger } from "../config/logger";
import { mediaService } from "../services/media.service";

const connection = new IORedis(env.REDIS_URL, {
  maxRetriesPerRequest: null,
});

const queueName = "media-processing";

export const mediaProcessingQueue = new Queue(queueName, {
  connection,
});

let worker: Worker | null = null;

export const enqueueMediaProcessingJob = async (mediaJobId: string) => {
  await mediaProcessingQueue.add(
    "process-media",
    { mediaJobId },
    {
      attempts: 3,
      removeOnComplete: 50,
      removeOnFail: 100,
      backoff: {
        type: "exponential",
        delay: 5000,
      },
    },
  );
};

export const startMediaProcessingWorker = async () => {
  if (worker) {
    return worker;
  }

  worker = new Worker(
    queueName,
    async (job) => {
      if (job.name === "process-media") {
        await mediaService.processJob(job.data.mediaJobId);
      }
    },
    {
      connection,
      concurrency: 4,
    },
  );

  worker.on("failed", (job, error) => {
    logger.error({ jobId: job?.id, error }, "Media processing job failed");
  });

  worker.on("completed", (job) => {
    logger.info({ jobId: job.id, name: job.name }, "Media processing job completed");
  });

  return worker;
};
