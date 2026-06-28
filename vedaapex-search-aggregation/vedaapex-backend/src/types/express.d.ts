import type { AuthUser } from "./api";

declare global {
  namespace Express {
    interface Request {
      authUser?: AuthUser;
      requestId?: string;
      csrfToken?: () => string;
    }
  }
}

export {};
