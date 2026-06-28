import { StatusCodes } from "http-status-codes";

import { mediaService } from "../services/media.service";
import { asyncHandler } from "../utils/async-handler";
import { successResponse } from "../utils/response";

export const mediaController = {
  createUploadUrl: asyncHandler(async (req, res) => {
    const result = await mediaService.createUploadUrl(req.body);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  registerAsset: asyncHandler(async (req, res) => {
    const result = await mediaService.registerUploadedAsset(req.authUser!.id, req.body);
    res.status(StatusCodes.CREATED).json(successResponse(result));
  }),

  uploadAsset: asyncHandler(async (req, res) => {
    const result = await mediaService.uploadDirectAsset(req.authUser!.id, req.body, req.file);
    res.status(StatusCodes.CREATED).json(successResponse(result));
  }),

  listAssets: asyncHandler(async (req, res) => {
    const result = await mediaService.listAssets(req.authUser!.id);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  createJob: asyncHandler(async (req, res) => {
    const result = await mediaService.createProcessingJob(req.authUser!.id, req.body);
    res.status(StatusCodes.CREATED).json(successResponse(result));
  }),

  listJobs: asyncHandler(async (req, res) => {
    const result = await mediaService.listJobs(req.authUser!.id);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  getJob: asyncHandler(async (req, res) => {
    const result = await mediaService.getJob(req.authUser!.id, req.params.jobId!);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),
};
