"""
Request schemas.
"""

from typing import Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request."""

    query: str = Field(..., min_length=2, max_length=200, description="Search query")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Results per page")

    class Config:
        json_schema_extra = {"example": {"query": "cancer cell", "page": 1, "page_size": 20}}
