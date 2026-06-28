import { z } from "zod";

export const analyzePaperSchema = z.object({
  force: z.boolean().optional().default(false),
  async: z.boolean().optional().default(false),
});

export const generateStudyPackSchema = z.object({
  force: z.boolean().optional().default(false),
});

export const evaluateAnswerSchema = z.object({
  paperId: z.string().cuid().optional(),
  question: z.string().min(5).max(2000),
  answerText: z.string().min(20).max(10000).optional(),
  submissionType: z.enum(["TEXT", "PDF", "IMAGE"]).default("TEXT"),
  totalMarks: z.coerce.number().positive().default(100),
  rubric: z.record(z.any()).optional(),
  classLevel: z.coerce.number().int().min(9).max(12),
  subject: z.string().min(2).max(100),
  board: z.string().min(2).max(100),
});

export const studyChatSchema = z.object({
  message: z.string().min(2).max(4000),
  context: z.record(z.any()).optional(),
});
