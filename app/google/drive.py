"""Google Drive API service."""

import logging
from typing import Any, Optional

from app.google.credentials import google_api_call
from app.google.scopes import DRIVE_API

logger = logging.getLogger("google.drive")


async def search_files(user_id: int, session, query: str = "", max_results: int = 10) -> dict:
    params = {"q": query, "pageSize": min(max_results, 100), "fields": "files(id,name,mimeType,modifiedTime,size)"}
    return await google_api_call(user_id, session, "GET", f"{DRIVE_API}/files", params=params)


async def upload_file(user_id: int, session, file_name: str, file_content: bytes, mime_type: str = "application/octet-stream", folder_id: Optional[str] = None) -> dict:
    import base64
    metadata = {"name": file_name}
    if folder_id:
        metadata["parents"] = [folder_id]
    metadata_str = __import__("json").dumps(metadata)
    boundary = "----VedaApexBoundary"
    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{metadata_str}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8") + file_content + f"\r\n--{boundary}--\r\n".encode("utf-8")

    import httpx
    from app.google.token_manager import get_valid_token
    access_token = await get_valid_token(user_id, session)
    if not access_token:
        raise ValueError("Google account not connected")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{DRIVE_API}/upload/files",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"uploadType": "multipart", "fields": "id,name,mimeType"},
            content=body,
        )
    if response.status_code >= 400:
        raise ValueError(f"Upload failed: {response.text}")
    return response.json()


async def download_file(user_id: int, session, file_id: str) -> bytes:
    import httpx
    from app.google.token_manager import get_valid_token
    access_token = await get_valid_token(user_id, session)
    if not access_token:
        raise ValueError("Google account not connected")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"{DRIVE_API}/files/{file_id}?alt=media",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code >= 400:
        raise ValueError(f"Download failed: {response.text}")
    return response.content


async def delete_file(user_id: int, session, file_id: str) -> dict:
    await google_api_call(user_id, session, "DELETE", f"{DRIVE_API}/files/{file_id}")
    return {"deleted": True, "file_id": file_id}


async def create_folder(user_id: int, session, folder_name: str, parent_id: Optional[str] = None) -> dict:
    metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        metadata["parents"] = [parent_id]
    return await google_api_call(user_id, session, "POST", f"{DRIVE_API}/files", json_data=metadata, params={"fields": "id,name"})


async def share_file(user_id: int, session, file_id: str, email: str, role: str = "reader") -> dict:
    permission = {"type": "user", "role": role, "emailAddress": email}
    return await google_api_call(
        user_id, session, "POST", f"{DRIVE_API}/files/{file_id}/permissions",
        json_data=permission, params={"fields": "id", "sendNotificationEmail": "true"},
    )
