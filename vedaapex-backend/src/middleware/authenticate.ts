import type { NextFunction, Request, Response } from "express";
import { StatusCodes } from "http-status-codes";

import { verifyAccessToken } from "../auth/jwt";
import { ApiError } from "../utils/api-error";

const getBearerToken = (req: Request) => {
  const authHeader = req.headers.authorization;

  if (authHeader?.startsWith("Bearer ")) {
    return authHeader.replace("Bearer ", "");
  }

  return null;
};

export const authenticate = (req: Request, _res: Response, next: NextFunction) => {
  try {
    const token = getBearerToken(req);

    if (!token) {
      throw new ApiError(StatusCodes.UNAUTHORIZED, "Authentication required");
    }

    const payload = verifyAccessToken(token);

    req.authUser = {
      id: payload.id,
      role: payload.role,
      email: payload.email,
      phone: payload.phone,
      sessionId: payload.sessionId,
    };

    next();
  } catch (error) {
    next(error);
  }
};
