"""app/routers/oauth.py - unified OAuth callback endpoint for Google and GitHub"""

import logging
import os
from typing import Optional
from fastapi import APIRouter, Request, Response, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from sqlmodel import Session, select
import re

from app.services.supabase_oauth import (
    exchange_code_for_token,
    detect_provider_from_payload,
    normalize_supabase_user,
    fetch_user_from_access_token,
    SupabaseOAuthError,
)
from app.db.session import get_session
from app.models.user import User
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash

logger = logging.getLogger("auth.oauth")
router = APIRouter()

SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", settings.SESSION_COOKIE_NAME)
SESSION_COOKIE_MAX_AGE = int(os.getenv("SESSION_COOKIE_MAX_AGE", settings.SESSION_COOKIE_MAX_AGE))
SESSION_COOKIE_SECURE = (
    os.getenv("SESSION_COOKIE_SECURE", str(settings.SESSION_COOKIE_SECURE)).lower() == "true"
)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", settings.SESSION_COOKIE_SAMESITE)

FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL") or settings.FRONTEND_BASE_URL or None
APP_BASE_URL = os.getenv("APP_BASE_URL") or settings.APP_BASE_URL or None

# Regex pattern for safe relative state URLs (allows provider prefix like "google:" or "github:")
_ALLOWED_RELATIVE_STATE = re.compile(r"^(google:|github:|)\/[A-Za-z0-9_\-\/\?\=\&\#]*$")


def _safe_frontend_redirect(state: Optional[str] = None) -> str:
    """Generate a safe redirect URL to frontend with optional state parameter."""
    base = FRONTEND_BASE_URL
    if not base:
        raise HTTPException(status_code=500, detail="FRONTEND_BASE_URL not configured")
    base = base.rstrip("/")
    if not state:
        return f"{base}/"
    if not _ALLOWED_RELATIVE_STATE.match(state):
        logger.warning("Rejected unsafe state for redirect: %s", state)
        return f"{base}/"
    return f"{base}{state}"


