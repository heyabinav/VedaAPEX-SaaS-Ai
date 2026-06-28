export const extractJson = <T>(text: string): T => {
  const cleaned = text.replace(/```json|```/gi, "").trim();
  const startIndex = cleaned.indexOf("{");
  const endIndex = cleaned.lastIndexOf("}");

  if (startIndex === -1 || endIndex === -1) {
    throw new Error("AI response did not contain valid JSON.");
  }

  return JSON.parse(cleaned.slice(startIndex, endIndex + 1)) as T;
};
