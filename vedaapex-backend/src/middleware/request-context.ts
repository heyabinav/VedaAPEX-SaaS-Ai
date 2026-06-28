import type { NextFunction, Request, Response } from "express";

export const requestContextMiddleware = (req: Request, res: Response, next: NextFunction) => {
  const requestId = (req.headers["x-request-id"] as string | undefined) ?? crypto.randomUUID();

  req.requestId = requestId;
  res.setHeader("x-request-id", requestId);

  next();
};
