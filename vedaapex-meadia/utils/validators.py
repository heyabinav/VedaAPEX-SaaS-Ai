"""
Input validation utilities.
"""

import re
from typing import Optional
from utils.exceptions import ValidationError
from config import config


class Validators:
    """Validation utilities."""

    @staticmethod
    def validate_query(query: str) -> str:
        """Validate search query."""
        if not query or not isinstance(query, str):
            raise ValidationError("Query must be a non-empty string")

        query = query.strip()

        if len(query) < config.MIN_QUERY_LENGTH:
            raise ValidationError(f"Query must be at least {config.MIN_QUERY_LENGTH} characters")

        if len(query) > config.MAX_QUERY_LENGTH:
            raise ValidationError(f"Query must not exceed {config.MAX_QUERY_LENGTH} characters")

        # Allow alphanumeric, spaces, hyphens, and punctuation
        if not re.match(r"^[a-zA-Z0-9\s\-_.,&()\u0080-\uFFFF]+$", query):
            raise ValidationError("Query contains invalid characters")

        return query

    @staticmethod
    def validate_pagination(page: Optional[int] = None, page_size: Optional[int] = None) -> tuple:
        """Validate pagination parameters."""
        page = page or 1
        page_size = page_size or config.DEFAULT_PAGE_SIZE

        if not isinstance(page, int) or page < 1:
            raise ValidationError("Page must be >= 1")

        if not isinstance(page_size, int) or page_size < 1:
            raise ValidationError("Page size must be >= 1")

        if page_size > config.MAX_PAGE_SIZE:
            raise ValidationError(f"Page size must not exceed {config.MAX_PAGE_SIZE}")

        return page, page_size

    @staticmethod
    def sanitize_query(query: str) -> str:
        """Sanitize query."""
        query = re.sub(r"\s+", " ", query.strip())
        query = re.sub(r"[^\w\s\-_.,&()]", "", query)
        return query


validators = Validators()
