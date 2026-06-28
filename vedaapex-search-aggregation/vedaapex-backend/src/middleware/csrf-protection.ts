import type { NextFunction, Request, Response } from "express";

import { env } from "../config/env";
import { ApiError } from "../utils/api-error";

const CSRF_COOKIE_NAME = "vedaapex.csrf";

const issueToken = (res: Response) => {
  const token = crypto.randomUUID().replace(/-/g, "");
  res.cookie(CSRF_COOKIE_NAME, token, {
    httpOnly: false,
    secure: env.NODE_ENV === "production",
    sameSite: "strict",
  });
  return token;
};

const isReadMethod = (method: string) => ["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase());

export const csrfProtection = (req: Request, res: Response, next: NextFunction) => {
  const cookieToken = req.cookies?.[CSRF_COOKIE_NAME] as string | undefined;
  const currentToken = cookieToken ?? issueToken(res);

  req.csrfToken = () => currentToken;

  if (isReadMethod(req.method)) {
    return next();
  }

  const headerToken = (req.headers["x-csrf-token"] as string | undefined) ?? req.body?.csrfToken;

  if (!headerToken || headerToken !== currentToken) {
    return next(new ApiError(403, "CSRF token validation failed."));
  }

  next();
};
