"""OAuth router for GitHub and Google via Supabase."""

import asyncio
import logging
import os
import uuid
from typing import Any, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.session import get_session
from app.models.user import User
from app.services.token_service import TokenService

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    from supabase import Client, create_client
except ImportError:  # pragma: no cover
    Client = Any
    create_client = None

logger = logging.getLogger("auth.oauth")
router = APIRouter()

if load_dotenv:
    load_dotenv()

SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", settings.SESSION_COOKIE_NAME)
SESSION_COOKIE_MAX_AGE = int(os.getenv("SESSION_COOKIE_MAX_AGE", settings.SESSION_COOKIE_MAX_AGE))
SESSION_COOKIE_SECURE = (
    os.getenv("SESSION_COOKIE_SECURE", str(settings.SESSION_COOKIE_SECURE)).lower() == "true"
)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", settings.SESSION_COOKIE_SAMESITE)

SUPABASE_URL = (os.getenv("SUPABASE_URL") or settings.SUPABASE_URL or "").rstrip("/")
SUPABASE_SERVICE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or settings.SUPABASE_SERVICE_ROLE_KEY
    or settings.SUPABASE_KEY
    or ""
)
FRONTEND_URL = os.getenv("FRONTEND_URL") or settings.FRONTEND_BASE_URL or ""
APP_BASE_URL = os.getenv("APP_BASE_URL") or settings.APP_BASE_URL or ""

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID") or os.getenv("GITHUB_OAUTH_CLIENT_ID") or settings.GITHUB_OAUTH_CLIENT_ID or ""
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET") or os.getenv("GITHUB_OAUTH_CLIENT_SECRET") or settings.GITHUB_OAUTH_CLIENT_SECRET or ""
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_OAUTH_CLIENT_ID") or settings.GOOGLE_OAUTH_CLIENT_ID or ""
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or settings.GOOGLE_OAUTH_CLIENT_SECRET or ""

supabase_client: Optional[Client] = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY and create_client:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("Supabase client initialized for OAuth router")
    except Exception as exc:
        logger.error("Failed to initialize Supabase client: %s", exc, exc_info=True)
        supabase_client = None
else:
    logger.warning("Supabase client not initialized for OAuth router")


def _get_supabase_client() -> Client:
    if supabase_client is None:
        raise HTTPException(status_code=500, detail="Supabase is not configured")
    return supabase_client


def _backend_callback_url(request: Request, provider: str) -> str:
    base = APP_BASE_URL.rstrip("/") if APP_BASE_URL else str(request.base_url).rstrip("/")
    return f"{base}/auth/callback?provider={provider}"


def _frontend_redirect_url(token: str, provider: str, email: Optional[str]) -> str:
    if not FRONTEND_URL:
        raise HTTPException(status_code=500, detail="FRONTEND_URL not configured")
    params = {
        "token": token,
        "provider": provider,
        "email": email or "",
    }
    separator = "&" if "?" in FRONTEND_URL else "?"
    return f"{FRONTEND_URL.rstrip('/')}{separator}{urlencode(params)}"


def _provider_from_state(state: Optional[str]) -> Optional[str]:
    if not state:
        return None
    state_value = state.strip().lower()
    if state_value.startswith("google:") or state_value == "google":
        return "google"
    if state_value.startswith("github:") or state_value == "github":
        return "github"
    if "google" in state_value:
        return "google"
    if "github" in state_value:
        return "github"
    return None


def _safe_get(data: Any, key: str, default: Any = None) -> Any:
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


def _extract_response_url(response: Any) -> Optional[str]:
    for key in ("url", "redirect_url", "provider_url", "authorization_url"):
        value = _safe_get(response, key)
        if value:
            return str(value)
    if isinstance(response, dict):
        for key in ("url", "redirect_url", "provider_url", "authorization_url"):
            value = response.get(key)
            if value:
                return str(value)
    return None


