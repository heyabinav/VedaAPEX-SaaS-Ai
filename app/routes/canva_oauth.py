import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.user import User
from app.models.user_oauth_tokens import UserOAuthToken
from app.routers.auth import get_current_user_auth
from app.services.canva_oauth_service import CanvaOAuthService
from app.helpers.token_helper import get_user_token, save_user_token, is_token_valid

logger = logging.getLogger("routes.canva_oauth")
router = APIRouter(prefix="/api/v1/canva", tags=["Canva OAuth"])


@router.get("/connect")
async def canva_connect(
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    try:
        state = f"user_id:{current_user.id}"
        auth_url = CanvaOAuthService.build_authorization_url(state)
        return {"success": True, "auth_url": auth_url, "state": state}
    except Exception as exc:
        logger.exception("Canva connect failed")
        raise HTTPException(status_code=500, detail=f"Unable to build Canva auth URL: {exc}") from exc


@router.get("/callback")
async def canva_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth code")

    try:
        token_data = await CanvaOAuthService.exchange_code(code)
        save_user_token(
            current_user.id,
            "canva",
            token_data.get("access_token"),
            token_data.get("refresh_token"),
            token_data.get("expires_at"),
            session=session,
        )
        return {"success": True, "message": "Canva connected successfully"}
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Canva callback failed")
        raise HTTPException(status_code=500, detail=f"Canva callback failed: {exc}") from exc


@router.get("/status")
async def canva_status(
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    token_data = get_user_token(current_user.id, "canva", session=session)
    return {
        "success": True,
        "connected": bool(token_data and token_data.get("access_token")),
        "valid": bool(token_data and token_data.get("access_token") and is_token_valid(current_user.id, "canva", session=session)),
        "expires_at": token_data.get("expires_at") if token_data else None,
    }


@router.delete("/disconnect")
async def canva_disconnect(
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    token_record = session.exec(
        select(UserOAuthToken).where(
            UserOAuthToken.user_id == current_user.id,
            UserOAuthToken.platform == "canva",
        )
    ).first()
    if not token_record:
        raise HTTPException(status_code=404, detail="No Canva connection found")
    session.delete(token_record)
    session.commit()
    return {"success": True, "message": "Canva disconnected successfully"}
