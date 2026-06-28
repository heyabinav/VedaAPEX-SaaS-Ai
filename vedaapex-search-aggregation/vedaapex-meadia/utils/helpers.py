"""
Helper utilities.
"""

import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime


class Helpers:
    """Helper utilities."""

    @staticmethod
    def generate_cache_key(prefix: str, query: str, page: int = 1) -> str:
        """Generate cache key."""
        key_str = f"{prefix}:{query}:{page}"
        return hashlib.md5(key_str.encode()).hexdigest()

    @staticmethod
    def get_timestamp() -> str:
        """Get ISO timestamp."""
        return datetime.utcnow().isoformat()

    @staticmethod
    def truncate_string(text: str, max_length: int = 100) -> str:
        """Truncate string."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    @staticmethod
    def extract_file_extension(filename: str) -> str:
        """Extract file extension."""
        if "." not in filename:
            return ""
        return filename.split(".")[-1].lower()

    @staticmethod
    def is_image(filename: str) -> bool:
        """Check if file is image."""
        image_extensions = ["jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "tiff"]
        ext = Helpers.extract_file_extension(filename)
        return ext in image_extensions

    @staticmethod
    def is_video(filename: str) -> bool:
        """Check if file is video."""
        video_extensions = ["webm", "ogv", "mp4", "mpeg", "mov", "avi"]
        ext = Helpers.extract_file_extension(filename)
        return ext in video_extensions

    @staticmethod
    def extract_image_metadata(file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract image metadata from Wikimedia response."""
        try:
            # Get file title/name
            title = file_data.get("title", "Untitled")

            # Get image info
            imageinfo = file_data.get("imageinfo", [{}])[0] if file_data.get("imageinfo") else {}

            # Build thumbnail URL
            thumbnail_url = imageinfo.get("thumburl", "")

            # Get full image URL
            image_url = imageinfo.get("url", "")

            # Get source URL
            source_url = f"https://commons.wikimedia.org/wiki/File:{title.replace(' ', '_')}"

            return {
                "title": title,
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "source_url": source_url,
                "media_type": "image",
                "width": imageinfo.get("width", 0),
                "height": imageinfo.get("height", 0),
                "mime_type": imageinfo.get("mime", ""),
            }
        except Exception as e:
            return {}

    @staticmethod
    def extract_video_metadata(file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract video metadata from Wikimedia response."""
        try:
            title = file_data.get("title", "Untitled")

            imageinfo = file_data.get("imageinfo", [{}])[0] if file_data.get("imageinfo") else {}

            # Get video URL
            video_url = imageinfo.get("url", "")

            # Get thumbnail
            thumbnail_url = imageinfo.get("thumburl", "")

            # Get source URL
            source_url = f"https://commons.wikimedia.org/wiki/File:{title.replace(' ', '_')}"

            return {
                "title": title,
                "video_url": video_url,
                "thumbnail_url": thumbnail_url,
                "source_url": source_url,
                "media_type": "video",
                "duration": imageinfo.get("duration", 0),
                "mime_type": imageinfo.get("mime", ""),
            }
        except Exception as e:
            return {}


helpers = Helpers()
