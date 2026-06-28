import { StatusCodes } from "http-status-codes";

import { aiService } from "../services/ai.service";
import { studyService } from "../services/study.service";
import { asyncHandler } from "../utils/async-handler";
import { successResponse } from "../utils/response";

export const studyController = {
  generatePlan: asyncHandler(async (req, res) => {
    const result = await aiService.generateStudyPlan({
      ...req.body,
      userId: req.authUser!.id,
    });
    res.status(StatusCodes.CREATED).json(successResponse(result));
  }),

  listPlans: asyncHandler(async (req, res) => {
    const result = await studyService.getStudyPlans(req.authUser!.id);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  updateProgress: asyncHandler(async (req, res) => {
    const result = await studyService.upsertProgress(req.authUser!.id, req.body);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  dashboard: asyncHandler(async (req, res) => {
    const result = await studyService.getStudyDashboard(req.authUser!.id);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  generateMockTest: asyncHandler(async (req, res) => {
    const result = await aiService.generateMockTest({
      ...req.body,
      userId: req.authUser!.id,
    });
    res.status(StatusCodes.CREATED).json(successResponse(result));
  }),
};
