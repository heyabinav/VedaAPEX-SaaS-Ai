import { AnalysisStatus, MockTestStatus, SubmissionType, UsageMetricType } from "@prisma/client";

import { aiGateway } from "../ai";
import {
  buildAnswerEvaluationPrompt,
  buildMockTestPrompt,
  buildPaperAnalysisPrompt,
  buildStudyChatPrompt,
  buildStudyPackPrompt,
  buildStudyPlanPrompt,
} from "../ai/prompts";
import { extractJson } from "../ai/json";
import { prisma } from "../config/prisma";
import { ApiError } from "../utils/api-error";
import { toOptionalJsonValue } from "../utils/prisma-json";
import { activityService } from "./activity.service";
import { storageService } from "./storage.service";
import { usageService } from "./usage.service";

type AnswerEvaluationPayload = {
  userId: string;
  paperId?: string;
  question: string;
  answerText?: string;
  totalMarks: number;
  rubric?: Record<string, unknown>;
  submissionType: "TEXT" | "PDF" | "IMAGE";
  classLevel: number;
  subject: string;
  board: string;
};

type StudyPlanPayload = {
  userId: string;
  classLevel: number;
  subject: string;
  board: string;
  examDate: string;
  availableHoursPerDay: number;
  weakTopics: string[];
  goals: string[];
};

type MockTestPayload = {
  userId: string;
  classLevel: number;
  subject: string;
  board: string;
  topicFocus: string[];
  questionCount: number;
};

