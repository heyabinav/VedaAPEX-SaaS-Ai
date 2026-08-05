"""Authentication routes for email verification."""

from utils.time import utcnow

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db, get_db_context
from ..models import EmailUser
from ..services import EmailService, TokenService
from ..utils import Validators
from ..config import EmailConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/email", tags=["email"])


# Pydantic models
class RegisterRequest(BaseModel):
    """User registration request."""

    email: str
    username: str
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    """User login request."""

    email: str
    password: str


class ResendVerificationRequest(BaseModel):
    """Resend verification email request."""

    email: str


class VerifyEmailResponse(BaseModel):
    """Email verification response."""

    success: bool
    message: str
    user: Optional[dict] = None


class LoginResponse(BaseModel):
    """Login response."""

    success: bool
    message: str
    user: Optional[dict] = None


class RegisterResponse(BaseModel):
    """Registration response."""

    success: bool
    message: str
    user: Optional[dict] = None


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(request: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    """
    Register a new user and send verification email.

    - Validates email and password
    - Creates user with hashed password
    - Generates verification token
    - Sends verification email

    Request:
        ```json
        {
            "email": "user@example.com",
            "username": "johndoe",
            "password": "SecurePass123",
            "full_name": "John Doe"
        }
        ```

    Response:
        ```json
        {
            "success": true,
            "message": "User registered. Check email for verification link.",
            "user": {
                "id": 1,
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "is_email_verified": false
            }
        }
        ```
    """
    try:
        # Validate inputs
        email_valid, email_error = Validators.validate_email(request.email)
        if not email_valid:
            raise HTTPException(status_code=400, detail=email_error)

        username_valid, username_error = Validators.validate_username(request.username)
        if not username_valid:
            raise HTTPException(status_code=400, detail=username_error)

        password_valid, password_error = Validators.validate_password(request.password)
        if not password_valid:
            raise HTTPException(status_code=400, detail=password_error)

        if request.full_name:
            name_valid, name_error = Validators.validate_full_name(request.full_name)
            if not name_valid:
                raise HTTPException(status_code=400, detail=name_error)

        # Check if user already exists
        existing_user = (
            db.query(EmailUser)
            .filter((EmailUser.email == request.email) | (EmailUser.username == request.username))
            .first()
        )

        if existing_user:
            if existing_user.email == request.email:
                raise HTTPException(status_code=409, detail="Email already registered")
            else:
                raise HTTPException(status_code=409, detail="Username already taken")

        # Generate verification token
        verification_token = TokenService.generate_verification_token()
        token_expiry = TokenService.get_token_expiry()

        # Hash password
        hashed_password = EmailUser.hash_password(request.password)

        # Create user
        new_user = EmailUser(
            email=request.email,
            username=request.username,
            hashed_password=hashed_password,
            full_name=request.full_name,
            verification_token=verification_token,
            verification_token_expires=token_expiry,
            is_email_verified=False,
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"✅ User registered: {request.email}")

        # Send verification email
        email_service = EmailService()
        email_sent = email_service.send_verification_email(
            to_email=request.email,
            username=request.username,
            verification_token=verification_token,
        )

        if not email_sent:
            logger.warning(f"⚠️  Failed to send verification email to {request.email}")

        return RegisterResponse(
            success=True,
            message="User registered successfully. Please check your email to verify your account.",
            user=new_user.to_dict(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """
    Login user (only if email is verified).

    - Validates credentials
    - Checks if email is verified
    - Returns success message

    Request:
        ```json
        {
            "email": "user@example.com",
            "password": "SecurePass123"
        }
        ```

    Response (Success):
        ```json
        {
            "success": true,
            "message": "Login successful",
            "user": {
                "id": 1,
                "email": "user@example.com",
                "username": "johndoe",
                "is_email_verified": true
            }
        }
        ```

    Response (Unverified Email):
        ```json
        {
            "success": false,
            "message": "Email not verified. Please check your email."
        }
        ```
    """
    try:
        # Validate inputs
        email_valid, email_error = Validators.validate_email(request.email)
        if not email_valid:
            raise HTTPException(status_code=400, detail=email_error)

        # Find user
        user = db.query(EmailUser).filter(EmailUser.email == request.email).first()

        if not user:
            logger.warning(f"⚠️  Login attempt with non-existent email: {request.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Check if user is active
        if not user.is_active:
            logger.warning(f"⚠️  Login attempt for inactive user: {request.email}")
            raise HTTPException(status_code=403, detail="Account is disabled")

        # Verify password
        if not user.verify_password(request.password):
            user.failed_login_attempts += 1
            user.last_failed_login_at = utcnow()

            if user.failed_login_attempts >= EmailConfig.MAX_LOGIN_ATTEMPTS:
                logger.warning(f"⚠️  Too many failed login attempts for: {request.email}")
                user.is_active = False

            db.commit()
            logger.warning(f"⚠️  Failed login for: {request.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Check if email is verified
        if not user.is_email_verified:
            logger.warning(f"⚠️  Login attempt with unverified email: {request.email}")
            raise HTTPException(
                status_code=403,
                detail="Email not verified. Please check your email for verification link.",
            )

        # Update login timestamp and reset failed attempts
        user.last_login_at = utcnow()
        user.failed_login_attempts = 0
        db.commit()

        logger.info(f"✅ Successful login: {request.email}")

        return LoginResponse(success=True, message="Login successful", user=user.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.get("/verify", status_code=200)
async def verify_email(token: str, db: Session = Depends(get_db)) -> VerifyEmailResponse:
    """
    Verify user email with token.

    - Validates token
    - Checks token expiration
    - Updates user verification status

    Query Parameters:
        - token (str): Verification token from email link

    Response (Success):
        ```json
        {
            "success": true,
            "message": "Email verified successfully",
            "user": {
                "id": 1,
                "email": "user@example.com",
                "is_email_verified": true
            }
        }
        ```

    Response (Invalid Token):
        ```json
        {
            "success": false,
            "message": "Invalid or expired verification token"
        }
        ```
    """
    try:
        # Validate token
        token_valid, token_error = Validators.validate_token(token)
        if not token_valid:
            raise HTTPException(status_code=400, detail=token_error)

        # Find user by token
        user = db.query(EmailUser).filter(EmailUser.verification_token == token).first()

        if not user:
            logger.warning(f"⚠️  Email verification attempt with invalid token")
            raise HTTPException(status_code=400, detail="Invalid verification token")

        # Check if token is expired
        if not user.is_verification_token_valid():
            logger.warning(f"⚠️  Email verification attempt with expired token for: {user.email}")
            raise HTTPException(status_code=400, detail="Verification token has expired")

        # Update user
        user.is_email_verified = True
        user.email_verified_at = utcnow()
        user.verification_token = None  # Clear token after use
        user.verification_token_expires = None
        db.commit()

        logger.info(f"✅ Email verified: {user.email}")

        return VerifyEmailResponse(
            success=True,
            message="Email verified successfully. You can now login.",
            user=user.to_dict(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Email verification error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Email verification failed")


@router.post("/resend-verification", response_model=RegisterResponse)
async def resend_verification_email(
    request: ResendVerificationRequest, db: Session = Depends(get_db)
) -> RegisterResponse:
    """
    Resend verification email to user.

    - Validates email
    - Checks user exists and email not verified
    - Generates new token
    - Sends email

    Request:
        ```json
        {
            "email": "user@example.com"
        }
        ```

    Response:
        ```json
        {
            "success": true,
            "message": "Verification email sent. Check your email."
        }
        ```
    """
    try:
        # Validate email
        email_valid, email_error = Validators.validate_email(request.email)
        if not email_valid:
            raise HTTPException(status_code=400, detail=email_error)

        # Find user
        user = db.query(EmailUser).filter(EmailUser.email == request.email).first()

        if not user:
            logger.warning(f"⚠️  Resend verification for non-existent email: {request.email}")
            raise HTTPException(status_code=404, detail="User not found")

        # Check if already verified
        if user.is_email_verified:
            raise HTTPException(status_code=400, detail="Email is already verified")

        # Generate new token
        verification_token = TokenService.generate_verification_token()
        token_expiry = TokenService.get_token_expiry()

        user.verification_token = verification_token
        user.verification_token_expires = token_expiry
        db.commit()

        logger.info(f"✅ Verification token regenerated for: {request.email}")

        # Send email
        email_service = EmailService()
        email_sent = email_service.send_verification_email(
            to_email=request.email,
            username=user.username,
            verification_token=verification_token,
        )

        if not email_sent:
            logger.warning(f"⚠️  Failed to resend verification email to {request.email}")
            raise HTTPException(status_code=500, detail="Failed to send email")

        return RegisterResponse(
            success=True,
            message="Verification email sent successfully. Check your email.",
            user=user.to_dict(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Resend verification error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to resend verification email")


@router.get("/health", status_code=200)
async def health_check():
    """
    Health check endpoint.

    Response:
        ```json
        {
            "status": "healthy",
            "service": "email-verification"
        }
        ```
    """
    return {
        "status": "healthy",
        "service": "email-verification",
        "timestamp": utcnow().isoformat(),
    }