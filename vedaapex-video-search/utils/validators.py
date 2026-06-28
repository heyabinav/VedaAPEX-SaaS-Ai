"""
Input validation utilities.
"""

import re
from typing import Optional
from utils.exceptions import ValidationError


class Validators:
    """Input validation utilities."""

    # ========================================================================
    # QUERY VALIDATION
    # ========================================================================

    @staticmethod
    def validate_search_query(query: str, min_length: int = 1, max_length: int = 256) -> str:
        """
        Validate search query.

        Args:
            query: Search query string
            min_length: Minimum query length
            max_length: Maximum query length

        Returns:
            Sanitized query string

        Raises:
            ValidationError: If query is invalid
        """
        if not query or not isinstance(query, str):
            raise ValidationError("Query must be a non-empty string")

        query = query.strip()

        if len(query) < min_length:
            raise ValidationError(f"Query must be at least {min_length} character(s)")

        if len(query) > max_length:
            raise ValidationError(f"Query must not exceed {max_length} characters")

        # Allow alphanumeric, spaces, hyphens, and basic punctuation
        if not re.match(r"^[a-zA-Z0-9\s\-_.,&()]+$", query):
            raise ValidationError("Query contains invalid characters")

        return query

    @staticmethod
    def validate_pagination(
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        max_page_size: int = 80,
    ) -> tuple:
        """
        Validate pagination parameters.

        Args:
            page: Page number (1-indexed)
            page_size: Results per page
            max_page_size: Maximum allowed page size

        Returns:
            Tuple of (page, page_size)

        Raises:
            ValidationError: If parameters are invalid
        """
        page = page or 1
        page_size = page_size or 20

        if not isinstance(page, int) or page < 1:
            raise ValidationError("Page must be an integer >= 1")

        if not isinstance(page_size, int) or page_size < 1:
            raise ValidationError("Page size must be an integer >= 1")

        if page_size > max_page_size:
            raise ValidationError(f"Page size must not exceed {max_page_size}")

        return page, page_size

    @staticmethod
    def validate_api_key(api_key: Optional[str]) -> str:
        """
        Validate API key format.

        Args:
            api_key: API key string

        Returns:
            Validated API key

        Raises:
            ValidationError: If API key is invalid
        """
        if not api_key or not isinstance(api_key, str):
            raise ValidationError("API key is required")

        if len(api_key) < 10:
            raise ValidationError("API key is invalid")

        return api_key.strip()

    @staticmethod
    def sanitize_query(query: str) -> str:
        """
        Sanitize query string.

        Args:
            query: Raw query string

        Returns:
            Sanitized query string
        """
        # Remove extra whitespace
        query = re.sub(r"\s+", " ", query.strip())
        # Remove special characters except basic punctuation
        query = re.sub(r"[^\w\s\-_.,&()]", "", query)
        return query

    @staticmethod
    def validate_sort_order(sort_order: Optional[str] = None) -> str:
        """
        Validate sort order.

        Args:
            sort_order: Sort order string

        Returns:
            Validated sort order

        Raises:
            ValidationError: If sort order is invalid
        """
        valid_orders = ["latest", "popular", "trending"]

        if sort_order is None:
            return "latest"

        if sort_order.lower() not in valid_orders:
            raise ValidationError(f"Sort order must be one of: {', '.join(valid_orders)}")

        return sort_order.lower()


# Create singleton instance
validators = Validators()
