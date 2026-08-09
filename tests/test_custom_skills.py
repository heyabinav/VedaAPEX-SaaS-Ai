"""Automated test suite for Custom Skill Add System.

Tests:
1. Create custom skill with trigger keywords
2. List user custom skills
3. Get single custom skill details
4. Update custom skill (name, instructions, triggers, active status)
5. Delete custom skill
6. Prompt trigger keyword matching
7. Multi-tenant isolation (User A vs User B)
8. System prompt augmentation with skill instructions
"""

import json
import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.models.custom_skill import UserCustomSkill
from app.models.user import User
from app.schemas.custom_skill import CustomSkillCreate, CustomSkillUpdate
from app.services.custom_skill_service import CustomSkillService


@pytest.fixture(name="db_session")
def db_session_fixture():
    import app.models.user  # noqa: F401
    import app.models.token  # noqa: F401
    import app.models.custom_skill  # noqa: F401

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="user_a")
def user_a_fixture(db_session: Session):
    user = User(
        email="usera@vedaapex.com",
        full_name="User A",
        referral_code="ref_usera_101",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(name="user_b")
def user_b_fixture(db_session: Session):
    user = User(
        email="userb@vedaapex.com",
        full_name="User B",
        referral_code="ref_userb_202",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_custom_skill(db_session: Session, user_a: User):
    body = CustomSkillCreate(
        name="web_development",
        description="Expert web development skill",
        trigger_keywords=["website banao", "web page banao", "landing page"],
        instructions="HTML, CSS, JS use karo. Clean, responsive mobile-friendly design banao.",
        tools_config={"theme": "dark"},
    )
    created = CustomSkillService.create_skill(db_session, user_a, body)

    assert created.id > 0
    assert created.user_id == user_a.id
    assert created.name == "web_development"
    assert created.slug == "web_development"
    assert "website banao" in created.trigger_keywords
    assert created.instructions.startswith("HTML, CSS")


def test_list_and_get_skills(db_session: Session, user_a: User):
    body = CustomSkillCreate(
        name="seo_expert",
        description="SEO writing skill",
        trigger_keywords=["seo content", "keyword research"],
        instructions="Use H1, H2 tags and meta descriptions.",
    )
    CustomSkillService.create_skill(db_session, user_a, body)

    skills = CustomSkillService.list_skills(db_session, user_a)
    assert len(skills) >= 1
    assert any(s.name == "seo_expert" for s in skills)

    skill_id = skills[0].id
    fetched = CustomSkillService.get_skill(db_session, user_a, skill_id)
    assert fetched.id == skill_id


def test_update_and_delete_skill(db_session: Session, user_a: User):
    body = CustomSkillCreate(
        name="temp_skill",
        description="Temp",
        trigger_keywords=["temp"],
        instructions="Temp instructions",
    )
    created = CustomSkillService.create_skill(db_session, user_a, body)

    # Update
    update_body = CustomSkillUpdate(
        name="updated_temp_skill",
        instructions="Updated instructions",
    )
    updated = CustomSkillService.update_skill(db_session, user_a, created.id, update_body)
    assert updated.name == "updated_temp_skill"
    assert updated.instructions == "Updated instructions"

    # Delete
    deleted = CustomSkillService.delete_skill(db_session, user_a, created.id)
    assert deleted is True

    skills = CustomSkillService.list_skills(db_session, user_a)
    assert not any(s.id == created.id for s in skills)


def test_skill_prompt_trigger_matching(db_session: Session, user_a: User):
    body = CustomSkillCreate(
        name="web_development",
        description="Web Dev",
        trigger_keywords=["website banao", "landing page"],
        instructions="Use HTML, CSS, JS",
    )
    CustomSkillService.create_skill(db_session, user_a, body)

    # Match prompt containing trigger phrase
    matched = CustomSkillService.match_skills(db_session, user_a, "Mujhe ek naya landing page website banao")
    assert len(matched) == 1
    assert matched[0].name == "web_development"

    # Non-matching prompt
    unmatched = CustomSkillService.match_skills(db_session, user_a, "Tell me a joke about cats")
    assert len(unmatched) == 0


def test_multi_tenant_isolation(db_session: Session, user_a: User, user_b: User):
    body = CustomSkillCreate(
        name="private_skill_a",
        description="Private to A",
        trigger_keywords=["private_a"],
        instructions="Instructions A",
    )
    skill_a = CustomSkillService.create_skill(db_session, user_a, body)

    # User B lists skills → should NOT see User A's skill
    skills_b = CustomSkillService.list_skills(db_session, user_b)
    assert not any(s.id == skill_a.id for s in skills_b)

    # User B tries matching prompt with User A's trigger → should return empty
    matched_b = CustomSkillService.match_skills(db_session, user_b, "private_a trigger")
    assert len(matched_b) == 0


def test_system_prompt_augmentation(db_session: Session, user_a: User):
    body = CustomSkillCreate(
        name="code_reviewer",
        description="Code Review",
        trigger_keywords=["review code"],
        instructions="Check for security, performance, and readability.",
    )
    CustomSkillService.create_skill(db_session, user_a, body)

    matched = CustomSkillService.match_skills(db_session, user_a, "Please review code for this function")
    augmented_prompt = CustomSkillService.build_augmented_system_prompt(
        "You are a helpful assistant.",
        matched,
    )

    assert "ACTIVE SKILL: CODE_REVIEWER" in augmented_prompt
    assert "Check for security, performance, and readability." in augmented_prompt
