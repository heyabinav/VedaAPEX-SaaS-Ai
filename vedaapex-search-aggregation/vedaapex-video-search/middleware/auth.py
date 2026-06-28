"""
API Key authentication middleware.
"""

import logging
from typing import Optional
from fastapi import Request, HTTPException, status

from config import config
from utils.exceptions import AuthenticationError
from utils.helpers import helpers

logger = logging.getLogger(__name__)


class APIKeyAuth:
    """API Key authentication."""

    @staticmethod
    def extract_api_key(request: Request) -> Optional[str]:
        """
        Extract API key from request.

        Args:
            request: FastAPI request

        Returns:
            API key or None

        Raises:
            AuthenticationError: If API key format is invalid
        """
        # Try Authorization header first
        auth_header = request.headers.get("Authorization", "")
        if auth_header:
            api_key = helpers.parse_api_key_from_header(auth_header)
            if api_key:
                return api_key

        # Try X-API-Key header
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return api_key

        # Try query parameter
        api_key = request.query_params.get("api_key", "")
        if api_key:
            return api_key

        return None

    @staticmethod
    def validate_api_key(api_key: Optional[str]) -> bool:
        """
        Validate API key.

        Args:
            api_key: API key to validate

        Returns:
            True if valid, False otherwise
        """
        if not api_key:
            return False

        # Check if API key is in allowed list
        if config.ALLOWED_API_KEYS and api_key not in config.ALLOWED_API_KEYS:
            return False

        return True

    @staticmethod
    async def verify_api_key(request: Request) -> bool:
        """
        Verify API key from request.

        Args:
            request: FastAPI request

        Returns:
            True if valid

        Raises:
            HTTPException: If authentication fails
        """
        if not config.ENABLE_API_KEY_AUTH:
            return True

        api_key = APIKeyAuth.extract_api_key(request)

        if not api_key:
            logger.warning(f"Missing API key: {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not APIKeyAuth.validate_api_key(api_key):
            logger.warning(f"Invalid API key: {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return True
