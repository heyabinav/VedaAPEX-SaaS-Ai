import { prisma } from "./config/prisma";
import { redis } from "./config/redis";
import { logger } from "./config/logger";
import { startQueueWorkers } from "./queues";

const bootstrapWorker = async () => {
  await prisma.$connect();
  await redis.connect();
  await startQueueWorkers();

  logger.info("VEDAAPEX queue worker started");

  const shutdown = async () => {
    logger.info("Shutting down queue worker");
    await prisma.$disconnect();
    redis.disconnect();
    process.exit(0);
  };

  process.on("SIGINT", () => void shutdown());
  process.on("SIGTERM", () => void shutdown());
};

void bootstrapWorker();
