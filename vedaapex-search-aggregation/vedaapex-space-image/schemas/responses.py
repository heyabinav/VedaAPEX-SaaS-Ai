"""
Response schemas.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class MediaResult(BaseModel):
    """Single media result from unified provider."""

    title: str = Field(..., description="Media title")
    description: str = Field(default="", description="Media description")
    media_type: str = Field(..., description="Type: image or video")
    provider: str = Field(..., description="Provider name: nasa, wikimedia, pexels")
    image_url: Optional[str] = Field(None, description="Image URL (for images)")
    video_url: Optional[str] = Field(None, description="Video URL (for videos)")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")
    source_url: str = Field(..., description="Source page URL")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Mars Rover Curiosity",
                "description": "Curiosity rover exploring Mars surface",
                "media_type": "image",
                "provider": "nasa",
                "image_url": "https://example.com/image.jpg",
                "thumbnail_url": "https://example.com/thumb.jpg",
                "source_url": "https://nasa.gov/...",
            }
        }


class Pagination(BaseModel):
    """Pagination info."""

    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Results per page")
    has_next: bool = Field(..., description="Has next page")

    class Config:
        json_schema_extra = {"example": {"page": 1, "page_size": 20, "has_next": True}}


class SearchResponse(BaseModel):
    """Search response."""

    success: bool = Field(..., description="Success status")
    provider: str = Field(..., description="Provider(s) used")
    query: str = Field(..., description="Search query")
    results: List[MediaResult] = Field(..., description="Search results")
    pagination: Pagination = Field(..., description="Pagination info")
    timestamp: str = Field(..., description="Response timestamp")
    cached: bool = Field(default=False, description="From cache")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "provider": "multi-provider",
                "query": "mars rover",
                "results": [],
                "pagination": {"page": 1, "page_size": 20, "has_next": True},
                "timestamp": "2024-01-01T12:00:00",
                "cached": False,
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Timestamp")
    providers: List[str] = Field(..., description="Available providers")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-01T12:00:00",
                "providers": ["nasa", "wikimedia", "pexels"],
            }
        }


class ErrorResponse(BaseModel):
    """Error response."""

    success: bool = Field(default=False, description="Always False")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status")
    timestamp: str = Field(..., description="Timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "ValidationError",
                "message": "Query is too short",
                "status_code": 400,
                "timestamp": "2024-01-01T12:00:00",
            }
        }
