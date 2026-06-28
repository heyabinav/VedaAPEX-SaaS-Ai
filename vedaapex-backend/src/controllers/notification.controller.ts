import { StatusCodes } from "http-status-codes";

import { notificationService } from "../services/notification.service";
import { asyncHandler } from "../utils/async-handler";
import { successResponse } from "../utils/response";

export const notificationController = {
  list: asyncHandler(async (req, res) => {
    const result = await notificationService.list(req.authUser!.id);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  markRead: asyncHandler(async (req, res) => {
    await notificationService.markRead(req.authUser!.id, req.params.notificationId!);
    res.status(StatusCodes.OK).json(successResponse({ read: true }));
  }),
};
