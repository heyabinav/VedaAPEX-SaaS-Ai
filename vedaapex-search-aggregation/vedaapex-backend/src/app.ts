import compression from "compression";
import cookieParser from "cookie-parser";
import cors from "cors";
import express, { type RequestHandler } from "express";
import helmet from "helmet";
import pinoHttp from "pino-http";
import swaggerUi from "swagger-ui-express";

import { swaggerSpec } from "./config/swagger";
import { env } from "./config/env";
import { logger } from "./config/logger";
import { prisma } from "./config/prisma";
import { redis } from "./config/redis";
import { apiV1Router } from "./routes/v1";
import { errorHandler } from "./middleware/error-handler";
import { notFoundHandler } from "./middleware/not-found";
import { csrfProtection } from "./middleware/csrf-protection";
import { requestContextMiddleware } from "./middleware/request-context";
import { generalRateLimiter } from "./middleware/rate-limiter";
import { sanitizeInputMiddleware } from "./middleware/sanitize-input";
import { successResponse } from "./utils/response";

export const createApp = () => {
  const app = express();

  if (env.TRUST_PROXY) {
    app.set("trust proxy", 1);
  }

  app.use(
    pinoHttp({
      logger,
      genReqId: (req) => (req.headers["x-request-id"] as string | undefined) ?? crypto.randomUUID(),
      customSuccessMessage: (req, res) => `${req.method} ${req.url} -> ${res.statusCode}`,
      customErrorMessage: (req, res, error) => `${req.method} ${req.url} failed: ${error.message}`,
    }),
  );
  app.use(requestContextMiddleware);
  app.use(helmet());
  app.use(
    cors({
      origin: env.allowedOrigins,
      credentials: env.CORS_ALLOW_CREDENTIALS,
    }),
  );
  app.use(generalRateLimiter);
  app.use(compression());
  app.use(express.json({ limit: `${env.MAX_UPLOAD_MB}mb` }));
  app.use(express.urlencoded({ extended: true }));
  app.use(cookieParser());
  app.use(sanitizeInputMiddleware);

  if (env.ENABLE_CSRF) {
    app.use(csrfProtection as RequestHandler);
  }

  app.get("/health", (_req, res) => {
    res.status(200).json(successResponse({ status: "ok", service: env.APP_NAME }));
  });

  app.get("/ready", async (_req, res, next) => {
    try {
      await prisma.$queryRaw`SELECT 1`;
      await redis.ping();

      res.status(200).json(
        successResponse({
          status: "ready",
          checks: {
            database: "ok",
            redis: "ok",
          },
        }),
      );
    } catch (error) {
      next(error);
    }
  });

  app.get("/csrf-token", (req, res) => {
    res.status(200).json(
      successResponse({
        csrfToken: req.csrfToken ? req.csrfToken() : null,
      }),
    );
  });

  if (env.ENABLE_SWAGGER) {
    app.use("/docs", swaggerUi.serve, swaggerUi.setup(swaggerSpec) as RequestHandler);
  }

  app.use(`${env.API_PREFIX}/${env.API_VERSION}`, apiV1Router);
  app.use(notFoundHandler);
  app.use(errorHandler);

  return app;
};
