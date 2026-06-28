"""Input validation utilities."""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class Validators:
    """Input validation utilities."""

    EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    USERNAME_REGEX = r"^[a-zA-Z0-9_-]{3,20}$"

    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """
        Validate email format.

        Args:
            email: Email address to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email is required"

        if len(email) > 255:
            return False, "Email is too long"

        if not re.match(Validators.EMAIL_REGEX, email):
            return False, "Invalid email format"

        return True, ""

    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """
        Validate username format.

        Args:
            username: Username to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not username:
            return False, "Username is required"

        if len(username) < 3:
            return False, "Username must be at least 3 characters"

        if len(username) > 20:
            return False, "Username must not exceed 20 characters"

        if not re.match(Validators.USERNAME_REGEX, username):
            return (
                False,
                "Username can only contain letters, numbers, hyphens, and underscores",
            )

        return True, ""

    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """
        Validate password strength.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        from ..config import EmailConfig

        if not password:
            return False, "Password is required"

        if len(password) < EmailConfig.PASSWORD_MIN_LENGTH:
            return (
                False,
                f"Password must be at least {EmailConfig.PASSWORD_MIN_LENGTH} characters",
            )

        if len(password) > 128:
            return False, "Password is too long"

        # Check for complexity (optional but recommended)
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            return False, "Password must contain uppercase, lowercase, and numbers"

        return True, ""

    @staticmethod
    def validate_full_name(full_name: str) -> Tuple[bool, str]:
        """
        Validate full name.

        Args:
            full_name: Full name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not full_name:
            return False, "Full name is required"

        if len(full_name) < 2:
            return False, "Full name must be at least 2 characters"

        if len(full_name) > 100:
            return False, "Full name must not exceed 100 characters"

        return True, ""

    @staticmethod
    def validate_token(token: str) -> Tuple[bool, str]:
        """
        Validate token format.

        Args:
            token: Token to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not token:
            return False, "Token is required"

        if len(token) < 10:
            return False, "Invalid token format"

        return True, ""
