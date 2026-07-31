import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.core.config import settings
from app.helpers.token_helper import get_user_token, save_user_token
from app.services.canva_oauth_service import CanvaOAuthService

logger = logging.getLogger("canva.design")


class CanvaService:
    @staticmethod
    async def _get_access_token(user_id: str) -> str:
        try:
            user_id_int = int(user_id)
        except (TypeError, ValueError):
            raise RuntimeError("Canva not connected. Please connect at /api/v1/canva/connect") from None

        token_data = get_user_token(user_id_int, "canva")
        if not token_data or not token_data.get("access_token"):
            raise RuntimeError("Canva not connected. Please connect at /api/v1/canva/connect")

        if token_data.get("expires_at") and datetime.utcnow() >= token_data["expires_at"] - timedelta(minutes=5):
            refreshed = await CanvaOAuthService.refresh_token(token_data.get("refresh_token") or "")
            if refreshed.get("access_token"):
                save_user_token(
                    int(user_id),
                    "canva",
                    refreshed.get("access_token"),
                    refreshed.get("refresh_token"),
                    refreshed.get("expires_at"),
                )
                return refreshed["access_token"]

        return token_data["access_token"]

    @staticmethod
    async def _request(access_token: str, method: str, url: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await getattr(client, method.lower())(url, headers=headers, json=json)
        if response.status_code == 429:
            logger.warning("Canva rate limit hit, retrying once")
            await asyncio.sleep(2)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await getattr(client, method.lower())(url, headers=headers, json=json)
        if response.status_code >= 400:
            logger.error("Canva API request failed %s %s", response.status_code, response.text)
            raise ValueError(f"Canva API error: {response.status_code} {response.text}")
        return response.json()

    @staticmethod
    async def list_canva_designs(user_id: str) -> dict[str, Any]:
        try:
            access_token = await CanvaService._get_access_token(user_id)
            payload = await CanvaService._request(access_token, "GET", f"{settings.CANVA_API_BASE_URL.rstrip('/')}/designs")
            items = payload.get("items", []) if isinstance(payload, dict) else []
            return {
                "success": True,
                "designs": [
                    {
                        "title": item.get("title") or item.get("name"),
                        "design_id": item.get("id"),
                        "preview_url": item.get("preview_url") or item.get("thumbnail_url"),
                    }
                    for item in items
                ],
            }
        except RuntimeError as exc:
            return {"success": False, "error": str(exc), "connect_url": "/api/v1/canva/connect"}
        except Exception as exc:
            logger.exception("Canva list designs failed")
            return {"success": False, "error": f"Unable to list Canva designs: {exc}"}

    @staticmethod
    async def create_canva_design(user_id: str, title: str, design_type: str) -> dict[str, Any]:
        try:
            access_token = await CanvaService._get_access_token(user_id)
            payload = {
                "title": title,
                "design_type": design_type,
            }
            result = await CanvaService._request(access_token, "POST", f"{settings.CANVA_API_BASE_URL.rstrip('/')}/designs", json=payload)
            return {
                "success": True,
                "design_id": result.get("id"),
                "edit_url": result.get("edit_url") or result.get("url"),
            }
        except RuntimeError as exc:
            return {"success": False, "error": str(exc), "connect_url": "/api/v1/canva/connect"}
        except Exception as exc:
            logger.exception("Canva create design failed")
            return {"success": False, "error": f"Unable to create Canva design: {exc}"}

    @staticmethod
    async def get_canva_design(user_id: str, design_id: str) -> dict[str, Any]:
        try:
            access_token = await CanvaService._get_access_token(user_id)
            payload = await CanvaService._request(access_token, "GET", f"{settings.CANVA_API_BASE_URL.rstrip('/')}/designs/{design_id}")
            return {
                "success": True,
                "design": {
                    "design_id": payload.get("id") or design_id,
                    "title": payload.get("title") or payload.get("name"),
                    "preview_url": payload.get("preview_url") or payload.get("thumbnail_url"),
                    "details": payload,
                },
            }
        except RuntimeError as exc:
            return {"success": False, "error": str(exc), "connect_url": "/api/v1/canva/connect"}
        except Exception as exc:
            logger.exception("Canva get design failed")
            return {"success": False, "error": f"Unable to fetch Canva design: {exc}"}

    @staticmethod
    async def export_canva_design(user_id: str, design_id: str, format: str = "pdf") -> dict[str, Any]:
        try:
            access_token = await CanvaService._get_access_token(user_id)
            payload = await CanvaService._request(access_token, "GET", f"{settings.CANVA_API_BASE_URL.rstrip('/')}/designs/{design_id}/export?format={format}")
            return {
                "success": True,
                "download_url": payload.get("download_url") or payload.get("url"),
                "format": format,
            }
        except RuntimeError as exc:
            return {"success": False, "error": str(exc), "connect_url": "/api/v1/canva/connect"}
        except Exception as exc:
            logger.exception("Canva export failed")
            return {"success": False, "error": f"Unable to export Canva design: {exc}"}

    @staticmethod
    async def duplicate_canva_design(user_id: str, design_id: str, new_title: str) -> dict[str, Any]:
        try:
            access_token = await CanvaService._get_access_token(user_id)
            payload = await CanvaService._request(access_token, "POST", f"{settings.CANVA_API_BASE_URL.rstrip('/')}/designs/{design_id}/duplicate", json={"title": new_title})
            return {
                "success": True,
                "design_id": payload.get("id"),
                "edit_url": payload.get("edit_url") or payload.get("url"),
            }
        except RuntimeError as exc:
            return {"success": False, "error": str(exc), "connect_url": "/api/v1/canva/connect"}
        except Exception as exc:
            logger.exception("Canva duplicate design failed")
            return {"success": False, "error": f"Unable to duplicate Canva design: {exc}"}

    @staticmethod
    async def create_design(
        access_token: str,
        prompt: str | None = None,
        title: str | None = None,
        template_id: str | None = None,
        style: str | None = None,
        metadata: dict[str, Any] | None = None,
        design_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not access_token:
            raise ValueError("Missing Canva access token")

        url = f"{settings.CANVA_API_BASE_URL.rstrip('/')}/designs"
        if design_payload:
            payload = design_payload
        else:
            payload = {
                "name": title or f"AI Design - {prompt or 'Untitled'}",
                "description": prompt or "Generated by VedaApex",
                "metadata": metadata or {},
                "source": {"type": "api", "name": "VedaApex"},
                "data": {
                    "prompt": prompt,
                    "style": style,
                    "template_id": template_id,
                },
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            if "data" in payload:
                payload["data"] = {k: v for k, v in payload["data"].items() if v is not None}

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code not in {200, 201}:
            logger.error("Canva design creation failed %s %s", response.status_code, response.text)
            raise ValueError(f"Canva design creation failed: {response.text}")

        return response.json()
