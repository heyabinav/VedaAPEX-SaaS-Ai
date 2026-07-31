"""Google Slides API service."""

import logging
from typing import Any, Optional

from app.google.credentials import google_api_call
from app.google.scopes import SLIDES_API, DRIVE_API

logger = logging.getLogger("google.slides")


async def create_presentation(user_id: int, session, title: str) -> dict:
    return await google_api_call(
        user_id, session, "POST", f"{SLIDES_API}/presentations",
        json_data={"title": title},
    )


async def add_slide(user_id: int, session, presentation_id: str, layout_id: Optional[str] = None) -> dict:
    requests_body = [{"createSlide": {"slideLayoutReference": {"layoutId": layout_id}} if layout_id else {}}]
    return await google_api_call(
        user_id, session, "POST", f"{SLIDES_API}/presentations/{presentation_id}:batchUpdate",
        json_data={"requests": requests_body},
    )


async def insert_text(user_id: int, session, presentation_id: str, page_object_id: str, text: str) -> dict:
    requests_body = [
        {
            "insertText": {
                "objectId": page_object_id,
                "insertionIndex": 0,
                "text": text,
            }
        }
    ]
    return await google_api_call(
        user_id, session, "POST", f"{SLIDES_API}/presentations/{presentation_id}:batchUpdate",
        json_data={"requests": requests_body},
    )


async def export_pdf(user_id: int, session, presentation_id: str) -> bytes:
    import httpx
    from app.google.token_manager import get_valid_token
    access_token = await get_valid_token(user_id, session)
    if not access_token:
        raise ValueError("Google account not connected")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"{DRIVE_API}/files/{presentation_id}/export",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"mimeType": "application/pdf"},
        )
    if response.status_code >= 400:
        raise ValueError(f"PDF export failed: {response.text}")
    return response.content
