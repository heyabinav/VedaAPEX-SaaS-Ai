export type AiGenerateParams = {
  systemPrompt: string;
  userPrompt: string;
  temperature?: number;
};

export type AiProviderResponse = {
  provider: string;
  model: string;
  text: string;
};

export interface AiProvider {
  generateText(params: AiGenerateParams): Promise<AiProviderResponse>;
}
