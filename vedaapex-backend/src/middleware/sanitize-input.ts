import type { NextFunction, Request, Response } from "express";
import xss from "xss";

const sanitizeValue = (value: unknown): unknown => {
  if (typeof value === "string") {
    return xss(value.trim());
  }

  if (Array.isArray(value)) {
    return value.map((entry) => sanitizeValue(entry));
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, entry]) => [key, sanitizeValue(entry)]));
  }

  return value;
};

export const sanitizeInputMiddleware = (req: Request, _res: Response, next: NextFunction) => {
  req.body = sanitizeValue(req.body);
  req.query = sanitizeValue(req.query) as Request["query"];
  req.params = sanitizeValue(req.params) as Request["params"];
  next();
};
