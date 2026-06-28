import { AuthProvider, SessionStatus, UserRole } from "@prisma/client";
import { OAuth2Client } from "google-auth-library";

import { env } from "../config/env";
import { getFirebaseApp } from "../config/firebase";
import { prisma } from "../config/prisma";
import { redis } from "../config/redis";
import { hashToken, signAccessToken, signRefreshToken, verifyRefreshToken } from "../auth/jwt";
import { ApiError } from "../utils/api-error";
import { durationToMs } from "../utils/time";
import { activityService } from "./activity.service";

const googleClient = env.GOOGLE_CLIENT_ID ? new OAuth2Client(env.GOOGLE_CLIENT_ID) : null;

type RequestMeta = {
  ipAddress?: string | null;
  userAgent?: string | null;
};

type TokenBundle = {
  accessToken: string;
  refreshToken: string;
  sessionId: string;
};

const createSessionTokens = async (
  user: { id: string; role: UserRole; email?: string | null; phone?: string | null },
  meta?: RequestMeta,
): Promise<TokenBundle> => {
  const provisionalPayload = {
    id: user.id,
    role: user.role,
    email: user.email ?? undefined,
    phone: user.phone ?? undefined,
  };
  const session = await prisma.session.create({
    data: {
      userId: user.id,
      refreshTokenHash: "pending",
      ipAddress: meta?.ipAddress ?? undefined,
      userAgent: meta?.userAgent ?? undefined,
      expiresAt: new Date(Date.now() + durationToMs(env.JWT_REFRESH_TTL)),
    },
  });

  const payload = {
    ...provisionalPayload,
    sessionId: session.id,
  };

  const accessToken = signAccessToken(payload);
  const refreshToken = signRefreshToken(payload);

  await prisma.session.update({
    where: { id: session.id },
    data: {
      refreshTokenHash: hashToken(refreshToken),
    },
  });

  return {
    accessToken,
    refreshToken,
    sessionId: session.id,
  };
};

const buildAuthResponse = async (userId: string, meta?: RequestMeta) => {
  const user = await prisma.user.findUniqueOrThrow({
    where: { id: userId },
  });

  const tokens = await createSessionTokens(user, meta);

  return {
    user,
    ...tokens,
  };
};

const sanitizePhone = (phone: string) => phone.replace(/[^\d+]/g, "");

