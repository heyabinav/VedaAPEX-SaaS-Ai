import { StatusCodes } from "http-status-codes";

import { enqueuePaperAnalysisJob } from "../queues/paper-processing.queue";
import { aiService } from "../services/ai.service";
import { asyncHandler } from "../utils/async-handler";
import { successResponse } from "../utils/response";

export const aiController = {
  analyzePaper: asyncHandler(async (req, res) => {
    if (req.body.async) {
      await enqueuePaperAnalysisJob(req.params.paperId!, req.body.force);
      res.status(StatusCodes.ACCEPTED).json(
        successResponse({
          queued: true,
          paperId: req.params.paperId,
          force: req.body.force,
        }),
      );
      return;
    }

    const result = await aiService.analyzePaper(req.params.paperId!, req.body.force);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  generateStudyPack: asyncHandler(async (req, res) => {
    const result = await aiService.generateStudyPack(req.params.paperId!, req.body.force);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  evaluateAnswer: asyncHandler(async (req, res) => {
    const result = await aiService.evaluateAnswer(
      {
        ...req.body,
        userId: req.authUser!.id,
      },
      req.file,
    );
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  studyChat: asyncHandler(async (req, res) => {
    const result = await aiService.studyChat(req.authUser!.id, req.body.message, req.body.context);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),
};
