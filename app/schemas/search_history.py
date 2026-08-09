"""Schemas for saving and listing search history."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class SearchHistoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    query: str = Field(..., min_length=1, max_length=4000)
    source: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = Field(default=None, max_length=500)
    results: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("title", "query", "source", "notes")
    @classmethod
    def _strip_text(cls, value: Optional[str]):
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class SearchHistoryItem(BaseModel):
    id: int
    title: str
    query: str
    source: Optional[str] = None
    notes: Optional[str] = None
    result_count: int = 0
    created_at: datetime


class SearchHistoryResponse(BaseModel):
    success: bool
    message: str
    data: SearchHistoryItem


class SearchHistoryListResponse(BaseModel):
    success: bool
    data: list[SearchHistoryItem]
    pagination: dict[str, int]


class SearchHistoryResultsResponse(BaseModel):
    success: bool
    history_id: int
    title: str
    result_count: int
    results: list[dict[str, Any]]


class SearchTitleGenerateRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    source: Optional[str] = Field(default=None, max_length=120)
    results: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("query", "source")
    @classmethod
    def _strip_text(cls, value: Optional[str]):
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class SearchTitleGenerateResponse(BaseModel):
    success: bool
    title: str
    source: Optional[str] = None


class DeepSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    depth: Optional[str] = Field(default="deep", max_length=50)
    save_history: bool = Field(default=True)

    @field_validator("query", "depth")
    @classmethod
    def _strip_text(cls, value: Optional[str]):
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class DeepSearchResponse(BaseModel):
    success: bool = True
    query: str
    subqueries: list[str]
    report: str
    sources: list[dict[str, Any]]
    total_sources_found: int
    history_id: Optional[int] = None
