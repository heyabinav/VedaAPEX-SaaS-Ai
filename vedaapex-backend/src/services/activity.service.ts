import { prisma } from "../config/prisma";
import { toOptionalJsonValue } from "../utils/prisma-json";

type ActivityInput = {
  userId?: string | null;
  action: string;
  entityType?: string;
  entityId?: string;
  ipAddress?: string | null;
  userAgent?: string | null;
  metadata?: Record<string, unknown>;
};

export const activityService = {
  async log(input: ActivityInput) {
    await prisma.activityLog.create({
      data: {
        userId: input.userId ?? undefined,
        action: input.action,
        entityType: input.entityType,
        entityId: input.entityId,
        ipAddress: input.ipAddress ?? undefined,
        userAgent: input.userAgent ?? undefined,
        metadata: toOptionalJsonValue(input.metadata),
      },
    });
  },
};