def _extract_session_payload(result: Any) -> tuple[dict[str, Any], dict[str, Any], Optional[str]]:
    if isinstance(result, dict):
        user = result.get("user") or {}
        session_data = result.get("session") or {}
        access_token = session_data.get("access_token") or result.get("access_token")
        return user or {}, session_data or {}, access_token

    user = _safe_get(result, "user") or {}
    session_data = _safe_get(result, "session") or {}
    access_token = _safe_get(session_data, "access_token") or _safe_get(result, "access_token")
    return user or {}, session_data or {}, access_token


async def _supabase_call(func):
    return await asyncio.to_thread(func)


async def _upsert_supabase_user_profile(user_payload: dict[str, Any], provider: str) -> None:
    try:
        client = _get_supabase_client()
        user_id = user_payload.get("id") or user_payload.get("sub") or user_payload.get("user_id")
        email = user_payload.get("email")
        meta = user_payload.get("user_metadata") or user_payload.get("app_metadata") or {}
        profile = {
            "id": str(user_id) if user_id else None,
            "email": email,
            "full_name": meta.get("full_name") or meta.get("name") or user_payload.get("name"),
            "provider": provider,
            "provider_id": str(user_id) if user_id else None,
            "avatar_url": user_payload.get("avatar_url") or user_payload.get("picture") or meta.get("avatar_url"),
        }
        payload = {key: value for key, value in profile.items() if value is not None}

        def _execute():
            return client.table("users").upsert(payload, on_conflict="email").execute()

        await _supabase_call(_execute)
    except Exception as exc:
        logger.warning("Supabase users upsert skipped/failed: %s", exc)


async def _save_local_user(
    session: Session,
    provider: str,
    user_payload: dict[str, Any],
) -> User:
    email = user_payload.get("email") or f"oauth_{provider}_{user_payload.get('id', uuid.uuid4().hex)}@noemail.local"
    meta = user_payload.get("user_metadata") or user_payload.get("app_metadata") or {}
    full_name = meta.get("full_name") or meta.get("name") or user_payload.get("name")
    provider_id = user_payload.get("id") or user_payload.get("sub") or user_payload.get("user_id")

    local_user = session.exec(select(User).where(User.email == email)).first()
    if local_user:
        dirty = False
        if full_name and local_user.full_name != full_name:
            local_user.full_name = full_name
            dirty = True
        if provider and local_user.provider != provider:
            local_user.provider = provider
            dirty = True
        if provider_id and local_user.provider_id != str(provider_id):
            local_user.provider_id = str(provider_id)
            dirty = True
        if not local_user.referral_code:
            local_user.referral_code = f"VEDA{uuid.uuid4().hex[:8].upper()}"
            dirty = True
        if dirty:
            session.add(local_user)
            session.commit()
            session.refresh(local_user)
    else:
        referral_code = f"VEDA{uuid.uuid4().hex[:8].upper()}"
        new_user = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(os.urandom(24).hex()),
            role="USER",
            referral_code=referral_code,
            provider=provider,
            provider_id=str(provider_id) if provider_id else None,
            last_login_at=None,
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        local_user = new_user

        try:
            TokenService.create_wallet(session, local_user.id)
        except Exception as exc:
            logger.warning("Wallet creation failed for OAuth user_id=%s: %s", local_user.id, exc)

    try:
        TokenService.get_balance(session, local_user.id)
    except ValueError:
        try:
            TokenService.create_wallet(session, local_user.id)
        except Exception as exc:
            logger.warning("Wallet ensure failed for OAuth user_id=%s: %s", local_user.id, exc)

    return local_user


async def _start_oauth_login(request: Request, provider: str) -> RedirectResponse:
    try:
        client = _get_supabase_client()
        callback_url = _backend_callback_url(request, provider)
        response = client.auth.sign_in_with_oauth(
            {
                "provider": provider,
                "options": {
                    "redirect_to": callback_url,
                },
            }
        )
        login_url = _extract_response_url(response)
        if not login_url:
            raise HTTPException(status_code=500, detail="Failed to generate OAuth URL")
        return RedirectResponse(url=login_url, status_code=302)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("OAuth login start failed for provider=%s", provider)
        raise HTTPException(status_code=500, detail=f"OAuth login failed: {str(exc)}") from exc


