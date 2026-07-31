"""Google People API service."""

import logging
from typing import Any, Optional

from app.google.credentials import google_api_call
from app.google.scopes import PEOPLE_API

logger = logging.getLogger("google.people")


async def list_contacts(user_id: int, session, page_size: int = 20) -> dict:
    return await google_api_call(
        user_id, session, "GET", f"{PEOPLE_API}/connections/people/me",
        params={"pageSize": min(page_size, 100), "personFields": "names,emailAddresses,phoneNumbers"},
    )


async def search_contacts(user_id: int, session, query: str) -> dict:
    return await google_api_call(
        user_id, session, "GET", f"{PEOPLE_API}/connections/people/me/search",
        params={"query": query, "personFields": "names,emailAddresses,phoneNumbers"},
    )


async def get_contact(user_id: int, session, resource_name: str) -> dict:
    return await google_api_call(
        user_id, session, "GET", f"{PEOPLE_API}/{resource_name}",
        params={"personFields": "names,emailAddresses,phoneNumbers,organizations,addresses"},
    )
