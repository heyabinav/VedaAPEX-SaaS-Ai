import { GoogleGenerativeAI } from "@google/generative-ai";

import { env } from "../config/env";
import type { AiGenerateParams, AiProvider, AiProviderResponse } from "./provider";

export class GeminiProvider implements AiProvider {
  private readonly client: GoogleGenerativeAI;

  constructor() {
    if (!env.GEMINI_API_KEY) {
      throw new Error("GEMINI_API_KEY is not configured.");
    }

    this.client = new GoogleGenerativeAI(env.GEMINI_API_KEY);
  }

  async generateText(params: AiGenerateParams): Promise<AiProviderResponse> {
    const model = this.client.getGenerativeModel({
      model: env.GEMINI_MODEL,
    });

    const result = await model.generateContent([params.systemPrompt, params.userPrompt].join("\n\n"));

    return {
      provider: "gemini",
      model: env.GEMINI_MODEL,
      text: result.response.text(),
    };
  }
}
