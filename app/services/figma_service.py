from utils.time import utcnow

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.helpers.token_helper import get_user_token, refresh_token_if_expired
from app.services.figma_oauth_service import FigmaOAuthService

logger = logging.getLogger("services.figma")


class FigmaService:
    @staticmethod
    def _validate_settings() -> None:
        if not settings.FIGMA_API_BASE_URL:
            raise ValueError("FIGMA_API_BASE_URL is not configured")

    @staticmethod
    async def _get_access_token(user_id: str) -> str:
        try:
            user_id_int = int(user_id)
        except (TypeError, ValueError):
            raise RuntimeError("Figma not connected. Please connect at /api/v1/figma/connect") from None

        token_data = get_user_token(user_id_int, "figma")
        if not token_data or not token_data.get("access_token"):
            raise RuntimeError("Figma not connected. Please connect at /api/v1/figma/connect")

        if token_data.get("expires_at") and utcnow() >= token_data["expires_at"] - timedelta(minutes=5):
            refreshed = await FigmaOAuthService.refresh_token(token_data.get("refresh_token") or "")
            if refreshed.get("access_token"):
                from app.helpers.token_helper import save_user_token

                save_user_token(
                    int(user_id),
                    "figma",
                    refreshed.get("access_token"),
                    refreshed.get("refresh_token"),
                    refreshed.get("expires_at"),
                )
                return refreshed["access_token"]

        return token_data["access_token"]

    @staticmethod
    async def api_request(
        access_token: str, path: str, method: str = "GET", json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        FigmaService._validate_settings()
        url = f"{settings.FIGMA_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                resp = await client.get(url, headers=headers)
            elif method.upper() == "POST":
                resp = await client.post(url, headers=headers, json=json)
            elif method.upper() == "PUT":
                resp = await client.put(url, headers=headers, json=json)
            elif method.upper() == "DELETE":
                resp = await client.delete(url, headers=headers, json=json)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        if resp.status_code == 429:
            logger.warning("Figma rate limit hit, retrying once")
            await asyncio.sleep(2)
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    resp = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    resp = await client.post(url, headers=headers, json=json)
                elif method.upper() == "PUT":
                    resp = await client.put(url, headers=headers, json=json)
                else:
                    resp = await client.delete(url, headers=headers, json=json)

        if resp.status_code >= 400:
            logger.error("Figma API request failed %s %s", resp.status_code, resp.text)
            raise ValueError(f"Figma API error: {resp.status_code} {resp.text}")

        return resp.json()

    @staticmethod
    async def list_figma_files(user_id: str) -> Dict[str, Any]:
        try:
            access_token = await FigmaService._get_access_token(user_id)
            payload = await FigmaService.api_request(access_token, "/me/files")
            files = payload.get("files", []) if isinstance(payload, dict) else []
            return {
                "success": True,
                "files": [
                    {
                        "name": item.get("name"),
                        "file_key": item.get("key") or item.get("file_key"),
                        "last_modified": item.get("last_modified"),
                    }
                    for item in files
                ],
            }
        except RuntimeError as exc:
            return {"success": False, "error": str(exc), "connect_url": "/api/v1/figma/connect"}
        except Exception as exc:
            logger.exception("Figma list files failed")
            return {"success": False, "error": f"Unable to list Figma files: {exc}"}

    @staticmethod
    async def get_figma_design(user_id: str, file_key: str) -> Dict[str, Any]:
        try:
            access_token = await FigmaService._get_access_token(user_id)
            payload = await FigmaService.api_request(access_token, f"/files/{file_key}")
            return {
                "success": True,
                "file": {
                    "name": payload.get("name"),
                    "file_key": payload.get("key") or file_key,
                    "pages": payload.get("pages", []),
                    "components": payload.get("components", []),
                    "details": payload,
                },
            }
        except RuntimeError as exc:
            return {"success": False, "error": str(exc), "connect_url": "/api/v1/figma/connect"}
        except Exception as exc:
            logger.exception("Figma get design failed")
            return {"success": False, "error": f"Unable to fetch Figma design: {exc}"}

    @staticmethod
    async def create_figma_file(user_id: str, name: str) -> Dict[str, Any]:
        try:
            access_token = await FigmaService._get_access_token(user_id)
            payload = await FigmaService.api_request(access_token, "/files", method="POST", json={"name": name})
            return {
                "success": True,
                "file_key": payload.get("key") or payload.get("file_key"),
                "edit_url": payload.get("edit_url") or payload.get("url"),
                "name": payload.get("name") or name,
            }
        except RuntimeError as exc:
            return {"success": False, "error": str(exc), "connect_url": "/api/v1/figma/connect"}
        except Exception as exc:
            logger.exception("Figma create file failed")
            return {"success": False, "error": f"Unable to create Figma file: {exc}"}

    @staticmethod
    async def export_figma_design(user_id: str, file_key: str, format: str = "png") -> Dict[str, Any]:
        try:
            access_token = await FigmaService._get_access_token(user_id)
            payload = await FigmaService.api_request(access_token, f"/images/{file_key}?format={format}")
            return {
                "success": True,
                "download_url": payload.get("images", {}).get(file_key) or payload.get("url"),
                "format": format,
            }
        except RuntimeError as exc:
            return {"success": False, "error": str(exc), "connect_url": "/api/v1/figma/connect"}
        except Exception as exc:
            logger.exception("Figma export failed")
            return {"success": False, "error": f"Unable to export Figma design: {exc}"}

    @staticmethod
    async def create_design(access_token: str, design_payload: Optional[Dict[str, Any]] = None, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Compatibility wrapper for existing routes."""
        if design_payload and isinstance(design_payload, dict):
            path = design_payload.get("path") or ""
            method = design_payload.get("method", "POST")
            body = design_payload.get("body")
            if path:
                return await FigmaService.api_request(access_token, path=path, method=method, json=body)

        return {
            "success": True,
            "note": "No direct Figma write path provided.",
            "prompt": prompt,
        }