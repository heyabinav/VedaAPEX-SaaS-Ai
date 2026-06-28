import { StatusCodes } from "http-status-codes";
import { UserRole } from "@prisma/client";

import { adminService } from "../services/admin.service";
import { analyticsService } from "../services/analytics.service";
import { paperService } from "../services/paper.service";
import { asyncHandler } from "../utils/async-handler";
import { successResponse } from "../utils/response";

export const adminController = {
  listUsers: asyncHandler(async (req, res) => {
    const page = Number(req.query.page ?? 1);
    const limit = Number(req.query.limit ?? 25);
    const result = await adminService.listUsers(page, limit);
    res.status(StatusCodes.OK).json(successResponse(result.items, { page: result.page, limit: result.limit, total: result.total }));
  }),

  updateUserRole: asyncHandler(async (req, res) => {
    const result = await adminService.updateUserRole(req.params.userId!, req.body.role as UserRole);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  revokeUserSessions: asyncHandler(async (req, res) => {
    await adminService.revokeUserSessions(req.params.userId!);
    res.status(StatusCodes.OK).json(successResponse({ revoked: true }));
  }),

  featurePaper: asyncHandler(async (req, res) => {
    const result = await paperService.featurePaper(req.params.paperId!, req.body.isFeatured ?? true);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  analyticsOverview: asyncHandler(async (_req, res) => {
    const result = await analyticsService.getAdminOverview();
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  paperAnalytics: asyncHandler(async (_req, res) => {
    const result = await analyticsService.getPaperAnalytics();
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  aiReports: asyncHandler(async (_req, res) => {
    const result = await adminService.listAiReports();
    res.status(StatusCodes.OK).json(successResponse(result));
  }),
};
