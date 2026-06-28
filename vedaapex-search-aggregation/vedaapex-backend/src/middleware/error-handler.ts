import type { NextFunction, Request, Response } from "express";
import { StatusCodes } from "http-status-codes";

import { env } from "../config/env";
import { logger } from "../config/logger";
import { ApiError } from "../utils/api-error";

export const errorHandler = (error: Error, req: Request, res: Response, _next: NextFunction) => {
  const statusCode = error instanceof ApiError ? error.statusCode : StatusCodes.INTERNAL_SERVER_ERROR;

  logger.error({
    err: error,
    requestId: req.requestId,
    path: req.path,
    method: req.method,
  });

  res.status(statusCode).json({
    success: false,
    message: error.message || "Internal server error",
    details: error instanceof ApiError ? error.details : undefined,
    requestId: req.requestId,
    stack: env.NODE_ENV === "development" ? error.stack : undefined,
  });
};
