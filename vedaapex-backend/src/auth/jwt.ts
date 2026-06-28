import { createHash } from "node:crypto";

import jwt, { type SignOptions } from "jsonwebtoken";

import { env } from "../config/env";
import type { AuthUser } from "../types/api";

type TokenPayload = AuthUser & {
  type: "access" | "refresh";
};

export const signAccessToken = (payload: AuthUser) =>
  jwt.sign(
    {
      ...payload,
      type: "access",
    },
    env.JWT_ACCESS_SECRET,
    {
      expiresIn: env.JWT_ACCESS_TTL as SignOptions["expiresIn"],
      issuer: env.JWT_ISSUER,
      audience: env.JWT_AUDIENCE,
    },
  );

export const signRefreshToken = (payload: AuthUser) =>
  jwt.sign(
    {
      ...payload,
      type: "refresh",
    },
    env.JWT_REFRESH_SECRET,
    {
      expiresIn: env.JWT_REFRESH_TTL as SignOptions["expiresIn"],
      issuer: env.JWT_ISSUER,
      audience: env.JWT_AUDIENCE,
    },
  );

export const verifyAccessToken = (token: string) =>
  jwt.verify(token, env.JWT_ACCESS_SECRET, {
    issuer: env.JWT_ISSUER,
    audience: env.JWT_AUDIENCE,
  }) as TokenPayload;

export const verifyRefreshToken = (token: string) =>
  jwt.verify(token, env.JWT_REFRESH_SECRET, {
    issuer: env.JWT_ISSUER,
    audience: env.JWT_AUDIENCE,
  }) as TokenPayload;

export const hashToken = (token: string) => createHash("sha256").update(token).digest("hex");
