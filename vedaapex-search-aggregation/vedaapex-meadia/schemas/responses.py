"""
Response schemas.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MediaResult(BaseModel):
    """Single media result."""

    title: str = Field(..., description="Media title")
    media_type: str = Field(..., description="Type: image or video")
    image_url: Optional[str] = Field(None, description="Image URL")
    video_url: Optional[str] = Field(None, description="Video URL")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")
    source_url: str = Field(..., description="Source page URL")
    width: Optional[int] = Field(None, description="Width in pixels")
    height: Optional[int] = Field(None, description="Height in pixels")
    duration: Optional[float] = Field(None, description="Duration for videos")
    mime_type: Optional[str] = Field(None, description="MIME type")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Example image",
                "media_type": "image",
                "image_url": "https://upload.wikimedia.org/...",
                "thumbnail_url": "https://upload.wikimedia.org/...",
                "source_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
                "width": 1920,
                "height": 1080,
                "mime_type": "image/jpeg",
            }
        }


class Pagination(BaseModel):
    """Pagination info."""

    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Results per page")
    total_count: Optional[int] = Field(None, description="Total results")
    has_next: bool = Field(..., description="Has next page")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 20,
                "total_count": 1000,
                "has_next": True,
            }
        }


class SearchResponse(BaseModel):
    """Search response."""

    success: bool = Field(..., description="Success status")
    provider: str = Field(..., description="Provider name")
    query: str = Field(..., description="Search query")
    results: List[MediaResult] = Field(..., description="Results")
    pagination: Pagination = Field(..., description="Pagination info")
    timestamp: str = Field(..., description="Response timestamp")
    cached: bool = Field(default=False, description="From cache")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "provider": "wikimedia",
                "query": "cancer cell",
                "results": [],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_count": 1000,
                    "has_next": True,
                },
                "timestamp": "2024-01-01T12:00:00",
                "cached": False,
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Timestamp")
    provider: str = Field(..., description="Provider status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-01T12:00:00",
                "provider": "operational",
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
