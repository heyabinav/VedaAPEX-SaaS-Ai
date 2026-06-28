"""
Response schemas with unified format.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ImageResult(BaseModel):
    """Single image result."""

    id: str = Field(..., description="Unique image ID")
    title: str = Field(..., description="Image title/description")
    image_url: str = Field(..., description="Full resolution image URL")
    thumbnail_url: str = Field(..., description="Thumbnail image URL")
    photographer: str = Field(..., description="Photographer name")
    photographer_url: Optional[str] = Field(None, description="Photographer profile URL")
    source_url: str = Field(..., description="Source/attribution URL")
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    avg_color: Optional[str] = Field(None, description="Average color")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "12345",
                "title": "Mountain landscape",
                "image_url": "https://images.pexels.com/...",
                "thumbnail_url": "https://images.pexels.com/...",
                "photographer": "John Doe",
                "photographer_url": "https://www.pexels.com/...",
                "source_url": "https://www.pexels.com/photo/...",
                "width": 5000,
                "height": 3000,
                "avg_color": "#90A870",
            }
        }


class VideoResult(BaseModel):
    """Single video result."""

    id: str = Field(..., description="Unique video ID")
    video_url: str = Field(..., description="HD video URL")
    thumbnail_url: str = Field(..., description="Thumbnail image URL")
    duration: int = Field(..., description="Video duration in seconds")
    creator: str = Field(..., description="Creator/videographer name")
    source_url: str = Field(..., description="Source/attribution URL")
    width: int = Field(..., description="Video width in pixels")
    height: int = Field(..., description="Video height in pixels")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "12345",
                "video_url": "https://videos.pexels.com/...",
                "thumbnail_url": "https://images.pexels.com/...",
                "duration": 60,
                "creator": "Jane Smith",
                "source_url": "https://www.pexels.com/video/...",
                "width": 1920,
                "height": 1080,
            }
        }


class Pagination(BaseModel):
    """Pagination information."""

    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Results per page")
    total_count: Optional[int] = Field(None, description="Total number of results")
    has_next: bool = Field(..., description="Whether more results are available")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 20,
                "total_count": 5000,
                "has_next": True,
            }
        }


class ImageSearchResponse(BaseModel):
    """Image search response."""

    success: bool = Field(..., description="Whether request was successful")
    query: str = Field(..., description="Search query")
    provider: str = Field(..., description="Provider name")
    results: List[ImageResult] = Field(..., description="Search results")
    pagination: Pagination = Field(..., description="Pagination info")
    timestamp: str = Field(..., description="Response timestamp")
    cached: bool = Field(default=False, description="Whether result was cached")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "query": "nature",
                "provider": "pexels",
                "results": [],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_count": 5000,
                    "has_next": True,
                },
                "timestamp": "2024-01-01T12:00:00",
                "cached": False,
            }
        }


class VideoSearchResponse(BaseModel):
    """Video search response."""

    success: bool = Field(..., description="Whether request was successful")
    query: str = Field(..., description="Search query")
    provider: str = Field(..., description="Provider name")
    results: List[VideoResult] = Field(..., description="Search results")
    pagination: Pagination = Field(..., description="Pagination info")
    timestamp: str = Field(..., description="Response timestamp")
    cached: bool = Field(default=False, description="Whether result was cached")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "query": "nature",
                "provider": "pexels",
                "results": [],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_count": 5000,
                    "has_next": True,
                },
                "timestamp": "2024-01-01T12:00:00",
                "cached": False,
            }
        }


class ErrorResponse(BaseModel):
    """Error response."""

    success: bool = Field(default=False, description="Always False for errors")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: str = Field(..., description="Error timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "ValidationError",
                "message": "Query must be at least 1 character",
                "status_code": 400,
                "timestamp": "2024-01-01T12:00:00",
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Check timestamp")
    uptime: Optional[float] = Field(None, description="Uptime in seconds")
    cache_status: Optional[str] = Field(None, description="Cache status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-01T12:00:00",
                "uptime": 3600.5,
                "cache_status": "operational",
            }
        }
