import type { PaginationMeta } from "../types/api";

type SuccessPayload<T> = {
  success: true;
  data: T;
  meta?: PaginationMeta | Record<string, unknown>;
};

export const successResponse = <T>(data: T, meta?: SuccessPayload<T>["meta"]): SuccessPayload<T> => ({
  success: true,
  data,
  meta,
});
