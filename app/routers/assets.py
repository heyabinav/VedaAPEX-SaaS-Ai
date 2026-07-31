"""
Media Proxy Router.

All AI-generated media is served through this router under the platform domain.
Frontend never receives provider URLs.

Endpoints:
- GET /api/v1/assets/{asset_id} - Serve an asset by ID
- GET /api/v1/assets/{asset_id}/download - Download an asset
- GET /api/v1/assets/proxy?url=... - Proxy a URL (for backward compat)
- GET /api/v1/assets/user/{user_id} - List user's assets
- GET /api/v1/assets/user/{user_id}/{type} - List user's assets by type
- DELETE /api/v1/assets/{asset_id} - Delete an asset (owner or admin)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlmodel import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_session
from app.middleware.auth_middleware import authenticate_user
from app.models.asset import AIAsset
from app.repositories.asset_repository import AssetRepository
from app.services.media_proxy_service import media_proxy

logger = logging.getLogger("app.routers.assets")

router = APIRouter(prefix="/assets", tags=["AI Assets & Media Proxy"])


@router.get("/{asset_id}")
async def serve_asset(
    asset_id: int,
    session: Session = Depends(get_session),
):
    """
    Serve an AI-generated asset through the platform proxy.

    This is the primary endpoint for viewing media. The URL is always under
    the platform domain, ensuring drag & drop protection.
    """
    asset = AssetRepository.get_by_id(session, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return media_proxy.serve_asset(
        r2_object_key=asset.r2_object_key,
        asset_id=asset.id,
        download=False,
    )


@router.get("/{asset_id}/download")
async def download_asset(
    asset_id: int,
    session: Session = Depends(get_session),
):
    """Download an AI-generated asset."""
    asset = AssetRepository.get_by_id(session, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    filename = asset.r2_object_key.split("/")[-1]
    return media_proxy.serve_asset(
        r2_object_key=asset.r2_object_key,
        asset_id=asset.id,
        filename=filename,
        download=True,
    )


@router.get("/user/{user_id}")
async def list_user_assets(
    user_id: int,
    asset_type: str = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(authenticate_user),
    session: Session = Depends(get_session),
):
    """List assets for a user. Users can only see their own assets, admins can see any."""
    if user.id != user_id and user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Cannot view other users' assets")

    assets, total = AssetRepository.get_by_user(
        session, user_id, asset_type=asset_type, page=page, limit=limit
    )

    return {
        "success": True,
        "data": {
            "assets": [
                {
                    "id": a.id,
                    "asset_type": a.asset_type,
                    "provider": a.provider,
                    "model": a.model,
                    "prompt": a.prompt[:100] if a.prompt else None,
                    "resolution": a.resolution,
                    "file_size_bytes": a.file_size_bytes,
                    "mime_type": a.mime_type,
                    "proxy_url": a.proxy_url,
                    "status": a.status,
                    "created_at": a.created_at.isoformat(),
                }
                for a in assets
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": max(1, -(-total // limit)),
            },
        },
    }


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: int,
    user=Depends(authenticate_user),
    session: Session = Depends(get_session),
):
    """Delete an asset. Owner or admin only."""
    asset = AssetRepository.get_by_id(session, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if asset.user_id != user.id and user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Cannot delete other users' assets")

    from app.services.asset_storage_service import asset_storage

    asset_storage.delete_asset(asset.r2_object_key)
    AssetRepository.delete(session, asset)

    logger.info(
        "Asset #%d deleted by user %d",
        asset_id,
        user.id,
    )

    return {"success": True, "message": "Asset deleted successfully"}
