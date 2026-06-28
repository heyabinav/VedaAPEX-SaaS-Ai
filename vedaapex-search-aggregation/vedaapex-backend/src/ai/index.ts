import { env } from "../config/env";
import { GeminiProvider } from "./gemini-provider";
import { GroqProvider } from "./groq-provider";
import { OpenAiProvider } from "./openai-provider";
import type { AiGenerateParams, AiProviderResponse } from "./provider";

const providerFactory = {
  groq: () => new GroqProvider(),
  openai: () => new OpenAiProvider(),
  gemini: () => new GeminiProvider(),
};

export const aiGateway = {
  async generateText(params: AiGenerateParams): Promise<AiProviderResponse> {
    const errors: string[] = [];

    for (const providerName of env.aiProviderPriority) {
      const factory = providerFactory[providerName as keyof typeof providerFactory];

      if (!factory) {
        continue;
      }

      try {
        return await factory().generateText(params);
      } catch (error) {
        errors.push(`${providerName}: ${(error as Error).message}`);
      }
    }

    throw new Error(`No AI provider available. ${errors.join(" | ")}`);
  },
};
