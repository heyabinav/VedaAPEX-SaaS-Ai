"""Google Docs API service."""

import logging
from typing import Any, Optional

from app.google.credentials import google_api_call
from app.google.scopes import DOCS_API

logger = logging.getLogger("google.docs")


async def create_document(user_id: int, session, title: str) -> dict:
    return await google_api_call(
        user_id, session, "POST", f"{DOCS_API}/documents",
        json_data={"title": title},
    )


async def read_document(user_id, session, document_id: str) -> dict:
    return await google_api_call(
        user_id, session, "GET", f"{DOCS_API}/documents/{document_id}",
    )


async def append_text(user_id: int, session, document_id: str, text: str) -> dict:
    end_of_body = {"index": -1}
    requests_body = [{"insertText": {"location": end_of_body, "text": text}}]
    return await google_api_call(
        user_id, session, "POST", f"{DOCS_API}/documents/{document_id}:batchUpdate",
        json_data={"requests": requests_body},
    )


async def replace_text(user_id: int, session, document_id: str, find_text: str, replace_text: str) -> dict:
    requests_body = [
        {
            "replaceAllText": {
                "containsText": {"text": find_text, "matchCase": True},
                "replaceText": replace_text,
            }
        }
    ]
    return await google_api_call(
        user_id, session, "POST", f"{DOCS_API}/documents/{document_id}:batchUpdate",
        json_data={"requests": requests_body},
    )
