"""API Router for Custom Skill Management & Execution.

Endpoints:
- POST /api/v1/skills
- GET /api/v1/skills
- GET /api/v1/skills/{id}
- PATCH /api/v1/skills/{id}
- DELETE /api/v1/skills/{id}
- POST /api/v1/skills/match
- POST /api/v1/skills/execute
"""

from __future__ import annotations

import logging
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.schemas.custom_skill import (
    CustomSkillCreate,
    CustomSkillExecuteRequest,
    CustomSkillExecuteResponse,
    CustomSkillListResponse,
    CustomSkillMatchRequest,
    CustomSkillMatchResponse,
    CustomSkillResponse,
    CustomSkillUpdate,
)
from app.services.custom_skill_service import CustomSkillService, _to_response

logger = logging.getLogger("routers.custom_skills")

router = APIRouter(prefix="/skills", tags=["Custom Skills"])


@router.post("", response_model=CustomSkillResponse)
async def create_skill(
    body: CustomSkillCreate,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Create a new custom skill."""
    return CustomSkillService.create_skill(session, user, body)


@router.get("", response_model=CustomSkillListResponse)
async def list_skills(
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """List all custom skills for the current user."""
    skills = CustomSkillService.list_skills(session, user)
    return CustomSkillListResponse(success=True, skills=skills)


@router.get("/{id}", response_model=CustomSkillResponse)
async def get_skill(
    id: int,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Get details of a specific custom skill."""
    skill = CustomSkillService.get_skill(session, user, id)
    return _to_response(skill)


@router.patch("/{id}", response_model=CustomSkillResponse)
async def update_skill(
    id: int,
    body: CustomSkillUpdate,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Update an existing custom skill."""
    return CustomSkillService.update_skill(session, user, id, body)


@router.delete("/{id}")
async def delete_skill(
    id: int,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Delete a custom skill."""
    CustomSkillService.delete_skill(session, user, id)
    return {"success": True, "message": f"Skill #{id} deleted successfully."}


@router.post("/match", response_model=CustomSkillMatchResponse)
async def match_skills(
    body: CustomSkillMatchRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Test prompt against user's active skills to find matching trigger keywords."""
    matched = CustomSkillService.match_skills(session, user, body.message)
    return CustomSkillMatchResponse(
        success=True,
        matched_skills=[_to_response(s) for s in matched],
    )


@router.post("/execute", response_model=CustomSkillExecuteResponse)
async def execute_with_skills(
    body: CustomSkillExecuteRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Execute AI prompt with automatic custom skill matching and instruction injection."""
    matched_skills = CustomSkillService.match_skills(session, user, body.message)
    augmented_system_prompt = CustomSkillService.build_augmented_system_prompt(
        body.system_prompt,
        matched_skills,
    )

    from main import _call_chat_model, _extract_llm_content

    messages = [
        {"role": "system", "content": augmented_system_prompt},
        {"role": "user", "content": body.message},
    ]

    try:
        raw_result, provider_used, model_used = await _call_chat_model(
            provider=body.provider or "auto",
            messages=messages,
            model=body.model,
        )
        reply = _extract_llm_content(raw_result)
        return CustomSkillExecuteResponse(
            success=True,
            reply=reply,
            matched_skills=[s.name for s in matched_skills],
            provider=provider_used,
            model=model_used,
        )
    except Exception as exc:
        logger.error("Skill execution LLM call failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"LLM execution failed: {exc}") from exc
