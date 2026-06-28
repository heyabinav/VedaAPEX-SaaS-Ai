import type { Request, Response } from "express";
import { StatusCodes } from "http-status-codes";

import { env } from "../config/env";
import { authService } from "../services/auth.service";
import { asyncHandler } from "../utils/async-handler";
import { ApiError } from "../utils/api-error";
import { successResponse } from "../utils/response";

const getRequestMeta = (req: Request) => ({
  ipAddress: req.ip,
  userAgent: req.headers["user-agent"] ?? null,
});

const attachRefreshCookie = (res: Response, refreshToken: string) => {
  res.cookie(env.SESSION_COOKIE_NAME, refreshToken, {
    httpOnly: true,
    secure: env.NODE_ENV === "production",
    sameSite: "strict",
    maxAge: 1000 * 60 * 60 * 24 * 30,
  });
};

export const authController = {
  googleLogin: asyncHandler(async (req, res) => {
    const payload = await authService.loginWithGoogle(req.body.idToken, getRequestMeta(req));
    attachRefreshCookie(res, payload.refreshToken);
    res.status(StatusCodes.OK).json(successResponse(payload));
  }),

  firebaseExchange: asyncHandler(async (req, res) => {
    const payload = await authService.exchangeFirebaseToken(req.body.firebaseToken, getRequestMeta(req));
    attachRefreshCookie(res, payload.refreshToken);
    res.status(StatusCodes.OK).json(successResponse(payload));
  }),

  requestOtp: asyncHandler(async (req, res) => {
    const payload = await authService.requestOtp(req.body.phone);
    res.status(StatusCodes.OK).json(successResponse(payload));
  }),

  verifyOtp: asyncHandler(async (req, res) => {
    const payload = await authService.verifyOtp(req.body.phone, req.body.otp, req.body.name, getRequestMeta(req));
    attachRefreshCookie(res, payload.refreshToken);
    res.status(StatusCodes.OK).json(successResponse(payload));
  }),

  refresh: asyncHandler(async (req, res) => {
    const refreshToken = req.body.refreshToken ?? req.cookies[env.SESSION_COOKIE_NAME];
    if (!refreshToken) {
      throw new ApiError(StatusCodes.UNAUTHORIZED, "Refresh token is required.");
    }
    const payload = await authService.refreshSession(refreshToken, getRequestMeta(req));
    attachRefreshCookie(res, payload.refreshToken);
    res.status(StatusCodes.OK).json(successResponse(payload));
  }),

  logout: asyncHandler(async (req, res) => {
    await authService.logout(req.authUser?.sessionId);
    res.clearCookie(env.SESSION_COOKIE_NAME);
    res.status(StatusCodes.OK).json(successResponse({ loggedOut: true }));
  }),

  me: asyncHandler(async (req, res) => {
    const profile = await authService.getProfile(req.authUser!.id);
    res.status(StatusCodes.OK).json(successResponse(profile));
  }),

  requestEmailVerification: asyncHandler(async (req, res) => {
    const payload = await authService.requestEmailVerification(req.authUser!.id);
    res.status(StatusCodes.OK).json(successResponse(payload));
  }),

  confirmEmailVerification: asyncHandler(async (req, res) => {
    const payload = await authService.confirmEmailVerification(req.body.token, req.authUser?.id);
    res.status(StatusCodes.OK).json(successResponse(payload));
  }),
};
