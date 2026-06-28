"""Request schemas."""

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Unified search request."""

    query: str = Field(..., min_length=2, max_length=200, description="Search query")
    media_type: str = Field(default="image", description="image or video")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Results per page")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "cancer cell",
                "media_type": "image",
                "page": 1,
                "page_size": 20,
            }
        }


class ImageSearchRequest(BaseModel):
    """Image search request."""

    query: str = Field(..., min_length=2, max_length=200)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class VideoSearchRequest(BaseModel):
    """Video search request."""

    query: str = Field(..., min_length=2, max_length=200)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
