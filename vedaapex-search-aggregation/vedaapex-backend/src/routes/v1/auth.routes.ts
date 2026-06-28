import { Router } from "express";

import { authController } from "../../controllers/auth.controller";
import { authenticate } from "../../middleware/authenticate";
import { authRateLimiter } from "../../middleware/rate-limiter";
import { validate } from "../../middleware/validate";
import {
  emailVerificationConfirmSchema,
  firebaseExchangeSchema,
  googleLoginSchema,
  refreshTokenSchema,
  requestOtpSchema,
  verifyOtpSchema,
} from "../../validators/auth.validator";

export const authRouter = Router();

/**
 * @openapi
 * /auth/google:
 *   post:
 *     summary: Login or register with Google ID token.
 */
authRouter.post("/google", authRateLimiter, validate(googleLoginSchema), authController.googleLogin);
authRouter.post("/firebase/exchange", authRateLimiter, validate(firebaseExchangeSchema), authController.firebaseExchange);
authRouter.post("/otp/request", authRateLimiter, validate(requestOtpSchema), authController.requestOtp);
authRouter.post("/otp/verify", authRateLimiter, validate(verifyOtpSchema), authController.verifyOtp);
authRouter.post("/refresh", validate(refreshTokenSchema), authController.refresh);
authRouter.post("/logout", authenticate, authController.logout);
authRouter.get("/me", authenticate, authController.me);
authRouter.post("/email/verification/request", authenticate, authController.requestEmailVerification);
authRouter.post(
  "/email/verification/confirm",
  authenticate,
  validate(emailVerificationConfirmSchema),
  authController.confirmEmailVerification,
);
