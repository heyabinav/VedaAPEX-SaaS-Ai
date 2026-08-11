"""
Authentication service – resolves the current user from:
  1. x-api-key header  →  direct API key lookup
  2. Bearer token      →  try as API key first, then Supabase token

Key fixes:
  • Added detailed logging for every resolution path
  • Wrapped Supabase verification in broader exception handling
"""

import logging

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, select

from ..models.user import User
from .api_key_service import APIKeyService
from .supabase_service import SupabaseService

logger = logging.getLogger("auth.service")


class AuthService:
    @staticmethod
    def _get_api_key_user(session: Session, api_key: str | None) -> User | None:
        if not api_key:
            return None

        user = session.exec(select(User).where(User.api_key == api_key)).first()
        if user and not user.is_active:
            raise HTTPException(status_code=401, detail="Account deactivated.")
        return user

    @staticmethod
    def get_user_from_any_api_key(
        session: Session,
        x_api_key: str | None = None,
        bearer_token: str | None = None,
    ) -> User | None:
        for candidate in (x_api_key, bearer_token):
            if not candidate:
                continue

            # Try hashed API key table first
            user = APIKeyService.validate_api_key(session, candidate)
            if not user:
                # Fall back to the legacy User.api_key column
                user = AuthService._get_api_key_user(session, candidate)

            if user:
                if not user.is_active:
                    raise HTTPException(status_code=401, detail="Account deactivated.")
                logger.info("Authenticated via API key user_id=%s", user.id)
                return user

        return None

    @staticmethod
    async def get_authenticated_user(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None,
        session: Session,
    ) -> User:
        bearer_token = credentials.credentials if credentials else None

        # 1) Try API key paths
        user = AuthService.get_user_from_any_api_key(
            session,
            x_api_key=request.headers.get("x-api-key"),
            bearer_token=bearer_token,
        )

        if user:
            request.state.user_id = user.id
            return user

        # 2) Require bearer token for Supabase auth
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Login required. Supply a Supabase Bearer token or x-api-key.",
            )

        # 3) Verify with Supabase
        logger.info("Verifying bearer token via Supabase …")
        try:
            supabase_user = await SupabaseService.verify_access_token(credentials.credentials)
        except RuntimeError as exc:
            logger.error("Supabase verification failed: %s", exc)
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Unexpected error verifying Supabase token")
            raise HTTPException(status_code=500, detail=f"Token verification error: {exc}") from exc

        if not supabase_user:
            raise HTTPException(status_code=401, detail="Invalid or expired Supabase token.")

        user, _ = SupabaseService.get_or_create_local_user(
            session, supabase_user, email_fallback=supabase_user.get("email")
        )
        if not user.is_active:
            raise HTTPException(status_code=401, detail="Account deactivated.")

        logger.info("Authenticated via Supabase token user_id=%s", user.id)
        request.state.user_id = user.id
        return user
