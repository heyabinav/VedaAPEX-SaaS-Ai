"""Main Media Search Service - Orchestrates all providers."""

import logging
from typing import Literal

from .models import MediaSearchRequest, MediaSearchResponse
from .intent_router import detect_intent, should_use_nasa
from .image_provider import ImageSearchProvider
from .video_provider import VideoSearchProvider
from .nasa_provider import NASASearchProvider

logger = logging.getLogger("app.services.media_search")


class MediaSearchService:
    """Unified media search service with intelligent provider routing."""
    
    def __init__(self):
        """Initialize all providers."""
        self.image_provider = ImageSearchProvider()
        self.video_provider = VideoSearchProvider()
        self.nasa_provider = NASASearchProvider()
    
    async def search(self, request: MediaSearchRequest) -> MediaSearchResponse:
        """
        Execute unified media search.
        
        Flow:
        1. Validate request
        2. Determine search type (auto-detect or explicit)
        3. Route to appropriate provider
        4. Return normalized response
        
        Args:
            request: MediaSearchRequest with query, type, limit, page
            
        Returns:
            Normalized MediaSearchResponse
            
        Raises:
            RuntimeError: For various error codes like INVALID_QUERY, UNSUPPORTED_SEARCH_TYPE, etc.
        """
        # Step 1: Validate query
        query = request.query.strip()
        if not query or len(query) < 2:
            raise RuntimeError("INVALID_QUERY: Query must be at least 2 characters")
        if len(query) > 200:
            raise RuntimeError("INVALID_QUERY: Query must be less than 200 characters")
        
        # Step 2: Determine search type
        search_type: Literal["image", "video", "space"] = request.type  # type: ignore
        
        if request.type == "auto":
            search_type = detect_intent(query)
            logger.debug(f"Auto-detected intent: {search_type} for query: {query}")
            
            # Special case: for space queries, check if NASA is appropriate
            if search_type == "image" and should_use_nasa(query):
                search_type = "space"
                logger.debug(f"Routing to NASA instead of image search for: {query}")
        else:
            if request.type not in ["image", "video", "space"]:
                raise RuntimeError(f"UNSUPPORTED_SEARCH_TYPE: Supported types are auto, image, video, space")
        
        logger.info(f"Media search: query='{query}' type={search_type} limit={request.limit} page={request.page}")
        
        # Step 3: Route to provider
        try:
            if search_type == "image":
                response = await self.image_provider.search(
                    query=query,
                    limit=request.limit,
                    page=request.page
                )
            elif search_type == "video":
                response = await self.video_provider.search(
                    query=query,
                    limit=request.limit,
                    page=request.page
                )
            elif search_type == "space":
                response = await self.nasa_provider.search(
                    query=query,
                    limit=request.limit,
                    page=request.page
                )
            else:
                raise RuntimeError(f"UNSUPPORTED_SEARCH_TYPE: {search_type}")
            
            logger.info(f"Search successful: got {len(response.results)} results")
            return response
            
        except RuntimeError as e:
            # Re-raise runtime errors (provider-specific errors)
            logger.error(f"Search error: {e}")
            raise
        except Exception as e:
            # Catch unexpected errors
            logger.exception(f"Unexpected error in media search: {e}")
            raise RuntimeError(f"SEARCH_ERROR: {str(e)}")
