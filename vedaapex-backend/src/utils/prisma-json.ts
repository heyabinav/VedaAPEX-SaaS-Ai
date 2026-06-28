import { Prisma } from "@prisma/client";

export const toJsonValue = (value: unknown): Prisma.InputJsonValue => value as Prisma.InputJsonValue;

export const toOptionalJsonValue = (value: unknown): Prisma.InputJsonValue | undefined =>
  value === undefined ? undefined : (value as Prisma.InputJsonValue);
