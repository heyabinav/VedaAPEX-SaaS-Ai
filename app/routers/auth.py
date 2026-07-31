"""
Authentication router – handles registration, login, logout, token retrieval,
and API‑key lifecycle.

Key improvements (deployment‑blocking fixes):
  • Every endpoint is wrapped in try/except with structured logging.
  • Registration & login return meaningful 4xx/5xx with detail strings.
  • Null‑safe access on wallet, subscription, and referral results.
  • Proper error handling for missing Supabase configuration.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.referral_service import ReferralService
from app.services.supabase_service import SupabaseService, SupabaseAuthError
from app.services.token_service import TokenService
from app.services.subscription_service import SubscriptionService
from app.schemas.auth import UserRegister, UserLogin, AuthResponse

logger = logging.getLogger("auth.router")

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


# ────────────────────────────────────────────────────────────
# Dependency – current authenticated user
# ────────────────────────────────────────────────────────────
async def get_current_user_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> User:
    return await AuthService.get_authenticated_user(request, credentials, session)


# ────────────────────────────────────────────────────────────
# API‑Key CRUD
# ────────────────────────────────────────────────────────────
@router.post("/api-key/generate")
async def generate_api_key(
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    try:
        new_key = f"va_live_{uuid.uuid4().hex}{uuid.uuid4().hex}"
        user.api_key = new_key
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info("API key generated for user_id=%s", user.id)
        return {"success": True, "api_key": new_key}
    except Exception as e:
        logger.exception("API key generation failed for user_id=%s", getattr(user, "id", "?"))
        raise HTTPException(status_code=500, detail=f"API key generation failed: {str(e)}") from e


@router.get("/api-key")
async def get_api_key(user: User = Depends(get_current_user_auth)):
    try:
        masked = None
        if user.api_key:
            masked = user.api_key[:12] + "..." + user.api_key[-4:]
        return {
            "success": True,
            "has_key": user.api_key is not None,
            "api_key": masked,
        }
    except Exception as e:
        logger.exception("Failed to retrieve API key")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve API key: {str(e)}") from e


@router.delete("/api-key/revoke")
async def revoke_api_key(
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    try:
        user.api_key = None
        session.add(user)
        session.commit()
        logger.info("API key revoked for user_id=%s", user.id)
        return {"success": True, "message": "API key revoked successfully."}
    except Exception as e:
        logger.exception("API key revocation failed for user_id=%s", user.id)
        raise HTTPException(status_code=500, detail=f"API key revocation failed: {str(e)}") from e


# ────────────────────────────────────────────────────────────
# POST /register
# ────────────────────────────────────────────────────────────
@router.post("/register", response_model=AuthResponse)
async def register(body: UserRegister, request: Request, session: Session = Depends(get_session)):
    """
    Register a new user with email and password.

    Handles:
    - Supabase configuration validation
    - Email/password validation
    - User creation with wallet
    - Referral processing
    - Comprehensive error responses
    """
    try:
        email = body.email.lower().strip() if body.email else ""
        password = body.password if body.password else ""
        full_name = body.full_name if hasattr(body, "full_name") else ""
        referral_code_input = body.referral_code if hasattr(body, "referral_code") else None

        if not email or not password:
            logger.warning("Registration attempt with missing email or password")
            raise HTTPException(status_code=400, detail="Email and password are required.")

        logger.info("Registration attempt for email=%s", email)

        # ── Check Supabase configuration ──
        if not SupabaseService.is_configured():
            logger.error("Supabase is not configured - registration disabled")
            raise HTTPException(
                status_code=503,
                detail="Authentication service is not configured. Please contact support.",
            )

        # ── Step 1: Supabase sign‑up ──
        try:
            auth_result = await SupabaseService.sign_up(
                email=email,
                password=password,
                metadata={"full_name": full_name} if full_name else None,
            )
            logger.info("Supabase sign_up succeeded for email=%s", email)
        except SupabaseAuthError as exc:
            logger.warning(
                "Supabase sign_up error for email=%s: %s (status=%s)",
                email,
                exc.message,
                exc.status_code,
            )
            status_code = exc.status_code
            if "already" in exc.message.lower() and status_code == 400:
                status_code = 409

            logger.debug("Supabase signup error details: %s", exc.message)
            raise HTTPException(
                status_code=status_code,
                detail=exc.message,
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected error during Supabase sign_up for email=%s", email)
            raise HTTPException(
                status_code=500, detail=f"Registration service error: {str(exc)}"
            ) from exc

        # ── Step 2: Local user + wallet creation ──
        try:
            user_data = auth_result.get("user") or {}
            user, created = SupabaseService.get_or_create_local_user(
                session,
                user_data,
                referral_code_input=referral_code_input,
                email_fallback=email,
            )
            logger.info(
                "Local user %s (id=%s, created=%s)",
                email,
                user.id if user else "?",
                created,
            )
        except Exception as e:
            logger.exception("Failed to create/fetch local user for email=%s", email)
            raise HTTPException(status_code=500, detail=f"User creation failed: {str(e)}") from e

        if not user:
            logger.error("User creation returned None for email=%s", email)
            raise HTTPException(status_code=500, detail="Failed to create user record.")

        # ── Step 3: Wallet balance ──
        wallet = None
        try:
            wallet = TokenService.get_balance(session, user.id)
        except ValueError:
            logger.warning("Wallet not found for user_id=%s — creating one", user.id)
            try:
                wallet = TokenService.create_wallet(session, user.id)
            except Exception as e:
                logger.exception("Wallet creation failed for user_id=%s", user.id)
                # Non-fatal, continue without wallet
                wallet = None

        # ── Step 4: Referral processing ──
        referral_result = None
        if created and referral_code_input:
            try:
                referral_result = ReferralService.process_referral(
                    session,
                    user.id,
                    referral_code_input,
                    request.client.host if request.client else None,
                )
                logger.info(
                    "Referral processed for user_id=%s with code=%s",
                    user.id,
                    referral_code_input,
                )
            except Exception as e:
                logger.warning("Referral processing failed (non‑fatal): %s", str(e))

        # ── Step 5: Build response ──
        token = auth_result.get("access_token")
        refresh_token = auth_result.get("refresh_token")

        subscription_summary = None
        try:
            subscription_summary = SubscriptionService.get_subscription_summary(session, user.id)
        except Exception as e:
            logger.warning("Subscription summary failed (non‑fatal): %s", str(e))
            subscription_summary = {"plan": "Free", "status": "active"}

        logger.info("Registration complete for email=%s user_id=%s", email, user.id)

        return {
            "success": True,
            "message": (
                "Account created successfully!"
                if token
                else "Account created. Verify your email before signing in."
            ),
            "data": {
                "user": {
                    "id": str(user.id) if user.id else None,
                    "email": user.email or "",
                    "fullName": user.full_name or "",
                    "referralCode": user.referral_code or "",
                    "role": user.role or "user",
                    "plan": user.plan or "Free",
                    "isPro": getattr(user, "is_pro", False),
                    "subscriptionStart": (
                        user.subscription_start.isoformat()
                        if getattr(user, "subscription_start", None)
                        else None
                    ),
                    "subscriptionEnd": (
                        user.subscription_end.isoformat()
                        if getattr(user, "subscription_end", None)
                        else None
                    ),
                },
                "token": token,
                "refreshToken": refresh_token,
                "requiresEmailConfirmation": token is None,
                "wallet": {"balance": wallet.balance if wallet else 0},
                "subscription": subscription_summary or {"plan": "Free", "status": "active"},
                "referral": referral_result,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled exception in register endpoint")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}") from e


# ────────────────────────────────────────────────────────────
# POST /login
# ────────────────────────────────────────────────────────────
@router.post("/login", response_model=AuthResponse)
async def login(body: UserLogin, session: Session = Depends(get_session)):
    """
    Login with email and password.

    Handles:
    - Supabase configuration validation
    - Credential validation
    - User sync and wallet setup
    - Comprehensive error responses
    """
    try:
        email = body.email.lower().strip() if body.email else ""
        password = body.password if body.password else ""

        if not email or not password:
            logger.warning("Login attempt with missing email or password")
            raise HTTPException(status_code=400, detail="Email and password are required.")

        logger.info("Login attempt for email=%s", email)

        # ── Check Supabase configuration ──
        if not SupabaseService.is_configured():
            logger.error("Supabase is not configured - login disabled")
            raise HTTPException(
                status_code=503,
                detail="Authentication service is not configured. Please contact support.",
            )

        # ── Supabase authenticate ──
        try:
            auth_result = await SupabaseService.sign_in_with_password(
                email=email, password=password
            )
            logger.info("Supabase sign_in succeeded for email=%s", email)
        except SupabaseAuthError as exc:
            logger.warning(
                "Login failed for email=%s: %s (status=%s)",
                email,
                exc.message,
                exc.status_code,
            )
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        except Exception as exc:
            logger.error("Supabase unavailable during login for email=%s: %s", email, str(exc))
            raise HTTPException(
                status_code=503,
                detail=f"Authentication service unavailable: {str(exc)}",
            ) from exc

        # ── Local user ──
        try:
            user_data = auth_result.get("user") or {}
            user, _ = SupabaseService.get_or_create_local_user(
                session, user_data, email_fallback=email
            )
        except OperationalError as e:
            logger.exception("Local user sync failed due to database operational error for email=%s", email)
            raise HTTPException(
                status_code=503,
                detail="Database service unavailable during login. Please try again later.",
            ) from e
        except SQLAlchemyError as e:
            logger.exception("Local user sync failed due to database error for email=%s", email)
            raise HTTPException(
                status_code=500,
                detail="Database error during login. Please contact support.",
            ) from e
        except Exception as e:
            logger.exception("Local user sync failed during login for email=%s", email)
            raise HTTPException(status_code=500, detail=f"User sync failed: {str(e)}") from e

        if not user:
            logger.error("User lookup returned None for email=%s", email)
            raise HTTPException(status_code=500, detail="User record not found.")

        if not getattr(user, "is_active", True):
            logger.warning("Login attempt for deactivated user=%s", email)
            raise HTTPException(status_code=403, detail="Account deactivated. Contact support.")

        # ── Wallet ──
        wallet = None
        try:
            wallet = TokenService.get_balance(session, user.id)
        except ValueError:
            logger.warning("Wallet missing for user_id=%s on login — creating", user.id)
            try:
                wallet = TokenService.create_wallet(session, user.id)
            except Exception as e:
                logger.exception("Wallet creation failed on login for user_id=%s", user.id)
                wallet = None

        # ── Subscription ──
        subscription_summary = None
        try:
            subscription_summary = SubscriptionService.get_subscription_summary(session, user.id)
        except Exception as e:
            logger.warning("Subscription summary failed (non‑fatal): %s", str(e))
            subscription_summary = {"plan": "Free", "status": "active"}

        logger.info("Login complete for email=%s user_id=%s", email, user.id)

        return {
            "success": True,
            "message": "Login successful!",
            "data": {
                "user": {
                    "id": str(user.id) if user.id else None,
                    "email": user.email or "",
                    "fullName": user.full_name or "",
                    "referralCode": user.referral_code or "",
                    "role": user.role or "user",
                    "plan": user.plan or "Free",
                    "isPro": getattr(user, "is_pro", False),
                    "subscriptionStart": (
                        user.subscription_start.isoformat()
                        if getattr(user, "subscription_start", None)
                        else None
                    ),
                    "subscriptionEnd": (
                        user.subscription_end.isoformat()
                        if getattr(user, "subscription_end", None)
                        else None
                    ),
                },
                "token": auth_result.get("access_token"),
                "refreshToken": auth_result.get("refresh_token"),
                "wallet": {"balance": wallet.balance if wallet else 0},
                "subscription": subscription_summary or {"plan": "Free", "status": "active"},
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled exception in login endpoint")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}") from e


# ────────────────────────────────────────────────────────────
# POST /logout
# ────────────────────────────────────────────────────────────
@router.post("/logout")
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user: User = Depends(get_current_user_auth),
):
    try:
        del user
        try:
            if credentials and not credentials.credentials.startswith("va_"):
                await SupabaseService.sign_out(credentials.credentials)
        except Exception as e:
            logger.warning("Supabase sign_out failed (non‑fatal): %s", str(e))

        request.state.user_id = None
        return {"success": True, "message": "Logged out successfully."}
    except Exception as e:
        logger.exception("Logout failed")
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}") from e


# ────────────────────────────────────────────────────────────
# GET /me
# ────────────────────────────────────────────────────────────
@router.get("/me")
async def get_me(
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    try:
        wallet = None
        try:
            wallet = TokenService.get_balance(session, user.id)
        except ValueError:
            logger.warning("Wallet missing for /me user_id=%s — creating", user.id)
            try:
                wallet = TokenService.create_wallet(session, user.id)
            except Exception as e:
                logger.warning("Wallet creation failed for /me user: %s", str(e))
                wallet = None

        subscription_summary = None
        try:
            subscription_summary = SubscriptionService.get_subscription_summary(session, user.id)
        except Exception as e:
            logger.warning("Subscription summary failed for /me: %s", str(e))
            subscription_summary = {"plan": "Free", "status": "active"}

        return {
            "success": True,
            "data": {
                "id": str(user.id) if user.id else None,
                "email": user.email or "",
                "full_name": user.full_name or "",
                "referral_code": user.referral_code or "",
                "role": user.role or "user",
                "plan": user.plan or "Free",
                "is_pro": getattr(user, "is_pro", False),
                "subscription_start": (
                    user.subscription_start.isoformat()
                    if getattr(user, "subscription_start", None)
                    else None
                ),
                "subscription_end": (
                    user.subscription_end.isoformat()
                    if getattr(user, "subscription_end", None)
                    else None
                ),
                "created_at": (
                    user.created_at.isoformat() if getattr(user, "created_at", None) else None
                ),
                "wallet": {
                    "balance": wallet.balance if wallet else 0,
                    "lifetime_earned": wallet.lifetime_earned if wallet else 0,
                    "lifetime_spent": wallet.lifetime_spent if wallet else 0,
                },
                "subscription": subscription_summary or {"plan": "Free", "status": "active"},
            },
        }
    except Exception as e:
        logger.exception("Failed to retrieve user profile")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve profile: {str(e)}") from e
