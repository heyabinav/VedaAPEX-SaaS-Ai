import OpenAI from "openai";

import { env } from "../config/env";
import type { AiGenerateParams, AiProvider, AiProviderResponse } from "./provider";

export class OpenAiProvider implements AiProvider {
  private readonly client: OpenAI;

  constructor() {
    if (!env.OPENAI_API_KEY) {
      throw new Error("OPENAI_API_KEY is not configured.");
    }

    this.client = new OpenAI({
      apiKey: env.OPENAI_API_KEY,
    });
  }

  async generateText(params: AiGenerateParams): Promise<AiProviderResponse> {
    const response = await this.client.chat.completions.create({
      model: env.OPENAI_MODEL,
      temperature: params.temperature ?? 0.2,
      messages: [
        {
          role: "system",
          content: params.systemPrompt,
        },
        {
          role: "user",
          content: params.userPrompt,
        },
      ],
    });

    return {
      provider: "openai",
      model: env.OPENAI_MODEL,
      text: response.choices[0]?.message.content ?? "",
    };
  }
}
