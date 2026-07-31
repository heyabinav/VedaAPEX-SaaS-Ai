import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.schemas.canva import CanvaDesignRequest
from app.services.canva_design_service import CanvaDesignService
from app.routers.oauth import _get_authenticated_local_user

logger = logging.getLogger("routers.canva")
router = APIRouter(prefix="/api/v1/canva", tags=["Canva"])


@router.post("/design")
async def create_canva_design(
    request: Request,
    body: CanvaDesignRequest,
    session: Session = Depends(get_session),
):
    user = await _get_authenticated_local_user(request, session)
    if not user.canva_access_token:
        raise HTTPException(status_code=400, detail="Canva account not connected.")

    prompt_text = None
    if body.design_payload is None:
        try:
            prompt_text = body.get_prompt()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        design = await CanvaDesignService.create_design(
            access_token=user.canva_access_token,
            prompt=prompt_text,
            title=body.title,
            template_id=body.template_id,
            style=body.style,
            metadata=body.metadata,
            design_payload=body.design_payload,
        )
        response_payload = {
            "success": True,
            "input_type": body.input_type,
            "design": design,
        }
        if prompt_text:
            response_payload["prompt"] = prompt_text
        if body.design_payload is not None:
            response_payload["design_payload"] = body.design_payload
        return response_payload
    except Exception as exc:
        logger.exception("Canva design creation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/command")
async def create_canva_command(
    request: Request,
    body: CanvaDesignRequest,
    session: Session = Depends(get_session),
):
    return await create_canva_design(request, body, session)


@router.get("/status")
async def canva_status(request: Request, session: Session = Depends(get_session)):
    user = await _get_authenticated_local_user(request, session)
    return {
        "success": True,
        "canva_connected": bool(user.canva_access_token),
        "canva_token_expires_at": user.canva_token_expires_at,
    }
