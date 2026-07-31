"""Google Workspace OAuth routes - connect, callback, status, disconnect."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.user import User
from app.models.user_oauth_tokens import UserOAuthToken
from app.routers.auth import get_current_user_auth
from app.google.oauth import build_authorization_url, verify_state, exchange_code, revoke_token
from app.google.token_manager import store_token, GOOGLE_PLATFORM

logger = logging.getLogger("routes.google_oauth")
router = APIRouter(prefix="/api/v1/google", tags=["Google Workspace"])


@router.get("/connect")
async def google_connect(
    request: Request,
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    try:
        auth_url, state = build_authorization_url(current_user.id)
        return {"success": True, "auth_url": auth_url, "state": state}
    except Exception as exc:
        logger.exception("Google connect failed")
        raise HTTPException(status_code=500, detail=f"Unable to build Google auth URL: {exc}") from exc


@router.get("/callback")
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
):
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth code or state")

    user_id = verify_state(state)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        token_data = await exchange_code(code)

        from app.db.session import get_session as _get_session
        with _get_session() as session:
            store_token(user_id, token_data, session)

        return {"success": True, "message": "Google account connected successfully"}
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Google callback failed")
        raise HTTPException(status_code=500, detail=f"Google callback failed: {exc}") from exc


@router.get("/status")
async def google_status(
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    from app.helpers.token_helper import get_user_token, is_token_valid
    token_data = get_user_token(current_user.id, GOOGLE_PLATFORM, session=session)
    return {
        "success": True,
        "connected": bool(token_data and token_data.get("access_token")),
        "valid": bool(token_data and token_data.get("access_token") and is_token_valid(current_user.id, GOOGLE_PLATFORM, session=session)),
        "expires_at": token_data.get("expires_at") if token_data else None,
    }


@router.delete("/disconnect")
async def google_disconnect(
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    from app.helpers.token_helper import get_user_token
    token_data = get_user_token(current_user.id, GOOGLE_PLATFORM, session=session)
    if token_data and token_data.get("access_token"):
        await revoke_token(token_data["access_token"])

    token_record = session.exec(
        select(UserOAuthToken).where(
            UserOAuthToken.user_id == current_user.id,
            UserOAuthToken.platform == GOOGLE_PLATFORM,
        )
    ).first()
    if not token_record:
        raise HTTPException(status_code=404, detail="No Google connection found")
    session.delete(token_record)
    session.commit()
    return {"success": True, "message": "Google account disconnected successfully"}
