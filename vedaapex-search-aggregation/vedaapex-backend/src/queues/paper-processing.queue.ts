import { Queue, Worker } from "bullmq";

import { env } from "../config/env";
import { aiService } from "../services/ai.service";
import { logger } from "../config/logger";
import IORedis from "ioredis";

const connection = new IORedis(env.REDIS_URL, {
  maxRetriesPerRequest: null,
});

const queueName = "paper-processing";

export const paperProcessingQueue = new Queue(queueName, {
  connection,
});

let worker: Worker | null = null;

export const enqueuePaperAnalysisJob = async (paperId: string, force = false) => {
  await paperProcessingQueue.add(
    "analyze-paper",
    { paperId, force },
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

export const startPaperProcessingWorker = async () => {
  if (worker) {
    return worker;
  }

  worker = new Worker(
    queueName,
    async (job) => {
      if (job.name === "analyze-paper") {
        await aiService.analyzePaper(job.data.paperId, job.data.force);
      }
    },
    {
      connection,
      concurrency: 5,
    },
  );

  worker.on("failed", (job, error) => {
    logger.error({ jobId: job?.id, error }, "Paper processing job failed");
  });

  worker.on("completed", (job) => {
    logger.info({ jobId: job.id, name: job.name }, "Paper processing job completed");
  });

  return worker;
};
