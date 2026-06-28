import { Prisma, UsageMetricType } from "@prisma/client";

import { prisma } from "../config/prisma";
import { toOptionalJsonValue } from "../utils/prisma-json";

type UsageInput = {
  userId?: string;
  paperId?: string;
  metricType: UsageMetricType;
  provider?: string;
  modelName?: string;
  inputTokens?: number;
  outputTokens?: number;
  estimatedCost?: number;
  metadata?: Record<string, unknown>;
};

export const usageService = {
  async track(input: UsageInput) {
    await prisma.aIUsageEvent.create({
      data: {
        userId: input.userId,
        paperId: input.paperId,
        metricType: input.metricType,
        provider: input.provider,
        modelName: input.modelName,
        inputTokens: input.inputTokens,
        outputTokens: input.outputTokens,
        estimatedCost: input.estimatedCost !== undefined ? new Prisma.Decimal(input.estimatedCost) : undefined,
        metadata: toOptionalJsonValue(input.metadata),
      },
    });
  },
};
