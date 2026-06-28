"""
Helper utilities.
"""

import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class Helpers:
    """Helper utilities."""

    @staticmethod
    def generate_cache_key(prefix: str, query: str, page: int = 1) -> str:
        """
        Generate cache key from query and pagination.

        Args:
            prefix: Cache key prefix
            query: Search query
            page: Page number

        Returns:
            Cache key hash
        """
        key_str = f"{prefix}:{query}:{page}"
        return hashlib.md5(key_str.encode()).hexdigest()

    @staticmethod
    def get_timestamp() -> str:
        """Get current ISO timestamp."""
        return datetime.utcnow().isoformat()

    @staticmethod
    def parse_api_key_from_header(auth_header: Optional[str]) -> Optional[str]:
        """
        Parse API key from Authorization header.

        Args:
            auth_header: Authorization header value

        Returns:
            API key or None
        """
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return parts[1]

    @staticmethod
    def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """
        Truncate string to maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to append

        Returns:
            Truncated string
        """
        if len(text) <= max_length:
            return text

        return text[: max_length - len(suffix)] + suffix

    @staticmethod
    def extract_image_metadata(image_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant metadata from raw Pexels image data.

        Args:
            image_data: Raw image data from Pexels

        Returns:
            Extracted metadata
        """
        return {
            "id": str(image_data.get("id", "")),
            "title": image_data.get("alt", "Untitled"),
            "image_url": image_data.get("src", {}).get("original", ""),
            "thumbnail_url": image_data.get("src", {}).get("medium", ""),
            "photographer": image_data.get("photographer", "Unknown"),
            "photographer_url": image_data.get("photographer_url", ""),
            "source_url": image_data.get("url", ""),
            "width": image_data.get("width", 0),
            "height": image_data.get("height", 0),
            "avg_color": image_data.get("avg_color", ""),
        }

    @staticmethod
    def extract_video_metadata(video_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant metadata from raw Pexels video data.

        Args:
            video_data: Raw video data from Pexels

        Returns:
            Extracted metadata
        """
        video_files = video_data.get("video_files", [])
        video_url = ""
        if video_files:
            # Get the highest quality HD video or fallback to first available
            for video_file in video_files:
                if video_file.get("quality") == "hd":
                    video_url = video_file.get("link", "")
                    break
            if not video_url and video_files:
                video_url = video_files[0].get("link", "")

        image_data = video_data.get("image", "")

        return {
            "id": str(video_data.get("id", "")),
            "video_url": video_url,
            "thumbnail_url": image_data,
            "duration": video_data.get("duration", 0),
            "creator": video_data.get("user", {}).get("name", "Unknown"),
            "source_url": video_data.get("url", ""),
            "width": video_data.get("width", 0),
            "height": video_data.get("height", 0),
        }

    @staticmethod
    def merge_metadata(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge metadata dictionaries.

        Args:
            base: Base metadata
            updates: Updates to merge

        Returns:
            Merged metadata
        """
        result = base.copy()
        result.update(updates)
        return result


# Create singleton instance
helpers = Helpers()
