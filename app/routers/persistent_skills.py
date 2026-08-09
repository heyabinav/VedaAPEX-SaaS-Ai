"""API Router for Persistent User Skills (Hugging Face Dataset backend).

Endpoints:
- GET /api/v1/skills          - Get all persistent user skills
- POST /api/v1/skills         - Add or update a user skill
- GET /api/v1/skills/{id}     - Get single skill details
- PATCH /api/v1/skills/{id}   - Update a user skill
- DELETE /api/v1/skills/{id}  - Delete single skill
- DELETE /api/v1/skills       - Delete all skills for user (removes skills/{user_id}.json)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request

from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.schemas.persistent_skill import (
    SkillCreateRequest,
    SkillDeleteAllResponse,
    SkillItem,
    SkillSingleResponse,
    SkillUpdateRequest,
    UserSkillsFileResponse,
)
from app.services.hf_storage.skills import SkillStorageService

logger = logging.getLogger("routers.persistent_skills")

router = APIRouter(prefix="/skills", tags=["Persistent User Skills"])


@router.get("", response_model=UserSkillsFileResponse)
async def get_all_skills(
    user: User = Depends(get_current_user_auth),
):
    """Load all persistent skills for the authenticated user from Hugging Face Dataset storage."""
    data = SkillStorageService.load_skills(user.id)
    return UserSkillsFileResponse(
        user_id=str(data.get("user_id", user.id)),
        skills=[SkillItem(**s) for s in data.get("skills", []) if isinstance(s, dict)],
        updated_at=data.get("updated_at", ""),
    )


@router.post("", response_model=SkillSingleResponse)
async def add_skill(
    body: SkillCreateRequest,
    user: User = Depends(get_current_user_auth),
):
    """Add a new skill or update an existing skill for the authenticated user."""
    skill_dict = body.model_dump()
    saved = SkillStorageService.add_skill(user.id, skill_dict)
    return SkillSingleResponse(
        success=True,
        skill=SkillItem(**saved),
    )


@router.get("/{skill_id}", response_model=SkillSingleResponse)
async def get_skill(
    skill_id: str,
    user: User = Depends(get_current_user_auth),
):
    """Get single skill details by skill ID or name for the authenticated user."""
    skill = SkillStorageService.get_skill(user.id, skill_id)
    return SkillSingleResponse(
        success=True,
        skill=SkillItem(**skill),
    )


@router.patch("/{skill_id}", response_model=SkillSingleResponse)
async def update_skill(
    skill_id: str,
    body: SkillUpdateRequest,
    user: User = Depends(get_current_user_auth),
):
    """Update level, confidence, or source for a specific skill owned by the authenticated user."""
    update_data = body.model_dump(exclude_unset=True)
    updated = SkillStorageService.update_skill(user.id, skill_id, update_data)
    return SkillSingleResponse(
        success=True,
        skill=SkillItem(**updated),
    )


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: str,
    user: User = Depends(get_current_user_auth),
):
    """Delete a specific skill for the authenticated user."""
    SkillStorageService.delete_skill(user.id, skill_id)
    return {
        "success": True,
        "message": f"Skill '{skill_id}' successfully deleted.",
    }


@router.delete("", response_model=SkillDeleteAllResponse)
async def delete_all_skills(
    user: User = Depends(get_current_user_auth),
):
    """Delete all skills for the authenticated user (removes skills/{user_id}.json from Hugging Face)."""
    SkillStorageService.delete_all_skills(user.id)
    return SkillDeleteAllResponse(
        success=True,
        message="✅ Aapki saari skills delete kar di gayi hain.",
    )
