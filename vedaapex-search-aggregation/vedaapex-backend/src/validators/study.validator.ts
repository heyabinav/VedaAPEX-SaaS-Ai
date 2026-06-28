import { z } from "zod";

export const generateStudyPlanSchema = z.object({
  classLevel: z.coerce.number().int().min(9).max(12),
  subject: z.string().min(2).max(100),
  board: z.string().min(2).max(100),
  examDate: z.string().datetime(),
  availableHoursPerDay: z.coerce.number().min(1).max(16),
  weakTopics: z.array(z.string()).default([]),
  goals: z.array(z.string()).default([]),
});

export const updateProgressSchema = z.object({
  classLevel: z.coerce.number().int().min(9).max(12),
  subject: z.string().min(2).max(100),
  board: z.string().min(2).max(100),
  weakTopics: z.array(z.string()).default([]),
  strongTopics: z.array(z.string()).default([]),
  scoreAverage: z.coerce.number().min(0).max(100).default(0),
  streakDays: z.coerce.number().int().min(0).default(0),
});

export const generateMockTestSchema = z.object({
  classLevel: z.coerce.number().int().min(9).max(12),
  subject: z.string().min(2).max(100),
  board: z.string().min(2).max(100),
  topicFocus: z.array(z.string()).default([]),
  questionCount: z.coerce.number().int().min(5).max(50).default(20),
});
