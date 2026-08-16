"""Pydantic schemas for Persistent User Skills (stored on Hugging Face Dataset)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SkillCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Skill name (e.g. Python, React)")
    level: str = Field(..., description="Skill level: beginner, intermediate, advanced, expert")
    confidence: Optional[float] = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score 0.0 to 1.0")
    source: Optional[str] = Field(default="user_declared", description="Skill source: user_declared, user_requested, verified")


class SkillUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    level: Optional[str] = Field(default=None, description="beginner, intermediate, advanced, expert")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    source: Optional[str] = Field(default=None)


class SkillItem(BaseModel):
    id: str
    name: str
    level: str
    confidence: float = 1.0
    source: str = "user_declared"
    created_at: str
    updated_at: str


class SkillSingleResponse(BaseModel):
    success: bool = True
    skill: SkillItem


class UserSkillsFileResponse(BaseModel):
    user_id: str
    skills: List[SkillItem] = Field(default_factory=list)
    updated_at: str


class SkillDeleteAllResponse(BaseModel):
    success: bool = True
    message: str = "✅ Aapki saari skills delete kar di gayi hain."


# Skill Ingestion Schemas

class GitHubImportRequest(BaseModel):
    """Request to import a GitHub repository as a skill."""
    url: str = Field(..., description="GitHub repository URL (e.g., https://github.com/owner/repo)")
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Custom skill name (optional)")
    description: Optional[str] = Field(None, min_length=10, max_length=500, description="Custom description (optional)")
    level: Optional[str] = Field(None, description="Skill level: beginner, intermediate, advanced, expert (optional)")


class FolderImportRequest(BaseModel):
    """Request to import a folder as a skill."""
    skill_name: str = Field(..., min_length=2, max_length=100, description="Name for the imported skill")
    description: Optional[str] = Field(None, min_length=10, max_length=500, description="Skill description (optional)")
    level: Optional[str] = Field(None, description="Skill level: beginner, intermediate, advanced, expert (optional)")

