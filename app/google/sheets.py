"""Google Sheets API service."""

import logging
from typing import Any, List, Optional

from app.google.credentials import google_api_call
from app.google.scopes import SHEETS_API

logger = logging.getLogger("google.sheets")


async def create_sheet(user_id: int, session, title: str) -> dict:
    return await google_api_call(
        user_id, session, "POST", f"{SHEETS_API}/spreadsheets",
        json_data={"properties": {"title": title}},
    )


async def read_sheet(user_id: int, session, spreadsheet_id: str, range_name: str = "Sheet1") -> dict:
    return await google_api_call(
        user_id, session, "GET", f"{SHEETS_API}/spreadsheets/{spreadsheet_id}/values/{range_name}",
    )


async def append_rows(user_id: int, session, spreadsheet_id: str, values: List[List[Any]], range_name: str = "Sheet1") -> dict:
    return await google_api_call(
        user_id, session, "POST",
        f"{SHEETS_API}/spreadsheets/{spreadsheet_id}/values/{range_name}:append",
        json_data={"values": values, "majorDimension": "ROWS"},
        params={"valueInputOption": "USER_ENTERED"},
    )


async def update_cells(user_id: int, session, spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> dict:
    return await google_api_call(
        user_id, session, "PUT", f"{SHEETS_API}/spreadsheets/{spreadsheet_id}/values",
        json_data={"range": range_name, "values": values, "majorDimension": "ROWS"},
        params={"valueInputOption": "USER_ENTERED"},
    )


async def clear_sheet(user_id: int, session, spreadsheet_id: str, range_name: str = "Sheet1") -> dict:
    return await google_api_call(
        user_id, session, "POST", f"{SHEETS_API}/spreadsheets/{spreadsheet_id}/values/{range_name}:clear",
    )
