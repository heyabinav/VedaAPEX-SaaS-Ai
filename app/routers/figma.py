import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.routers.oauth import router as oauth_router

from app.db.session import get_session
from app.models.user import User
from app.services.figma_oauth_service import FigmaOAuthService
from app.services.figma_service import FigmaService
from app.routers.oauth import _get_authenticated_local_user

logger = logging.getLogger("routers.figma")
router = APIRouter(prefix="/api/v1/figma", tags=["Figma"]) 


@router.post("/design")
async def create_figma_design(request: Request, body: dict, session: Session = Depends(get_session)):
    user = await _get_authenticated_local_user(request, session)
    if not user.figma_access_token:
        raise HTTPException(status_code=400, detail="Figma account not connected.")

    prompt_text = body.get("prompt")
    design_payload = body.get("design_payload")

    try:
        result = await FigmaService.create_design(
            access_token=user.figma_access_token, design_payload=design_payload, prompt=prompt_text
        )
        return {"success": True, "result": result}
    except Exception as exc:
        logger.exception("Figma design operation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/command")
async def create_figma_command(request: Request, body: dict, session: Session = Depends(get_session)):
    return await create_figma_design(request, body, session)


@router.get("/status")
async def figma_status(request: Request, session: Session = Depends(get_session)):
    user = await _get_authenticated_local_user(request, session)
    return {
        "success": True,
        "figma_connected": bool(user.figma_access_token),
        "figma_token_expires_at": user.figma_token_expires_at,
    }


# OAuth endpoints (non-prefixed for compatibility)


@oauth_router.get("/auth/figma/login")
async def figma_login(request: Request, session: Session = Depends(get_session), redirect: Optional[str] = None):
    user = await _get_authenticated_local_user(request, session)
    redirect_path = redirect if redirect and redirect.startswith("/") else "/"
    state_value = f"figma:{redirect_path}"
    login_url = FigmaOAuthService.build_authorization_url(state_value)
    return {"success": True, "provider": "figma", "auth_url": login_url, "redirect": False}


@oauth_router.get("/auth/figma/callback")
async def figma_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, session: Session = Depends(get_session)):
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    user = await _get_authenticated_local_user(request, session)
    try:
        token_data = await FigmaOAuthService.exchange_code(code)
    except Exception as exc:
        logger.exception("Figma token exchange failed: %s", exc)
        raise HTTPException(status_code=500, detail="Token exchange failed") from exc

    # save tokens on user
    user.figma_access_token = token_data.get("access_token")
    user.figma_refresh_token = token_data.get("refresh_token")
    user.figma_token_expires_at = token_data.get("expires_at")
    session.add(user)
    session.commit()
    session.refresh(user)

    return {"success": True, "connected": True}


@oauth_router.post("/auth/figma/refresh")
async def figma_refresh(request: Request, session: Session = Depends(get_session)):
    user = await _get_authenticated_local_user(request, session)
    if not user.figma_refresh_token:
        raise HTTPException(status_code=400, detail="Figma is not connected")

    try:
        token_data = await FigmaOAuthService.refresh_token(user.figma_refresh_token)
    except Exception as exc:
        logger.exception("Figma refresh failed: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to refresh Figma token") from exc

    user.figma_access_token = token_data.get("access_token")
    user.figma_refresh_token = token_data.get("refresh_token")
    user.figma_token_expires_at = token_data.get("expires_at")
    session.add(user)
    session.commit()
    session.refresh(user)

    return {"success": True, "figma_connected": True, "expires_at": token_data.get("expires_at")}
