"""Unified connectors router - handles all providers via /connectors/{provider}/*."""

import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.db.session import get_session
from app.db.session import get_session_context as _get_session
from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.connectors.registry import connector_registry
from app.connectors.token_manager import (
    get_valid_access_token,
    store_connector_token,
    get_connector_status,
    disconnect_connector,
)

logger = logging.getLogger("routers.connectors")
router = APIRouter(prefix="/connectors", tags=["Connectors"])


@router.get("/providers")
async def list_providers():
    return {"success": True, "providers": connector_registry.providers()}


@router.get("/{provider}/login")
async def connector_login(
    provider: str,
    request: Request,
    current_user: User = Depends(get_current_user_auth),
):
    conn = connector_registry.get(provider)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Unknown connector: {provider}")

    if not conn.config.client_id:
        raise HTTPException(status_code=503, detail=f"{provider.title()} OAuth not configured")

    state = secrets.token_urlsafe(32)
    auth_url = conn.build_authorization_url(state)

    from app.helpers.token_helper import save_user_token
    with _get_session() as session:
        save_user_token(current_user.id, f"{provider}_state", state, None, session=session)

    logger.info("Connector login initiated: provider=%s user_id=%s", provider, current_user.id)
    return {"success": True, "provider": provider, "auth_url": auth_url, "state": state}


@router.get("/{provider}/callback")
async def connector_callback(
    provider: str,
    code: Optional[str] = None,
    state: Optional[str] = None,
):
    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth code")
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")

    conn = connector_registry.get(provider)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Unknown connector: {provider}")

    from app.helpers.token_helper import get_user_token

    with _get_session() as session:
        state_record = get_user_token(0, f"{provider}_state", session=session)

    from app.helpers.token_helper import _decrypt_text as _dt
    from sqlmodel import select
    from app.models.user_oauth_tokens import UserOAuthToken

    with _get_session() as session:
        record = session.exec(
            select(UserOAuthToken).where(
                UserOAuthToken.platform == f"{provider}_state",
            )
        ).first()
        if not record:
            raise HTTPException(status_code=400, detail="Invalid OAuth state - please try again")
        real_state = _dt(record.access_token) if record.access_token else ""
        user_id = record.user_id

    if state != real_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    try:
        tokens = await conn.exchange_code(code)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Connector callback failed: provider=%s", provider)
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {exc}") from exc

    with _get_session() as session:
        store_connector_token(user_id, provider, tokens, session)
        session.exec(
            select(UserOAuthToken).where(
                UserOAuthToken.platform == f"{provider}_state",
            )
        ).first()

    with _get_session() as session:
        record = session.exec(
            select(UserOAuthToken).where(
                UserOAuthToken.platform == f"{provider}_state",
                UserOAuthToken.user_id == user_id,
            )
        ).first()
        if record:
            session.delete(record)
            session.commit()

    logger.info("Connector connected: provider=%s user_id=%s", provider, user_id)
    return {"success": True, "provider": provider, "message": f"{provider.title()} connected successfully"}


@router.get("/{provider}/status")
async def connector_status(
    provider: str,
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    conn = connector_registry.get(provider)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Unknown connector: {provider}")

    return get_connector_status(current_user.id, provider, session)


@router.post("/{provider}/disconnect")
async def connector_disconnect(
    provider: str,
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    conn = connector_registry.get(provider)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Unknown connector: {provider}")

    from app.helpers.token_helper import get_user_token
    token_data = get_user_token(current_user.id, provider, session=session)
    if token_data and token_data.get("access_token"):
        try:
            await conn.revoke_token(token_data["access_token"])
        except Exception:
            pass

    removed = disconnect_connector(current_user.id, provider, session)
    if not removed:
        raise HTTPException(status_code=404, detail=f"No {provider.title()} connection found")

    return {"success": True, "provider": provider, "message": f"{provider.title()} disconnected successfully"}
