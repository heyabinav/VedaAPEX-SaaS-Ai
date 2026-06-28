"""Validators for input validation."""

import logging
import re
from config import config
from utils.exceptions import ValidationError

logger = logging.getLogger(__name__)


class Validators:
    """Input validators."""

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

        if not re.match(r"^[a-zA-Z0-9\s\-_.,&()\u0080-\uFFFF]+$", query):
            raise ValidationError("Query contains invalid characters")

        logger.debug(f"Query validated: {query}")
        return query

    @staticmethod
    def validate_pagination(page: int = None, page_size: int = None) -> tuple:
        """Validate pagination parameters."""
        page = page or 1
        page_size = page_size or config.DEFAULT_PAGE_SIZE

        if not isinstance(page, int) or page < 1:
            raise ValidationError("Page must be >= 1")

        if not isinstance(page_size, int) or page_size < 1:
            raise ValidationError("Page size must be >= 1")

        if page_size > config.MAX_PAGE_SIZE:
            raise ValidationError(f"Page size must not exceed {config.MAX_PAGE_SIZE}")

        logger.debug(f"Pagination validated: page={page}, page_size={page_size}")
        return page, page_size

    @staticmethod
    def validate_media_type(media_type: str = None) -> str:
        """Validate media type."""
        if not media_type:
            return "image"

        if media_type not in ["image", "video"]:
            raise ValidationError("Media type must be 'image' or 'video'")

        return media_type


validators = Validators()