export const authService = {
  async loginWithGoogle(idToken: string, meta?: RequestMeta) {
    if (!googleClient || !env.GOOGLE_CLIENT_ID) {
      throw new ApiError(500, "Google authentication is not configured.");
    }

    const ticket = await googleClient.verifyIdToken({
      idToken,
      audience: env.GOOGLE_CLIENT_ID,
    });
    const payload = ticket.getPayload();

    if (!payload?.email) {
      throw new ApiError(401, "Google token does not contain a verified email.");
    }

    const user = await prisma.user.upsert({
      where: { email: payload.email },
      update: {
        name: payload.name ?? "VEDAAPEX User",
        avatarUrl: payload.picture,
        lastLoginAt: new Date(),
        emailVerified: Boolean(payload.email_verified),
        provider: AuthProvider.GOOGLE,
      },
      create: {
        email: payload.email,
        name: payload.name ?? "VEDAAPEX User",
        avatarUrl: payload.picture,
        role: UserRole.USER,
        emailVerified: Boolean(payload.email_verified),
        provider: AuthProvider.GOOGLE,
        lastLoginAt: new Date(),
      },
    });

    await activityService.log({
      userId: user.id,
      action: "auth.google.login",
      ipAddress: meta?.ipAddress,
      userAgent: meta?.userAgent,
    });

    return buildAuthResponse(user.id, meta);
  },

  async exchangeFirebaseToken(firebaseToken: string, meta?: RequestMeta) {
    const app = getFirebaseApp();

    if (!app) {
      throw new ApiError(500, "Firebase authentication is not configured.");
    }

    const decoded = await app.auth().verifyIdToken(firebaseToken);

    const user = await prisma.user.upsert({
      where: decoded.email ? { email: decoded.email } : { firebaseUid: decoded.uid },
      update: {
        firebaseUid: decoded.uid,
        email: decoded.email,
        phone: decoded.phone_number,
        name: decoded.name ?? decoded.phone_number ?? "VEDAAPEX User",
        avatarUrl: decoded.picture,
        emailVerified: Boolean(decoded.email_verified),
        phoneVerified: Boolean(decoded.phone_number),
        provider: AuthProvider.FIREBASE,
        lastLoginAt: new Date(),
      },
      create: {
        firebaseUid: decoded.uid,
        email: decoded.email,
        phone: decoded.phone_number,
        name: decoded.name ?? decoded.phone_number ?? "VEDAAPEX User",
        avatarUrl: decoded.picture,
        emailVerified: Boolean(decoded.email_verified),
        phoneVerified: Boolean(decoded.phone_number),
        provider: AuthProvider.FIREBASE,
        lastLoginAt: new Date(),
      },
    });

    await activityService.log({
      userId: user.id,
      action: "auth.firebase.exchange",
      ipAddress: meta?.ipAddress,
      userAgent: meta?.userAgent,
    });

    return buildAuthResponse(user.id, meta);
  },

  async requestOtp(phone: string) {
    const normalizedPhone = sanitizePhone(phone);
    const otp = env.OTP_MOCK_DELIVERY ? env.OTP_DEV_BYPASS_CODE : String(Math.floor(100000 + Math.random() * 900000));

    await redis.set(`otp:${normalizedPhone}`, otp, "EX", env.OTP_TTL_SECONDS);
    await redis.del(`otp:attempts:${normalizedPhone}`);

    return {
      phone: normalizedPhone,
      expiresInSeconds: env.OTP_TTL_SECONDS,
      devCode: env.NODE_ENV !== "production" ? otp : undefined,
    };
  },

  async verifyOtp(phone: string, otp: string, name?: string, meta?: RequestMeta) {
    const normalizedPhone = sanitizePhone(phone);
    const attemptsKey = `otp:attempts:${normalizedPhone}`;
    const storedOtp = await redis.get(`otp:${normalizedPhone}`);

    if (!storedOtp) {
      throw new ApiError(401, "OTP expired or not found.");
    }

    const attempts = Number((await redis.get(attemptsKey)) ?? 0);

    if (attempts >= env.OTP_MAX_ATTEMPTS) {
      throw new ApiError(429, "Too many OTP attempts.");
    }

    if (storedOtp !== otp) {
      await redis.incr(attemptsKey);
      await redis.expire(attemptsKey, env.OTP_TTL_SECONDS);
      throw new ApiError(401, "Invalid OTP.");
    }

    await redis.del(`otp:${normalizedPhone}`);
    await redis.del(attemptsKey);

    const user = await prisma.user.upsert({
      where: { phone: normalizedPhone },
      update: {
        name: name ?? normalizedPhone,
        phoneVerified: true,
        provider: AuthProvider.OTP,
        lastLoginAt: new Date(),
      },
      create: {
        phone: normalizedPhone,
        name: name ?? normalizedPhone,
        phoneVerified: true,
        provider: AuthProvider.OTP,
        role: UserRole.USER,
        lastLoginAt: new Date(),
      },
    });

    await activityService.log({
      userId: user.id,
      action: "auth.otp.verify",
      ipAddress: meta?.ipAddress,
      userAgent: meta?.userAgent,
    });

    return buildAuthResponse(user.id, meta);
  },

  async refreshSession(refreshToken: string, meta?: RequestMeta) {
    const payload = verifyRefreshToken(refreshToken);

    if (!payload.sessionId) {
      throw new ApiError(401, "Invalid refresh token payload.");
    }

    const session = await prisma.session.findUnique({
      where: { id: payload.sessionId },
      include: {
        user: true,
      },
    });

    if (!session || session.status !== SessionStatus.ACTIVE || session.refreshTokenHash !== hashToken(refreshToken)) {
      throw new ApiError(401, "Refresh session is invalid or revoked.");
    }

    if (session.expiresAt.getTime() < Date.now()) {
      await prisma.session.update({
        where: { id: session.id },
        data: {
          status: SessionStatus.EXPIRED,
        },
      });
      throw new ApiError(401, "Refresh session expired.");
    }

    const accessToken = signAccessToken({
      id: session.user.id,
      role: session.user.role,
      email: session.user.email ?? undefined,
      phone: session.user.phone ?? undefined,
      sessionId: session.id,
    });
    const newRefreshToken = signRefreshToken({
      id: session.user.id,
      role: session.user.role,
      email: session.user.email ?? undefined,
      phone: session.user.phone ?? undefined,
      sessionId: session.id,
    });

    await prisma.session.update({
      where: { id: session.id },
      data: {
        refreshTokenHash: hashToken(newRefreshToken),
        ipAddress: meta?.ipAddress ?? session.ipAddress ?? undefined,
        userAgent: meta?.userAgent ?? session.userAgent ?? undefined,
        expiresAt: new Date(Date.now() + durationToMs(env.JWT_REFRESH_TTL)),
      },
    });

    return {
      accessToken,
      refreshToken: newRefreshToken,
      sessionId: session.id,
      user: session.user,
    };
  },

  async logout(sessionId?: string) {
    if (!sessionId) {
      return;
    }

    await prisma.session.updateMany({
      where: { id: sessionId },
      data: {
        status: SessionStatus.REVOKED,
        revokedAt: new Date(),
      },
    });
  },

  async getProfile(userId: string) {
    return prisma.user.findUniqueOrThrow({
      where: { id: userId },
      include: {
        studyPlans: {
          take: 3,
          orderBy: { createdAt: "desc" },
        },
        progressRecords: true,
      },
    });
  },

  async requestEmailVerification(userId: string) {
    const user = await prisma.user.findUniqueOrThrow({
      where: { id: userId },
    });

    if (!user.email) {
      throw new ApiError(400, "User does not have an email address.");
    }

    const token = crypto.randomUUID().replace(/-/g, "");
    await redis.set(`email-verification:${token}`, user.id, "EX", 60 * 60 * 24);

    return {
      email: user.email,
      expiresInSeconds: 60 * 60 * 24,
      devToken: env.NODE_ENV !== "production" ? token : undefined,
    };
  },

  async confirmEmailVerification(token: string, userId?: string) {
    const storedUserId = await redis.get(`email-verification:${token}`);

    if (!storedUserId) {
      throw new ApiError(400, "Verification token is invalid or expired.");
    }

    if (userId && storedUserId !== userId) {
      throw new ApiError(403, "Verification token does not belong to the authenticated user.");
    }

    const user = await prisma.user.update({
      where: { id: storedUserId },
      data: {
        emailVerified: true,
      },
    });

    await redis.del(`email-verification:${token}`);

    return user;
  },
};
