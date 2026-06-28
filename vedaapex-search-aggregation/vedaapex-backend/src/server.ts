import { createApp } from "./app";
import { env } from "./config/env";
import { logger } from "./config/logger";
import { prisma } from "./config/prisma";
import { redis } from "./config/redis";
import { startQueueWorkers } from "./queues";

const bootstrap = async () => {
  await prisma.$connect();
  await redis.connect();

  const app = createApp();
  const server = app.listen(env.PORT, () => {
    logger.info(`VEDAAPEX backend listening on port ${env.PORT}`);
  });

  if (env.ENABLE_INLINE_QUEUE_WORKERS) {
    await startQueueWorkers();
  }

  const shutdown = async () => {
    logger.info("Shutting down gracefully");
    server.close(async () => {
      await prisma.$disconnect();
      redis.disconnect();
      process.exit(0);
    });
  };

  process.on("SIGINT", () => void shutdown());
  process.on("SIGTERM", () => void shutdown());
};

void bootstrap();
