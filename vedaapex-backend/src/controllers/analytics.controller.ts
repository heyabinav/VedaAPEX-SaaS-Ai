import { StatusCodes } from "http-status-codes";

import { analyticsService } from "../services/analytics.service";
import { asyncHandler } from "../utils/async-handler";
import { successResponse } from "../utils/response";

export const analyticsController = {
  leaderboard: asyncHandler(async (req, res) => {
    const result = await analyticsService.getLeaderboard(req.query.scope as string | undefined, req.query.subject as string | undefined);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),
};
