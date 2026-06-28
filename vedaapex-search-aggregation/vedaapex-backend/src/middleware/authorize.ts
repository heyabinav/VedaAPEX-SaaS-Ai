import type { NextFunction, Request, Response } from "express";
import { StatusCodes } from "http-status-codes";

import { ApiError } from "../utils/api-error";

export const authorize =
  (...allowedRoles: string[]) =>
  (req: Request, _res: Response, next: NextFunction) => {
    if (!req.authUser) {
      return next(new ApiError(StatusCodes.UNAUTHORIZED, "Authentication required"));
    }

    if (!allowedRoles.includes(req.authUser.role)) {
      return next(new ApiError(StatusCodes.FORBIDDEN, "Insufficient permissions"));
    }

    next();
  };