@router.get("/auth/callback")
async def auth_callback(
    request: Request,
    response: Response,
    code: Optional[str] = None,
    state: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """
    Unified OAuth callback endpoint for Google and GitHub.

    Flow:
    1. Receive authorization code from Supabase
    2. Exchange code for access token (server-side)
    3. Fetch authenticated user from Supabase /auth/v1/user
    4. Detect provider (Google or GitHub) from Supabase response
    5. Normalize user data
    6. Create or update local user in database
    7. Create secure JWT session cookie
    8. Redirect to frontend with optional state path
    """
    logger.info(
        "OAuth callback invoked from %s (client=%s)",
        request.url,
        request.client.host if request.client else "unknown",
    )

    # Validate authorization code
    if not code:
        logger.warning("OAuth callback missing code")
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Validate APP_BASE_URL is configured
    if not APP_BASE_URL:
        logger.error("APP_BASE_URL not configured")
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured for OAuth (APP_BASE_URL missing)",
        )

    redirect_uri = f"{APP_BASE_URL.rstrip('/')}/auth/callback"

    # Pre-detect provider from state parameter (format: "google:/path" or "github:/path")
    detected_provider_from_state = None
    original_state = state
    if state and state.startswith(("google:", "github:")):
        provider_part, _, path_part = state.partition(":")
        detected_provider_from_state = provider_part.lower()
        state = path_part or "/"  # Extract the redirect path
        logger.info("Provider detected from state parameter: %s", detected_provider_from_state)

    # Step 1: Exchange authorization code for access token
    try:
        token_payload = await exchange_code_for_token(
            code=code,
            redirect_uri=redirect_uri,
            provider=detected_provider_from_state,
            timeout=settings.SUPABASE_TIMEOUT_SECONDS,
        )
        logger.debug("Token payload keys: %s", list(token_payload.keys()))
    except SupabaseOAuthError as exc:
        logger.exception("Token exchange failed: %s", exc)
        redirect_target = _safe_frontend_redirect("/auth/error")
        return RedirectResponse(
            url=f"{redirect_target}?error=token_exchange_failed", status_code=302
        )

    # Step 2: Detect provider from payload (if not already detected from state)
    provider = detected_provider_from_state or detect_provider_from_payload(token_payload) or None
    logger.info("Detected OAuth provider=%s", provider)

    # Step 3: Fetch user info from Supabase
    access_token = token_payload.get("access_token")
    user_info = None
    if access_token:
        try:
            user_info = await fetch_user_from_access_token(access_token)
            logger.info(
                "Fetched user info from Supabase for provider=%s id=%s",
                provider,
                user_info.get("id"),
            )
        except SupabaseOAuthError:
            logger.exception(
                "Failed to fetch user info; will fallback to token payload 'user' if present"
            )
            user_info = token_payload.get("user") or None

    # Fallback: use user from token payload if not fetched separately
    if not user_info:
        user_info = token_payload.get("user") or {}
        if not user_info:
            logger.error("No user info available from token payload")
            redirect_target = _safe_frontend_redirect("/auth/error")
            return RedirectResponse(url=f"{redirect_target}?error=no_user_info", status_code=302)

    # Step 4: Normalize user data (handles Google/GitHub differences)
    normalized = normalize_supabase_user(user_info, provider=provider)
    if not provider:
        provider = normalized.get("provider")
    logger.info(
        "Normalized user: provider=%s email=%s provider_id=%s",
        provider,
        normalized.get("email"),
        normalized.get("provider_id"),
    )

    # Validate provider is supported
    if provider not in (None, "google", "github"):
        logger.warning("Unsupported provider detected: %s", provider)

    # Step 5: Create or update local user in database
    local_user = None
    try:
        email = normalized.get("email")
        provider_id = normalized.get("provider_id")

        # Try to find existing user by email (preferred)
        if email:
            stmt = select(User).where(User.email == email)
            local_user = session.exec(stmt).first()

        # If not found by email, try provider + provider_id
        if not local_user and provider_id:
            stmt2 = select(User).where(
                User.provider == provider, User.provider_id == str(provider_id)
            )
            local_user = session.exec(stmt2).first()

        if local_user:
            # Update existing user if data changed
            dirty = False
            if normalized.get("full_name") and local_user.full_name != normalized.get("full_name"):
                local_user.full_name = normalized.get("full_name")
                dirty = True
            if provider and local_user.provider != provider:
                local_user.provider = provider
                dirty = True
            if provider_id and local_user.provider_id != str(provider_id):
                local_user.provider_id = str(provider_id)
                dirty = True
            if not local_user.referral_code:
                import uuid

                local_user.referral_code = f"VEDA{uuid.uuid4().hex[:8].upper()}"
                dirty = True
            if dirty:
                session.add(local_user)
                session.commit()
                session.refresh(local_user)
            logger.info(
                "Existing local user matched id=%s email=%s",
                local_user.id,
                local_user.email,
            )

            # Ensure the existing user has a wallet
            try:
                from app.services.token_service import TokenService

                try:
                    TokenService.get_balance(session, local_user.id)
                except ValueError:
                    TokenService.create_wallet(session, local_user.id)
                    logger.info(
                        "Created missing wallet for existing OAuth user_id=%s",
                        local_user.id,
                    )
            except Exception as e:
                logger.warning("Failed to check/create wallet for existing OAuth user: %s", e)
        else:
            # Create new user
            import uuid

            rand_pw = os.urandom(24).hex()
            referral_code = f"VEDA{uuid.uuid4().hex[:8].upper()}"
            new_user = User(
                email=normalized.get("email") or f"oauth_{provider}_{provider_id}@noemail.local",
                full_name=normalized.get("full_name") or None,
                hashed_password=get_password_hash(rand_pw),
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
            logger.info(
                "Created new local user id=%s email=%s provider=%s referral_code=%s",
                local_user.id,
                local_user.email,
                provider,
                referral_code,
            )

            # Initialize TokenWallet
            try:
                from app.services.token_service import TokenService

                TokenService.create_wallet(session, local_user.id)
                logger.info("Wallet created for OAuth user_id=%s", local_user.id)
            except Exception as e:
                logger.warning("Wallet creation for OAuth user failed: %s", e)
    except Exception as exc:
        logger.exception("Failed to upsert local user during OAuth callback: %s", exc)
        redirect_target = _safe_frontend_redirect("/auth/error")
        return RedirectResponse(url=f"{redirect_target}?error=user_upsert_failed", status_code=302)

    # Step 6: Create secure JWT session token
    try:
        jwt_token = create_access_token(subject=str(local_user.id))
    except Exception:
        logger.exception("Failed to create session JWT")
        redirect_target = _safe_frontend_redirect("/auth/error")
        return RedirectResponse(
            url=f"{redirect_target}?error=session_creation_failed", status_code=302
        )

    # Step 7: Generate safe redirect URL
    try:
        redirect_path = state if state else "/"
        frontend_redirect = _safe_frontend_redirect(redirect_path)
    except HTTPException:
        frontend_redirect = _safe_frontend_redirect("/")

    # Step 8: Create response with secure cookie redirect
    resp = RedirectResponse(url=frontend_redirect, status_code=302)
    resp.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=jwt_token,
        max_age=SESSION_COOKIE_MAX_AGE,
        secure=SESSION_COOKIE_SECURE,
        httponly=SESSION_COOKIE_HTTPONLY,
        samesite=SESSION_COOKIE_SAMESITE,
        path="/",
    )
    logger.info(
        "OAuth login success for user_id=%s provider=%s redirect=%s",
        local_user.id,
        provider,
        frontend_redirect,
    )
    return resp


@router.get("/api/v1/auth/oauth_me")
async def oauth_me(request: Request, session: Session = Depends(get_session)):
    """Get current authenticated user info from OAuth session."""
    from jose import jwt, JWTError

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
    """Logout by clearing the session cookie."""
    resp = JSONResponse({"success": True, "message": "Logged out"})
    resp.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return resp