export const aiService = {
  async analyzePaper(paperId: string, force = false) {
    const paper = await prisma.paper.findUnique({
      where: { id: paperId },
      include: {
        analysis: true,
      },
    });

    if (!paper) {
      throw new ApiError(404, "Paper not found.");
    }

    if (paper.analysis?.status === AnalysisStatus.COMPLETED && !force) {
      return paper.analysis;
    }

    const extractedText = paper.analysis?.ocrText?.trim();

    if (!extractedText) {
      throw new ApiError(400, "Paper has no OCR or extracted text available for analysis.");
    }

    await prisma.aIAnalysis.upsert({
      where: { paperId },
      create: {
        paperId,
        status: AnalysisStatus.PROCESSING,
        ocrText: extractedText,
      },
      update: {
        status: AnalysisStatus.PROCESSING,
        errorMessage: null,
      },
    });

    try {
      const response = await aiGateway.generateText(
        buildPaperAnalysisPrompt(extractedText, {
          paperId: paper.id,
          title: paper.title,
          classLevel: paper.classLevel,
          subject: paper.subject,
          board: paper.board,
          year: paper.year,
        }),
      );
      const parsed = extractJson<{
        repeatedQuestions: unknown;
        importantChapters: unknown;
        topicWeightage: unknown;
        predictedQuestions: unknown;
        difficultyLevel?: string;
        revisionStrategy: unknown;
        extractedQuestions: unknown;
        questionAnswerBank?: unknown;
        rapidRevisionNotes?: unknown;
        studyStrategy?: unknown;
        summary?: string;
      }>(response.text);

      const analysis = await prisma.aIAnalysis.update({
        where: { paperId },
        data: {
          status: AnalysisStatus.COMPLETED,
          provider: response.provider,
          modelName: response.model,
          repeatedQuestions: toOptionalJsonValue(parsed.repeatedQuestions),
          importantChapters: toOptionalJsonValue(parsed.importantChapters),
          topicWeightage: toOptionalJsonValue(parsed.topicWeightage),
          predictedQuestions: toOptionalJsonValue(parsed.predictedQuestions),
          difficultyLevel: parsed.difficultyLevel,
          revisionStrategy: toOptionalJsonValue(parsed.revisionStrategy),
          extractedQuestions: toOptionalJsonValue(parsed.extractedQuestions),
          questionAnswerBank: toOptionalJsonValue(parsed.questionAnswerBank),
          rapidRevisionNotes: toOptionalJsonValue(parsed.rapidRevisionNotes),
          studyStrategy: toOptionalJsonValue(parsed.studyStrategy),
          summary: parsed.summary,
          generatedAt: new Date(),
        },
      });

      await prisma.paper.update({
        where: { id: paperId },
        data: {
          aiSummary: parsed.summary,
        },
      });

      await usageService.track({
        paperId,
        metricType: UsageMetricType.PAPER_ANALYSIS,
        provider: response.provider,
        modelName: response.model,
      });

      return analysis;
    } catch (error) {
      await prisma.aIAnalysis.update({
        where: { paperId },
        data: {
          status: AnalysisStatus.FAILED,
          errorMessage: (error as Error).message,
        },
      });
      throw error;
    }
  },

  async evaluateAnswer(input: AnswerEvaluationPayload, file?: Express.Multer.File) {
    let answerFileUrl: string | undefined;

    if (!input.answerText && !file) {
      throw new ApiError(400, "Either answerText or answer file is required.");
    }

    if (file) {
      const extension = file.originalname.split(".").pop() ?? "bin";
      const storageKey = storageService.buildAnswerStorageKey(input.userId, extension);
      const uploaded = await storageService.uploadBuffer(storageKey, file.buffer, file.mimetype);
      answerFileUrl = uploaded.url;
    }

    const response = await aiGateway.generateText(
      buildAnswerEvaluationPrompt({
        question: input.question,
        answerText: input.answerText,
        answerFileUrl,
        totalMarks: input.totalMarks,
        rubric: input.rubric,
        classLevel: input.classLevel,
        subject: input.subject,
        board: input.board,
      }),
    );

    const parsed = extractJson<{
      marksAwarded: number;
      totalMarks: number;
      improvements: unknown;
      mistakes: unknown;
      idealAnswer: unknown;
      scoringExplanation: string;
      grammarIssues: unknown;
      topperAnswer: unknown;
    }>(response.text);

    const evaluation = await prisma.answerEvaluation.create({
      data: {
        userId: input.userId,
        paperId: input.paperId,
        submissionType: input.submissionType as SubmissionType,
        answerText: input.answerText,
        answerFileUrl,
        rubric: toOptionalJsonValue(input.rubric),
        marksAwarded: parsed.marksAwarded,
        totalMarks: parsed.totalMarks,
        improvements: toOptionalJsonValue(parsed.improvements),
        mistakes: toOptionalJsonValue(parsed.mistakes),
        idealAnswer: toOptionalJsonValue(parsed.idealAnswer),
        scoringExplanation: parsed.scoringExplanation,
        grammarIssues: toOptionalJsonValue(parsed.grammarIssues),
        topperAnswer: toOptionalJsonValue(parsed.topperAnswer),
        provider: response.provider,
        modelName: response.model,
      },
    });

    await usageService.track({
      userId: input.userId,
      paperId: input.paperId,
      metricType: UsageMetricType.ANSWER_EVALUATION,
      provider: response.provider,
      modelName: response.model,
    });

    await activityService.log({
      userId: input.userId,
      action: "answer.evaluated",
      entityType: "AnswerEvaluation",
      entityId: evaluation.id,
    });

    return evaluation;
  },

  async generateStudyPlan(input: StudyPlanPayload) {
    const response = await aiGateway.generateText(
      buildStudyPlanPrompt({
        classLevel: input.classLevel,
        subject: input.subject,
        board: input.board,
        examDate: input.examDate,
        availableHoursPerDay: input.availableHoursPerDay,
        weakTopics: input.weakTopics,
        goals: input.goals,
      }),
    );

    const parsed = extractJson<{
      title: string;
      goals: unknown;
      dailyGoals: unknown;
      recommendations: unknown;
      revisionSchedule: unknown;
      weakTopics: string[];
    }>(response.text);

    const studyPlan = await prisma.studyPlan.create({
      data: {
        userId: input.userId,
        title: parsed.title,
        goals: toOptionalJsonValue(parsed.goals)!,
        dailyGoals: toOptionalJsonValue(parsed.dailyGoals)!,
        recommendations: toOptionalJsonValue(parsed.recommendations)!,
        revisionSchedule: toOptionalJsonValue(parsed.revisionSchedule)!,
        weakTopics: parsed.weakTopics,
        startsAt: new Date(),
        endsAt: new Date(input.examDate),
      },
    });

    await usageService.track({
      userId: input.userId,
      metricType: UsageMetricType.RECOMMENDATION,
      provider: response.provider,
      modelName: response.model,
    });

    return studyPlan;
  },

  async generateMockTest(input: MockTestPayload) {
    const response = await aiGateway.generateText(
      buildMockTestPrompt({
        classLevel: input.classLevel,
        subject: input.subject,
        board: input.board,
        topicFocus: input.topicFocus,
        questionCount: input.questionCount,
      }),
    );

    const parsed = extractJson<{
      title: string;
      questions: unknown;
      answerKey: unknown;
    }>(response.text);

    const mockTest = await prisma.mockTest.create({
      data: {
        userId: input.userId,
        title: parsed.title,
        classLevel: input.classLevel,
        subject: input.subject,
        board: input.board,
        questions: toOptionalJsonValue(parsed.questions)!,
        answerKey: toOptionalJsonValue(parsed.answerKey),
        status: MockTestStatus.GENERATED,
      },
    });

    await usageService.track({
      userId: input.userId,
      metricType: UsageMetricType.MOCK_TEST,
      provider: response.provider,
      modelName: response.model,
    });

    return mockTest;
  },

  async studyChat(userId: string, message: string, context?: Record<string, unknown>) {
    const response = await aiGateway.generateText(buildStudyChatPrompt(message, context));

    await usageService.track({
      userId,
      metricType: UsageMetricType.CHAT,
      provider: response.provider,
      modelName: response.model,
      metadata: {
        messageLength: message.length,
      },
    });

    return {
      reply: response.text,
      provider: response.provider,
      model: response.model,
    };
  },

  async generateStudyPack(paperId: string, force = false) {
    const paper = await prisma.paper.findUnique({
      where: { id: paperId },
      include: {
        analysis: true,
      },
    });

    if (!paper) {
      throw new ApiError(404, "Paper not found.");
    }

    const analysis = paper.analysis;

    if (!analysis?.ocrText?.trim()) {
      throw new ApiError(400, "Paper OCR text is required before generating a study pack.");
    }

    if (!force && analysis.questionAnswerBank && analysis.rapidRevisionNotes && analysis.studyStrategy) {
      return {
        paperId,
        questionAnswerBank: analysis.questionAnswerBank,
        rapidRevisionNotes: analysis.rapidRevisionNotes,
        studyStrategy: analysis.studyStrategy,
      };
    }

    const response = await aiGateway.generateText(
      buildStudyPackPrompt({
        classLevel: paper.classLevel,
        subject: paper.subject,
        board: paper.board,
        year: paper.year,
        title: paper.title,
        ocrText: analysis.ocrText,
      }),
    );

    const parsed = extractJson<{
      questionAnswerBank: unknown;
      rapidRevisionNotes: unknown;
      studyStrategy: unknown;
    }>(response.text);

    await prisma.aIAnalysis.update({
      where: { paperId },
      data: {
        questionAnswerBank: toOptionalJsonValue(parsed.questionAnswerBank),
        rapidRevisionNotes: toOptionalJsonValue(parsed.rapidRevisionNotes),
        studyStrategy: toOptionalJsonValue(parsed.studyStrategy),
      },
    });

    await usageService.track({
      paperId,
      metricType: UsageMetricType.STUDY_PACK,
      provider: response.provider,
      modelName: response.model,
    });

    return {
      paperId,
      questionAnswerBank: parsed.questionAnswerBank,
      rapidRevisionNotes: parsed.rapidRevisionNotes,
      studyStrategy: parsed.studyStrategy,
    };
  },
};
