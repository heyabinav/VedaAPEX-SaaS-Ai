from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.core.commands.executor import execute_command
from app.core.commands.registry import list_command_definitions
from app.core.commands.validator import CommandValidationError, validate_command_payload, validate_command_text

logger = logging.getLogger("routers.commands")

router = APIRouter(prefix="/commands", tags=["Commands"])


@router.get("", response_model=dict[str, Any])
async def list_commands(
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Return enabled commands for the authenticated user.

    Phase 1 is plumbing-only; real handlers are intentionally disabled.
    """
    del session
    del user
    return {
        "success": True,
        "commands": list_command_definitions(),
    }


@router.post("/validate", response_model=dict[str, Any])
async def validate_command_route(
    payload: dict[str, Any],
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Validate a raw or structured slash command payload."""
    del session
    del user
    try:
        if isinstance(payload, dict) and "message" in payload:
            parsed = validate_command_text(payload["message"])
        else:
            parsed = validate_command_payload(payload)
        return {
            "success": True,
            "valid": True,
            "parsed": parsed,
        }
    except CommandValidationError as exc:
        return {
            "success": False,
            "valid": False,
            "error": str(exc),
        }


@router.post("/execute", response_model=dict[str, Any])
async def execute_command_route(
    payload: dict[str, Any],
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Execute a slash command through the registry-driven execution layer."""
    del session
    del user
    try:
        result = execute_command(payload)
        return result
    except Exception as exc:  # keep the command boundary robust and non-crashing
        logger.warning("Command execution failed: %s", exc)
        return {
            "success": False,
            "status": "error",
            "message": str(exc),
            "fallback_to_chat": True,
        }
