import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.user import User
from app.models.user_oauth_tokens import UserOAuthToken
from app.routers.auth import get_current_user_auth
from app.services.figma_oauth_service import FigmaOAuthService
from app.helpers.token_helper import get_user_token, save_user_token, is_token_valid

logger = logging.getLogger("routes.figma_oauth")
router = APIRouter(prefix="/api/v1/figma", tags=["Figma OAuth"])


@router.get("/connect")
async def figma_connect(
    request: Request,
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    try:
        state = f"user_id:{current_user.id}"
        auth_url = FigmaOAuthService.build_authorization_url(state)
        return {"success": True, "auth_url": auth_url, "state": state}
    except Exception as exc:
        logger.exception("Figma connect failed")
        raise HTTPException(status_code=500, detail=f"Unable to build Figma auth URL: {exc}") from exc


@router.get("/callback")
async def figma_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth code")

    try:
        token_data = await FigmaOAuthService.exchange_code(code)
        save_user_token(
            current_user.id,
            "figma",
            token_data.get("access_token"),
            token_data.get("refresh_token"),
            token_data.get("expires_at"),
            session=session,
        )
        return {"success": True, "message": "Figma connected successfully"}
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Figma callback failed")
        raise HTTPException(status_code=500, detail=f"Figma callback failed: {exc}") from exc


@router.get("/status")
async def figma_status(
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    token_data = get_user_token(current_user.id, "figma", session=session)
    return {
        "success": True,
        "connected": bool(token_data and token_data.get("access_token")),
        "valid": bool(token_data and token_data.get("access_token") and is_token_valid(current_user.id, "figma", session=session)),
        "expires_at": token_data.get("expires_at") if token_data else None,
    }


@router.delete("/disconnect")
async def figma_disconnect(
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    token_record = session.exec(
        select(UserOAuthToken).where(
            UserOAuthToken.user_id == current_user.id,
            UserOAuthToken.platform == "figma",
        )
    ).first()
    if not token_record:
        raise HTTPException(status_code=404, detail="No Figma connection found")
    session.delete(token_record)
    session.commit()
    return {"success": True, "message": "Figma disconnected successfully"}
