"""
Supabase authentication service.

Handles:
  • Sign‑up / sign‑in via Supabase GoTrue HTTP API
  • Access‑token verification
  • Local‑user upsert (get‑or‑create)

Key fixes:
  • Added detailed logging at every step
  • Wrapped local DB operations in try/except
  • Made get_or_create_local_user resilient to IntegrityError
    (race‑condition / duplicate email)
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

import httpx
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlmodel import Session, select

from ..core.config import settings
from ..core.security import get_password_hash
from ..models.user import User
from .token_service import TokenService

logger = logging.getLogger("auth.supabase")


class SupabaseAuthError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SupabaseService:
    @staticmethod
    def is_configured() -> bool:
        return bool(
            settings.SUPABASE_URL and (settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY)
        )

    @staticmethod
    def _base_url() -> str:
        if not settings.SUPABASE_URL:
            raise RuntimeError("Supabase auth is not configured (SUPABASE_URL missing).")
        return settings.SUPABASE_URL.rstrip("/")

    @staticmethod
    def _headers(access_token: Optional[str] = None) -> dict[str, str]:
        api_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        if not api_key:
            raise RuntimeError("Supabase auth is not configured (SUPABASE_KEY missing).")

        headers = {
            "apikey": api_key,
            "Content-Type": "application/json",
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers

    @staticmethod
    def _extract_error(payload: Any) -> str:
        if isinstance(payload, dict):
            for key in ("msg", "message", "error_description", "error"):
                value = payload.get(key)
                if value:
                    return str(value)
        return "Supabase request failed."

    @staticmethod
    def _safe_json(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return {"message": response.text or "Supabase request failed."}

    # ─── verify_access_token ──────────────────────────────
    @staticmethod
    async def verify_access_token(access_token: str) -> Optional[dict[str, Any]]:
        if not SupabaseService.is_configured():
            raise RuntimeError("Supabase auth is not configured.")

        logger.debug("Verifying access token …")
        try:
            async with httpx.AsyncClient(timeout=settings.SUPABASE_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    f"{SupabaseService._base_url()}/auth/v1/user",
                    headers=SupabaseService._headers(access_token),
                )
        except httpx.HTTPError as exc:
            logger.error("Supabase /auth/v1/user request failed: %s", exc)
            raise RuntimeError("Supabase auth is unavailable.") from exc

        if response.status_code == 200:
            return SupabaseService._safe_json(response)
        if response.status_code in {401, 403}:
            logger.info("Token verification returned %s (invalid/expired)", response.status_code)
            return None

        raise SupabaseAuthError(
            SupabaseService._extract_error(SupabaseService._safe_json(response)),
            status_code=response.status_code,
        )

    # ─── sign_up ──────────────────────────────────────────
    @staticmethod
    async def sign_up(
        email: str, password: str, metadata: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        if not SupabaseService.is_configured():
            raise RuntimeError("Supabase auth is not configured.")

        payload: dict[str, Any] = {"email": email, "password": password}
        if metadata:
            payload["data"] = metadata

        logger.info("Calling Supabase /auth/v1/signup for email=%s", email)
        try:
            async with httpx.AsyncClient(timeout=settings.SUPABASE_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{SupabaseService._base_url()}/auth/v1/signup",
                    headers=SupabaseService._headers(),
                    json=payload,
                )
        except httpx.HTTPError as exc:
            logger.error("Supabase signup HTTP error: %s", exc)
            raise RuntimeError("Supabase auth is unavailable.") from exc

        data = SupabaseService._safe_json(response)
        logger.info("Supabase signup response status=%s", response.status_code)

        if response.status_code not in {200, 201}:
            error_msg = SupabaseService._extract_error(data)
            logger.warning("Supabase signup error: %s (status=%s)", error_msg, response.status_code)
            raise SupabaseAuthError(error_msg, status_code=response.status_code)

        return data

    # ─── sign_in_with_password ────────────────────────────
    @staticmethod
    async def sign_in_with_password(email: str, password: str) -> dict[str, Any]:
        if not SupabaseService.is_configured():
            raise RuntimeError("Supabase auth is not configured.")

        logger.info("Calling Supabase sign_in for email=%s", email)
        try:
            async with httpx.AsyncClient(timeout=settings.SUPABASE_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{SupabaseService._base_url()}/auth/v1/token?grant_type=password",
                    headers=SupabaseService._headers(),
                    json={"email": email, "password": password},
                )
        except httpx.HTTPError as exc:
            logger.error("Supabase sign_in HTTP error: %s", exc)
            raise RuntimeError("Supabase auth is unavailable.") from exc

        data = SupabaseService._safe_json(response)
        if response.status_code != 200:
            error_msg = SupabaseService._extract_error(data)
            logger.warning("Supabase sign_in error: %s", error_msg)
            raise SupabaseAuthError(error_msg, status_code=response.status_code)

        logger.info("Supabase sign_in success for email=%s", email)
        return data

    # ─── sign_out ─────────────────────────────────────────
    @staticmethod
    async def sign_out(access_token: str) -> None:
        if not SupabaseService.is_configured():
            return

        try:
            async with httpx.AsyncClient(timeout=settings.SUPABASE_TIMEOUT_SECONDS) as client:
                await client.post(
                    f"{SupabaseService._base_url()}/auth/v1/logout",
                    headers=SupabaseService._headers(access_token),
                )
        except httpx.HTTPError:
            logger.warning("Supabase sign_out request failed (ignored)")
            return

    # ─── get_or_create_local_user ─────────────────────────
    @staticmethod
    def get_or_create_local_user(
        session: Session,
        supabase_user: dict[str, Any],
        referral_code_input: Optional[str] = None,
        email_fallback: Optional[str] = None,
    ) -> tuple[User, bool]:
        email = (
            supabase_user.get("email")
            or email_fallback
            or f"{supabase_user.get('id', uuid.uuid4().hex)}@supabase.local"
        )
        metadata = supabase_user.get("user_metadata") or {}
        full_name = metadata.get("full_name") or metadata.get("name") or supabase_user.get("phone")

        logger.info("get_or_create_local_user email=%s", email)

        user = session.exec(select(User).where(User.email == email)).first()
        created = False

        if not user:
            created = True
            referral_code = f"VEDA{uuid.uuid4().hex[:8].upper()}"
            logger.info(
                "Creating new local user email=%s referral_code=%s",
                email,
                referral_code,
            )
            user = User(
                email=email,
                hashed_password=get_password_hash(uuid.uuid4().hex),
                full_name=full_name,
                referral_code=referral_code,
                referred_by=referral_code_input,
                role="USER",
                last_login_at=datetime.utcnow(),
            )
            session.add(user)
            try:
                session.commit()
                session.refresh(user)
            except IntegrityError:
                # Race condition: another request created the user between our
                # SELECT and INSERT. Roll back and re‑fetch.
                logger.warning(
                    "IntegrityError creating user %s — likely race condition, re‑fetching",
                    email,
                )
                session.rollback()
                user = session.exec(select(User).where(User.email == email)).first()
                if not user:
                    raise  # genuinely broken
                created = False

            if created:
                try:
                    TokenService.create_wallet(session, user.id)
                    logger.info("Wallet created for user_id=%s", user.id)
                except Exception as e:
                    logger.warning(
                        "Wallet creation in get_or_create failed (will retry later): %s",
                        e,
                    )
        else:
            if full_name and user.full_name != full_name:
                user.full_name = full_name
            user.last_login_at = datetime.utcnow()
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("Existing user found user_id=%s", user.id)

        return user, created
