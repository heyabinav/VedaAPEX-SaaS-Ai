"""Google Calendar API service."""

import logging
from typing import Any, Optional

from app.google.credentials import google_api_call
from app.google.scopes import CALENDAR_API

logger = logging.getLogger("google.calendar")


async def list_events(user_id: int, session, calendar_id: str = "primary", max_results: int = 10, time_min: Optional[str] = None) -> dict:
    params = {"maxResults": min(max_results, 250), "singleEvents": True, "orderBy": "startTime"}
    if time_min:
        params["timeMin"] = time_min
    return await google_api_call(
        user_id, session, "GET", f"{CALENDAR_API}/calendars/{calendar_id}/events", params=params,
    )


async def create_event(user_id: int, session, summary: str, start_time: str, end_time: str, description: str = "", calendar_id: str = "primary", timezone: str = "UTC") -> dict:
    event_body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time, "timeZone": timezone},
        "end": {"dateTime": end_time, "timeZone": timezone},
    }
    return await google_api_call(
        user_id, session, "POST", f"{CALENDAR_API}/calendars/{calendar_id}/events",
        json_data=event_body,
    )


async def update_event(user_id: int, session, event_id: str, summary: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None, description: Optional[str] = None, calendar_id: str = "primary") -> dict:
    event_body = {}
    if summary:
        event_body["summary"] = summary
    if description is not None:
        event_body["description"] = description
    if start_time:
        event_body["start"] = {"dateTime": start_time}
    if end_time:
        event_body["end"] = {"dateTime": end_time}
    return await google_api_call(
        user_id, session, "PUT", f"{CALENDAR_API}/calendars/{calendar_id}/events/{event_id}",
        json_data=event_body,
    )


async def delete_event(user_id: int, session, event_id: str, calendar_id: str = "primary") -> dict:
    await google_api_call(user_id, session, "DELETE", f"{CALENDAR_API}/calendars/{calendar_id}/events/{event_id}")
    return {"deleted": True, "event_id": event_id}
