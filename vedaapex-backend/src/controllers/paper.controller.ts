import type { Request, Response } from "express";
import { StatusCodes } from "http-status-codes";

import { paperService } from "../services/paper.service";
import { asyncHandler } from "../utils/async-handler";
import { successResponse } from "../utils/response";

export const paperController = {
  list: asyncHandler(async (req, res) => {
    const result = await paperService.listPapers(req.query as never);
    res.status(StatusCodes.OK).json(successResponse(result.items, result.pagination));
  }),

  coverage: asyncHandler(async (_req, res) => {
    const result = await paperService.getCoverageMatrix();
    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  getById: asyncHandler(async (req, res) => {
    const paper = await paperService.getPaperById(req.params.paperId!);
    await paperService.incrementView(req.params.paperId!);
    res.status(StatusCodes.OK).json(successResponse(paper));
  }),

  trending: asyncHandler(async (_req, res) => {
    const papers = await paperService.getTrendingPapers();
    res.status(StatusCodes.OK).json(successResponse(papers));
  }),

  uploadUrl: asyncHandler(async (req, res) => {
    const data = await paperService.createPaperUploadUrl(req.body);
    res.status(StatusCodes.OK).json(successResponse(data));
  }),

  uploadPaper: asyncHandler(async (req, res) => {
    const paper = await paperService.createPaperFromUpload(req.body, req.file!, req.authUser?.id);
    res.status(StatusCodes.CREATED).json(successResponse(paper));
  }),

  bulkImport: asyncHandler(async (req, res) => {
    const result = await paperService.bulkImportPapers(req.body.papers, req.authUser?.id);
    res.status(StatusCodes.CREATED).json(successResponse(result, { total: result.length }));
  }),

  updatePaper: asyncHandler(async (req, res) => {
    const paper = await paperService.updatePaper(req.params.paperId!, req.body);
    res.status(StatusCodes.OK).json(successResponse(paper));
  }),

  deletePaper: asyncHandler(async (req, res) => {
    await paperService.deletePaper(req.params.paperId!);
    res.status(StatusCodes.OK).json(successResponse({ deleted: true }));
  }),

  bookmarkPaper: asyncHandler(async (req, res) => {
    await paperService.bookmarkPaper(req.authUser!.id, req.params.paperId!);
    res.status(StatusCodes.OK).json(successResponse({ bookmarked: true }));
  }),

  removeBookmark: asyncHandler(async (req, res) => {
    await paperService.removeBookmark(req.authUser!.id, req.params.paperId!);
    res.status(StatusCodes.OK).json(successResponse({ removed: true }));
  }),

  downloadPaper: asyncHandler(async (req, res) => {
    const payload = await paperService.recordDownload(req.params.paperId!, req.authUser?.id, req.ip);
    res.status(StatusCodes.OK).json(successResponse(payload));
  }),
};
