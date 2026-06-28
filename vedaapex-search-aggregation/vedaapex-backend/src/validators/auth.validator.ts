import { z } from "zod";

export const googleLoginSchema = z.object({
  idToken: z.string().min(10),
});

export const firebaseExchangeSchema = z.object({
  firebaseToken: z.string().min(10),
});

export const requestOtpSchema = z.object({
  phone: z.string().min(10).max(20),
});

export const verifyOtpSchema = z.object({
  phone: z.string().min(10).max(20),
  otp: z.string().length(6),
  name: z.string().min(2).max(80).optional(),
});

export const refreshTokenSchema = z.object({
  refreshToken: z.string().min(20).optional(),
});

export const emailVerificationConfirmSchema = z.object({
  token: z.string().min(10),
});
