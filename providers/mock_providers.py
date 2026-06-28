"""Mock providers for demonstration."""

import logging

logger = logging.getLogger(__name__)


class MockProvider:
    """Mock provider for testing."""

    def __init__(self, name: str):
        self.name = name
        self.timeout = 15

    async def search_images(self, query: str, page: int = 1, page_size: int = 20) -> dict:
        """Mock image search."""
        logger.info(f"{self.name}: Searching images for '{query}'")
        return {
            "collection": {
                "items": [
                    {
                        "title": f"{query} - Result {i+1}",
                        "description": f"{query} result from {self.name}",
                        "url": f"https://example.com/{i+1}",
                        "image_url": f"https://example.com/image{i+1}.jpg",
                        "thumbnail_url": f"https://example.com/thumb{i+1}.jpg",
                        "source_url": f"https://example.com/source/{i+1}",
                    }
                    for i in range(page_size)
                ]
            }
        }

    async def search_videos(self, query: str, page: int = 1, page_size: int = 20) -> dict:
        """Mock video search."""
        logger.info(f"{self.name}: Searching videos for '{query}'")
        return {
            "collection": {
                "items": [
                    {
                        "title": f"{query} - Video {i+1}",
                        "description": f"{query} video from {self.name}",
                        "video_url": f"https://example.com/video{i+1}.mp4",
                        "thumbnail_url": f"https://example.com/thumb{i+1}.jpg",
                        "source_url": f"https://example.com/source/{i+1}",
                    }
                    for i in range(page_size)
                ]
            }
        }


class PexelsProvider(MockProvider):
    """Pexels provider stub."""

    def __init__(self):
        super().__init__("pexels")


class WikimediaProvider(MockProvider):
    """Wikimedia Commons provider stub."""

    def __init__(self):
        super().__init__("wikimedia")


class NASAProvider(MockProvider):
    """NASA provider stub."""

    def __init__(self):
        super().__init__("nasa")
