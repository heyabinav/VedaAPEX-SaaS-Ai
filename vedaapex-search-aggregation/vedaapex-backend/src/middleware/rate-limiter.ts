import type { RequestHandler } from "express";

import { env } from "../config/env";
import { redis } from "../config/redis";

type LimiterOptions = {
  prefix: string;
  windowMs: number;
  max: number;
  message: string;
};

type FallbackBucket = {
  count: number;
  resetAt: number;
};

const fallbackBuckets = new Map<string, FallbackBucket>();

const setHeaders = (res: Parameters<RequestHandler>[1], max: number, remaining: number, resetSeconds: number) => {
  res.setHeader("RateLimit-Limit", String(max));
  res.setHeader("RateLimit-Remaining", String(Math.max(0, remaining)));
  res.setHeader("RateLimit-Reset", String(Math.max(1, resetSeconds)));
};

const enforceFallbackLimit = (key: string, options: LimiterOptions) => {
  const now = Date.now();
  const current = fallbackBuckets.get(key);

  if (!current || current.resetAt <= now) {
    const bucket = {
      count: 1,
      resetAt: now + options.windowMs,
    };

    fallbackBuckets.set(key, bucket);
    return {
      allowed: true,
      remaining: options.max - 1,
      resetSeconds: Math.ceil(options.windowMs / 1000),
    };
  }

  current.count += 1;

  return {
    allowed: current.count <= options.max,
    remaining: options.max - current.count,
    resetSeconds: Math.ceil((current.resetAt - now) / 1000),
  };
};

const createRateLimiter = (options: LimiterOptions): RequestHandler => {
  return async (req, res, next) => {
    const identifier = req.ip || req.socket.remoteAddress || "unknown";
    const bucketKey = `rate-limit:${options.prefix}:${identifier}:${Math.floor(Date.now() / options.windowMs)}`;

    try {
      const currentCount = await redis.incr(bucketKey);

      if (currentCount === 1) {
        await redis.pexpire(bucketKey, options.windowMs);
      }

      const ttlMs = await redis.pttl(bucketKey);
      const resetSeconds = Math.ceil((ttlMs > 0 ? ttlMs : options.windowMs) / 1000);
      setHeaders(res, options.max, options.max - currentCount, resetSeconds);

      if (currentCount > options.max) {
        res.status(429).json({
          success: false,
          message: options.message,
        });
        return;
      }
    } catch {
      const fallbackState = enforceFallbackLimit(bucketKey, options);
      setHeaders(res, options.max, fallbackState.remaining, fallbackState.resetSeconds);

      if (!fallbackState.allowed) {
        res.status(429).json({
          success: false,
          message: options.message,
        });
        return;
      }
    }

    next();
  };
};

export const generalRateLimiter = createRateLimiter({
  prefix: "general",
  windowMs: env.RATE_LIMIT_WINDOW_MS,
  max: env.RATE_LIMIT_MAX,
  message: "Too many requests. Please retry later.",
});

export const authRateLimiter = createRateLimiter({
  prefix: "auth",
  windowMs: env.AUTH_RATE_LIMIT_WINDOW_MS,
  max: env.AUTH_RATE_LIMIT_MAX,
  message: "Too many authentication attempts. Please retry later.",
});