@router.get("/auth/github/login")
async def github_login(request: Request):
    return await _start_oauth_login(request, "github")


@router.get("/auth/google/login")
async def google_login(request: Request):
    return await _start_oauth_login(request, "google")


@router.get("/auth/callback")
async def auth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    provider: Optional[str] = None,
    session: Session = Depends(get_session),
):
    try:
        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")

        detected_provider = (provider or _provider_from_state(state) or "").lower() or None
        client = _get_supabase_client()

        try:
            exchange_result = client.auth.exchange_code_for_session({"auth_code": code})
        except TypeError:
            exchange_result = client.auth.exchange_code_for_session(code)

        user_payload, session_payload, access_token = _extract_session_payload(exchange_result)
        if not access_token and isinstance(exchange_result, dict):
            access_token = exchange_result.get("access_token")

        if not access_token:
            raise HTTPException(status_code=500, detail="Supabase session token not available")

        if not detected_provider:
            identities = user_payload.get("identities") or []
            if identities and isinstance(identities, list):
                first_identity = identities[0] or {}
                detected_provider = (first_identity.get("provider") or "").lower() or None
            if not detected_provider:
                app_metadata = user_payload.get("app_metadata") or {}
                detected_provider = (app_metadata.get("provider") or "").lower() or None
            if not detected_provider:
                detected_provider = "github" if user_payload.get("avatar_url") or user_payload.get("login") else "google"

        if not user_payload:
            try:
                user_payload = client.auth.get_user(access_token).user or {}
            except Exception:
                user_payload = {}

        await _upsert_supabase_user_profile(user_payload, detected_provider or "google")
        local_user = await _save_local_user(session, detected_provider or "google", user_payload)

        try:
            local_jwt = create_access_token(subject=str(local_user.id))
        except Exception as exc:
            logger.exception("Failed to create local JWT: %s", exc)
            raise HTTPException(status_code=500, detail="Session creation failed") from exc

        email = user_payload.get("email") or local_user.email
        frontend_redirect = _frontend_redirect_url(access_token, detected_provider or "google", email)

        response = RedirectResponse(url=frontend_redirect, status_code=302)
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=local_jwt,
            max_age=SESSION_COOKIE_MAX_AGE,
            secure=SESSION_COOKIE_SECURE,
            httponly=SESSION_COOKIE_HTTPONLY,
            samesite=SESSION_COOKIE_SAMESITE,
            path="/",
        )
        logger.info(
            "OAuth success user_id=%s provider=%s email=%s",
            local_user.id,
            detected_provider,
            email,
        )
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("OAuth callback failed: %s", exc)
        redirect_base = FRONTEND_URL.rstrip("/") if FRONTEND_URL else ""
        if redirect_base:
            fallback = f"{redirect_base}?{urlencode({'error': 'oauth_callback_failed'})}"
            return RedirectResponse(url=fallback, status_code=302)
        raise HTTPException(status_code=500, detail="OAuth callback failed") from exc


@router.get("/api/v1/auth/oauth_me")
async def oauth_me(request: Request, session: Session = Depends(get_session)):
    from jose import JWTError, jwt

    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        logger.exception("Invalid session JWT")
        raise HTTPException(status_code=401, detail="Invalid session token")

    user = session.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="Unknown user")

    return {
        "success": True,
        "data": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "provider": user.provider,
            "provider_id": user.provider_id,
            "role": user.role,
            "plan": user.plan,
        },
    }


@router.post("/api/v1/auth/logout")
async def oauth_logout(response: Response):
    resp = JSONResponse({"success": True, "message": "Logged out"})
    resp.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return resp
