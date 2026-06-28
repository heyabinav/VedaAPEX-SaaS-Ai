type StudyPlanInput = {
  classLevel: number;
  subject: string;
  board: string;
  examDate: string;
  availableHoursPerDay: number;
  weakTopics: string[];
  goals: string[];
};

type MockTestInput = {
  classLevel: number;
  subject: string;
  board: string;
  topicFocus: string[];
  questionCount: number;
};

export const buildPaperAnalysisPrompt = (paperText: string, metadata: Record<string, unknown>) => ({
  systemPrompt:
    "You are an exam-paper analysis engine for Indian secondary education. Return strict JSON only with keys repeatedQuestions, importantChapters, topicWeightage, predictedQuestions, difficultyLevel, revisionStrategy, extractedQuestions, summary.",
  userPrompt: `Paper metadata: ${JSON.stringify(metadata)}\n\nExtracted paper text:\n${paperText.slice(0, 16000)}`,
});

export const buildAnswerEvaluationPrompt = (input: Record<string, unknown>) => ({
  systemPrompt:
    "You evaluate student answers like a board examiner. Return strict JSON only with keys marksAwarded, totalMarks, improvements, mistakes, idealAnswer, scoringExplanation, grammarIssues, topperAnswer.",
  userPrompt: JSON.stringify(input),
});

export const buildStudyPlanPrompt = (input: StudyPlanInput) => ({
  systemPrompt:
    "You are an AI study planner for school students. Return strict JSON only with keys title, goals, dailyGoals, recommendations, revisionSchedule, weakTopics.",
  userPrompt: JSON.stringify(input),
});

export const buildMockTestPrompt = (input: MockTestInput) => ({
  systemPrompt:
    "You generate mock tests for Indian board exam students. Return strict JSON only with keys title, questions, answerKey.",
  userPrompt: JSON.stringify(input),
});

export const buildStudyChatPrompt = (message: string, context?: Record<string, unknown>) => ({
  systemPrompt:
    "You are VEDAAPEX Study Assistant. Give concise, practical guidance for class 9 to 12 students. If you use structured advice, keep it compact.",
  userPrompt: JSON.stringify({
    message,
    context,
  }),
});

export const buildStudyPackPrompt = (input: {
  classLevel: number;
  subject: string;
  board: string;
  year: number;
  title: string;
  ocrText: string;
}) => ({
  systemPrompt:
    "You are a board-exam study strategist. Return strict JSON only with keys questionAnswerBank, rapidRevisionNotes, studyStrategy. questionAnswerBank must include likelyQuestions, idealAnswers, and marksBreakdown.",
  userPrompt: JSON.stringify(input),
});
