import { env } from "../config/env";
import type { AiGenerateParams, AiProvider, AiProviderResponse } from "./provider";

type GroqChatResponse = {
  choices?: Array<{
    message?: {
      content?: string;
    };
  }>;
};

export class GroqProvider implements AiProvider {
  constructor() {
    if (!env.GROQ_API_KEY) {
      throw new Error("GROQ_API_KEY is not configured.");
    }
  }

  async generateText(params: AiGenerateParams): Promise<AiProviderResponse> {
    const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        authorization: `Bearer ${env.GROQ_API_KEY}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: env.GROQ_MODEL,
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
      }),
    });

    if (!response.ok) {
      throw new Error(`Groq request failed with status ${response.status}.`);
    }

    const data = (await response.json()) as GroqChatResponse;

    return {
      provider: "groq",
      model: env.GROQ_MODEL,
      text: data.choices?.[0]?.message?.content ?? "",
    };
  }
}
