"""Pydantic schemas for Custom Skill management and execution."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CustomSkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Skill name")
    description: str = Field(default="", description="Short skill description")
    trigger_keywords: List[str] = Field(default_factory=list, description="Trigger keywords or phrases")
    instructions: str = Field(..., min_length=1, description="System prompt instructions for this skill")
    tools_config: Dict[str, Any] = Field(default_factory=dict, description="Optional tool configurations")


class CustomSkillUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    trigger_keywords: Optional[List[str]] = None
    instructions: Optional[str] = None
    tools_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class CustomSkillResponse(BaseModel):
    id: int
    user_id: int
    name: str
    slug: str
    description: str
    trigger_keywords: List[str]
    instructions: str
    tools_config: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CustomSkillListResponse(BaseModel):
    success: bool = True
    skills: List[CustomSkillResponse] = Field(default_factory=list)


class CustomSkillMatchRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message to match against active skills")


class CustomSkillMatchResponse(BaseModel):
    success: bool = True
    matched_skills: List[CustomSkillResponse] = Field(default_factory=list)


class CustomSkillExecuteRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    system_prompt: Optional[str] = Field(default=None, description="Optional base system prompt")
    provider: Optional[str] = Field(default="auto", description="LLM provider: groq, openai, gemini, or auto")
    model: Optional[str] = Field(default=None, description="Specific LLM model name")


class CustomSkillExecuteResponse(BaseModel):
    success: bool = True
    reply: str
    matched_skills: List[str] = Field(default_factory=list)
    provider: Optional[str] = None
    model: Optional[str] = None
