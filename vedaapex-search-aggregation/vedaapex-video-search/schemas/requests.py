"""
Request schemas with Pydantic validation.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=80, description="Results per page")

    class Config:
        json_schema_extra = {"example": {"page": 1, "page_size": 20}}


class ImageSearchRequest(BaseModel):
    """Image search request."""

    query: str = Field(..., min_length=1, max_length=256, description="Search query")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=80, description="Results per page")
    sort: Optional[str] = Field(
        default="latest", description="Sort order: latest, popular, trending"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate and sanitize query."""
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {"query": "nature", "page": 1, "page_size": 20, "sort": "latest"}
        }


class VideoSearchRequest(BaseModel):
    """Video search request."""

    query: str = Field(..., min_length=1, max_length=256, description="Search query")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=80, description="Results per page")
    sort: Optional[str] = Field(
        default="latest", description="Sort order: latest, popular, trending"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate and sanitize query."""
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {"query": "nature", "page": 1, "page_size": 20, "sort": "latest"}
        }
