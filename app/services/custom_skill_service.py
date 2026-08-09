"""Service layer for Custom Skill CRUD, trigger keyword matching, and system prompt augmentation."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.custom_skill import UserCustomSkill
from app.models.user import User
from app.schemas.custom_skill import (
    CustomSkillCreate,
    CustomSkillResponse,
    CustomSkillUpdate,
)
from app.utils.time import utcnow

logger = logging.getLogger("services.custom_skills")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "custom_skill"


def _unique_slug(session: Session, user_id: int, base_slug: str, current_id: Optional[int] = None) -> str:
    slug = base_slug
    suffix = 1
    while True:
        existing = session.exec(
            select(UserCustomSkill).where(
                UserCustomSkill.user_id == user_id,
                UserCustomSkill.slug == slug,
            )
        ).first()
        if not existing or existing.id == current_id:
            return slug
        suffix += 1
        slug = f"{base_slug}_{suffix}"


def _to_response(skill: UserCustomSkill) -> CustomSkillResponse:
    try:
        triggers = json.loads(skill.trigger_keywords or "[]")
    except Exception:
        triggers = []

    try:
        tools_cfg = json.loads(skill.tools_config or "{}")
    except Exception:
        tools_cfg = {}

    return CustomSkillResponse(
        id=skill.id or 0,
        user_id=skill.user_id,
        name=skill.name,
        slug=skill.slug,
        description=skill.description,
        trigger_keywords=triggers if isinstance(triggers, list) else [],
        instructions=skill.instructions,
        tools_config=tools_cfg if isinstance(tools_cfg, dict) else {},
        is_active=skill.is_active,
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )


class CustomSkillService:
    @staticmethod
    def create_skill(session: Session, user: User, body: CustomSkillCreate) -> CustomSkillResponse:
        slug = _unique_slug(session, user.id, _slugify(body.name))

        triggers_json = json.dumps([kw.strip().lower() for kw in body.trigger_keywords if kw.strip()])
        tools_json = json.dumps(body.tools_config or {})

        skill = UserCustomSkill(
            user_id=user.id,
            name=body.name.strip(),
            slug=slug,
            description=body.description.strip(),
            trigger_keywords=triggers_json,
            instructions=body.instructions.strip(),
            tools_config=tools_json,
            is_active=True,
        )

        session.add(skill)
        session.commit()
        session.refresh(skill)

        logger.info("Created custom skill '%s' (id=%s) for user_id=%s", skill.name, skill.id, user.id)
        return _to_response(skill)

    @staticmethod
    def list_skills(session: Session, user: User, active_only: bool = False) -> List[CustomSkillResponse]:
        query = select(UserCustomSkill).where(UserCustomSkill.user_id == user.id)
        if active_only:
            query = query.where(UserCustomSkill.is_active == True)  # noqa: E712
        skills = session.exec(query.order_by(UserCustomSkill.updated_at.desc())).all()
        return [_to_response(s) for s in skills]

    @staticmethod
    def get_skill(session: Session, user: User, skill_id: int) -> UserCustomSkill:
        skill = session.get(UserCustomSkill, skill_id)
        if not skill or skill.user_id != user.id:
            raise HTTPException(status_code=404, detail="Custom skill not found")
        return skill

    @staticmethod
    def update_skill(session: Session, user: User, skill_id: int, body: CustomSkillUpdate) -> CustomSkillResponse:
        skill = CustomSkillService.get_skill(session, user, skill_id)

        if body.name is not None:
            skill.name = body.name.strip()
            skill.slug = _unique_slug(session, user.id, _slugify(body.name), current_id=skill.id)
        if body.description is not None:
            skill.description = body.description.strip()
        if body.trigger_keywords is not None:
            skill.trigger_keywords = json.dumps([kw.strip().lower() for kw in body.trigger_keywords if kw.strip()])
        if body.instructions is not None:
            skill.instructions = body.instructions.strip()
        if body.tools_config is not None:
            skill.tools_config = json.dumps(body.tools_config)
        if body.is_active is not None:
            skill.is_active = body.is_active

        skill.updated_at = utcnow()
        session.add(skill)
        session.commit()
        session.refresh(skill)

        logger.info("Updated custom skill id=%s for user_id=%s", skill.id, user.id)
        return _to_response(skill)

    @staticmethod
    def delete_skill(session: Session, user: User, skill_id: int) -> bool:
        skill = CustomSkillService.get_skill(session, user, skill_id)
        session.delete(skill)
        session.commit()
        logger.info("Deleted custom skill id=%s for user_id=%s", skill_id, user.id)
        return True

    @staticmethod
    def match_skills(session: Session, user: User, prompt_text: str) -> List[UserCustomSkill]:
        """Match prompt_text against active skills' trigger keywords for this user."""
        if not prompt_text:
            return []

        text_lower = prompt_text.lower()
        active_skills = session.exec(
            select(UserCustomSkill).where(
                UserCustomSkill.user_id == user.id,
                UserCustomSkill.is_active == True,  # noqa: E712
            )
        ).all()

        matched: List[UserCustomSkill] = []
        for skill in active_skills:
            try:
                keywords = json.loads(skill.trigger_keywords or "[]")
            except Exception:
                keywords = []

            # Check if skill name or any trigger keyword is in user text
            if skill.name.lower() in text_lower:
                matched.append(skill)
                continue

            for kw in keywords:
                if kw and (kw.lower() in text_lower):
                    matched.append(skill)
                    break

        return matched

    @staticmethod
    def build_augmented_system_prompt(base_prompt: Optional[str], matched_skills: List[UserCustomSkill]) -> str:
        """Inject instructions of matched skills into system prompt."""
        system_prompt = base_prompt or "You are a helpful AI assistant."
        if not matched_skills:
            return system_prompt

        skill_sections = []
        for skill in matched_skills:
            skill_sections.append(f"=== ACTIVE SKILL: {skill.name.upper()} ===\nDescription: {skill.description}\nInstructions:\n{skill.instructions}")

        augmented = f"{system_prompt}\n\n" + "\n\n".join(skill_sections)
        return augmented
