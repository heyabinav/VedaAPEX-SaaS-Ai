import type { NextFunction, Request, Response } from "express";
import type { ZodSchema } from "zod";

import { ApiError } from "../utils/api-error";

type ValidationTarget = "body" | "params" | "query";

export const validate =
  <T>(schema: ZodSchema<T>, target: ValidationTarget = "body") =>
  (req: Request, _res: Response, next: NextFunction) => {
    const parsed = schema.safeParse(req[target]);

    if (!parsed.success) {
      return next(new ApiError(400, "Validation failed", parsed.error.flatten()));
    }

    req[target] = parsed.data as Request[ValidationTarget];
    next();
  };
