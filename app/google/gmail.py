"""Gmail API service."""

import logging
from typing import Any, Optional

from app.google.credentials import google_api_call
from app.google.scopes import GMAIL_API

logger = logging.getLogger("google.gmail")


async def search_emails(user_id: int, session, query: str = "", max_results: int = 10) -> dict:
    params = {"q": query, "maxResults": min(max_results, 50)}
    return await google_api_call(user_id, session, "GET", f"{GMAIL_API}/users/me/messages", params=params)


async def read_email(user_id: int, session, message_id: str) -> dict:
    return await google_api_call(
        user_id, session, "GET", f"{GMAIL_API}/users/me/messages/{message_id}",
        params={"format": "full"},
    )


async def send_email(user_id: int, session, to: str, subject: str, body: str) -> dict:
    import base64
    message_parts = [
        f"To: {to}",
        f"Subject: {subject}",
        "MIME-Version: 1.0",
        "Content-Type: text/plain; charset=utf-8",
        "",
        body,
    ]
    raw_message = base64.urlsafe_b64encode("\r\n".join(message_parts).encode("utf-8")).decode("utf-8")
    return await google_api_call(
        user_id, session, "POST", f"{GMAIL_API}/users/me/messages/send",
        json_data={"raw": raw_message},
    )


async def list_labels(user_id: int, session) -> dict:
    return await google_api_call(user_id, session, "GET", f"{GMAIL_API}/users/me/labels")
