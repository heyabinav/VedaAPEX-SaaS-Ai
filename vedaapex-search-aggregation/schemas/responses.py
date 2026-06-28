"""Response schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """Single search result."""

    title: str = Field(..., description="Result title")
    description: Optional[str] = Field(None, description="Description")
    media_type: str = Field(..., description="image or video")
    provider: str = Field(..., description="Provider name")
    image_url: Optional[str] = Field(None, description="Image URL")
    video_url: Optional[str] = Field(None, description="Video URL")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")
    source_url: str = Field(..., description="Source page URL")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Cancer Cell under Microscope",
                "description": "High resolution cancer cell image",
                "media_type": "image",
                "provider": "wikimedia",
                "image_url": "https://example.com/image.jpg",
                "thumbnail_url": "https://example.com/thumb.jpg",
                "source_url": "https://commons.wikimedia.org/...",
            }
        }


class Pagination(BaseModel):
    """Pagination info."""

    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Results per page")
    has_next: bool = Field(..., description="Has next page")


class UnifiedSearchResponse(BaseModel):
    """Unified search response."""

    success: bool = Field(..., description="Success status")
    query: str = Field(..., description="Search query")
    selected_provider: str = Field(..., description="Primary provider used")
    fallback_providers: List[str] = Field(..., description="Fallback providers")
    results: List[SearchResult] = Field(..., description="Search results")
    pagination: Pagination = Field(..., description="Pagination info")
    timestamp: str = Field(..., description="Response timestamp")
    cached: bool = Field(default=False, description="From cache")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "query": "cancer cell",
                "selected_provider": "wikimedia",
                "fallback_providers": ["nasa", "pexels"],
                "results": [],
                "pagination": {"page": 1, "page_size": 20, "has_next": True},
                "timestamp": "2024-01-15T10:30:00",
                "cached": False,
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    providers: List[str] = Field(..., description="Available providers")
    timestamp: str = Field(..., description="Timestamp")


class ErrorResponse(BaseModel):
    """Error response."""

    success: bool = Field(default=False)
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status")
    timestamp: str = Field(..., description="Timestamp")
