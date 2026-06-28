import { redis } from "../config/redis";

type CacheEnvelope<T> = {
  value: T;
  cachedAt: string;
};

export const cacheService = {
  async getJson<T>(key: string): Promise<T | null> {
    const raw = await redis.get(key);

    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw) as CacheEnvelope<T>;
    return parsed.value;
  },

  async setJson<T>(key: string, value: T, ttlSeconds: number) {
    const payload: CacheEnvelope<T> = {
      value,
      cachedAt: new Date().toISOString(),
    };

    await redis.set(key, JSON.stringify(payload), "EX", ttlSeconds);
  },

  async deleteByPrefix(prefix: string) {
    const keys = await redis.keys(`${prefix}*`);

    if (keys.length > 0) {
      await redis.del(...keys);
    }
  },
};
