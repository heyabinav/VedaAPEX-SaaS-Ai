import type { NextFunction, Request, Response } from "express";

export const asyncHandler =
  <T extends Request>(handler: (req: T, res: Response, next: NextFunction) => Promise<unknown>) =>
  (req: T, res: Response, next: NextFunction) => {
    void handler(req, res, next).catch(next);
  };
