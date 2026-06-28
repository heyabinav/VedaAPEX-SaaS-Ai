"""Token generation and verification service."""

import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from ..config import EmailConfig

logger = logging.getLogger(__name__)


class TokenService:
    """Service for generating and verifying tokens."""

    @staticmethod
    def generate_verification_token() -> str:
        """
        Generate a cryptographically secure verification token.

        Returns:
            Hex string token of specified length
        """
        token = secrets.token_hex(EmailConfig.VERIFICATION_TOKEN_LENGTH // 2)
        logger.debug("✅ Verification token generated")
        return token

    @staticmethod
    def get_token_expiry() -> datetime:
        """
        Get token expiration datetime.

        Returns:
            Datetime when token expires
        """
        return datetime.utcnow() + EmailConfig.VERIFICATION_TOKEN_EXPIRY

    @staticmethod
    def hash_token(token: str) -> str:
        """
        Hash token for secure storage (optional).

        Args:
            token: Raw token to hash

        Returns:
            SHA256 hash of token
        """
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def is_token_expired(expiry_time: datetime) -> bool:
        """
        Check if token is expired.

        Args:
            expiry_time: Token expiration datetime

        Returns:
            True if token is expired, False otherwise
        """
        return datetime.utcnow() > expiry_time

    @staticmethod
    def generate_session_token(user_id: int, email: str) -> str:
        """
        Generate a session token (for JWT-like functionality).

        Args:
            user_id: User ID
            email: User email

        Returns:
            Session token
        """
        timestamp = datetime.utcnow().isoformat()
        data = f"{user_id}:{email}:{timestamp}:{secrets.token_hex(16)}"
        token = hashlib.sha256(data.encode()).hexdigest()
        logger.debug(f"✅ Session token generated for user {user_id}")
        return token
