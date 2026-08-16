"""Data models for media search."""

from typing import Any, List, Optional, Literal
from pydantic import BaseModel, Field


class MediaSearchRequest(BaseModel):
    """Unified media search request."""
    
    query: str = Field(..., min_length=2, max_length=200, description="Search query")
    type: Literal["auto", "image", "video", "space"] = Field(
        default="auto",
        description="Search type: auto-detect or explicit (image, video, space)"
    )
    limit: int = Field(default=10, ge=1, le=50, description="Number of results")
    page: int = Field(default=1, ge=1, description="Page number for pagination")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "human cell images",
                "type": "auto",
                "limit": 10,
                "page": 1
            }
        }


class MediaResult(BaseModel):
    """Normalized media result across all providers."""
    
    id: str = Field(..., description="Unique result ID")
    type: Literal["image", "video", "space"] = Field(..., description="Result type")
    title: str = Field(..., description="Title/name of the result")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail image URL")
    image_url: Optional[str] = Field(None, description="Full image URL (for images)")
    video_url: Optional[str] = Field(None, description="Video URL (for videos)")
    source_url: Optional[str] = Field(None, description="Source/clickable URL")
    source_name: Optional[str] = Field(None, description="Provider name (Pexels, NASA, etc.)")
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    duration: Optional[str] = Field(None, description="Video duration HH:MM:SS (for videos)")
    channel: Optional[str] = Field(None, description="Video channel/uploader (for videos)")
    description: Optional[str] = Field(None, description="Description/details")
    date: Optional[str] = Field(None, description="Publication/capture date (for NASA)")


class PaginationInfo(BaseModel):
    """Pagination details."""
    
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="Whether more results available")
    total_available: Optional[int] = Field(None, description="Total available results (if known)")


class MediaSearchResponse(BaseModel):
    """Unified search response."""
    
    success: bool = Field(..., description="Whether search succeeded")
    query: str = Field(..., description="Original search query")
    type: Literal["image", "video", "space"] = Field(..., description="Detected/requested search type")
    provider: str = Field(..., description="Provider used (pexels_image, pexels_video, nasa)")
    results: List[MediaResult] = Field(..., description="List of results")
    pagination: PaginationInfo = Field(..., description="Pagination info")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "query": "human cell",
                "type": "image",
                "provider": "pexels_image",
                "results": [
                    {
                        "id": "pexels_1234",
                        "type": "image",
                        "title": "Human Cell Under Microscope",
                        "thumbnail_url": "https://...",
                        "image_url": "https://...",
                        "source_url": "https://www.pexels.com/...",
                        "source_name": "Pexels",
                        "width": 1200,
                        "height": 800
                    }
                ],
                "pagination": {
                    "page": 1,
                    "limit": 10,
                    "has_more": True
                }
            }
        }


class MediaSearchErrorResponse(BaseModel):
    """Error response for media search."""
    
    success: bool = Field(default=False, description="Always false for errors")
    error: dict = Field(
        ...,
        description="Error details",
        json_schema_extra={
            "example": {
                "code": "INVALID_QUERY",
                "message": "Search query is empty or too short"
            }
        }
    )
