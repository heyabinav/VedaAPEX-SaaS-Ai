"""MCP tools for Google Workspace services."""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.google.token_manager import get_valid_token

logger = logging.getLogger("mcp.google_tools")
router = APIRouter(prefix="/api/v1/mcp/google", tags=["Google MCP Tools"])


def _require_google(user: User, session: Session):
    import asyncio
    token = asyncio.get_event_loop().run_until_complete(get_valid_token(user.id, session))
    if not token:
        raise HTTPException(status_code=400, detail="Google account not connected. Please connect first.")
    return token


class GmailSearchRequest(BaseModel):
    query: str = Field(..., description="Gmail search query")
    max_results: int = Field(default=10, ge=1, le=50)


class GmailReadRequest(BaseModel):
    message_id: str = Field(..., description="Gmail message ID")


class GmailSendRequest(BaseModel):
    to: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body text")


class DriveSearchRequest(BaseModel):
    query: str = Field(default="", description="Drive search query")
    max_results: int = Field(default=10, ge=1, le=100)


class DriveShareRequest(BaseModel):
    file_id: str = Field(..., description="Drive file ID")
    email: str = Field(..., description="Email to share with")
    role: str = Field(default="reader", description="Permission role: reader, writer, owner")


class DriveCreateFolderRequest(BaseModel):
    folder_name: str = Field(..., description="Folder name")
    parent_id: Optional[str] = Field(default=None, description="Parent folder ID")


class DocsCreateRequest(BaseModel):
    title: str = Field(..., description="Document title")


class DocsReadRequest(BaseModel):
    document_id: str = Field(..., description="Google Doc ID")


class DocsAppendRequest(BaseModel):
    document_id: str = Field(..., description="Google Doc ID")
    text: str = Field(..., description="Text to append")


class DocsReplaceRequest(BaseModel):
    document_id: str = Field(..., description="Google Doc ID")
    find_text: str = Field(..., description="Text to find")
    replace_text: str = Field(..., description="Text to replace with")


class SheetsCreateRequest(BaseModel):
    title: str = Field(..., description="Spreadsheet title")


class SheetsReadRequest(BaseModel):
    spreadsheet_id: str = Field(..., description="Spreadsheet ID")
    range_name: str = Field(default="Sheet1", description="Cell range")


class SheetsAppendRequest(BaseModel):
    spreadsheet_id: str = Field(..., description="Spreadsheet ID")
    values: list[list[Any]] = Field(..., description="2D array of values")
    range_name: str = Field(default="Sheet1", description="Cell range")


class SheetsUpdateRequest(BaseModel):
    spreadsheet_id: str = Field(..., description="Spreadsheet ID")
    range_name: str = Field(..., description="Cell range (e.g., A1:C3)")
    values: list[list[Any]] = Field(..., description="2D array of values")


class SheetsClearRequest(BaseModel):
    spreadsheet_id: str = Field(..., description="Spreadsheet ID")
    range_name: str = Field(default="Sheet1", description="Cell range")


class SlidesCreateRequest(BaseModel):
    title: str = Field(..., description="Presentation title")


class CalendarListRequest(BaseModel):
    calendar_id: str = Field(default="primary", description="Calendar ID")
    max_results: int = Field(default=10, ge=1, le=250)
    time_min: Optional[str] = Field(default=None, description="Start time (ISO 8601)")


class CalendarCreateRequest(BaseModel):
    summary: str = Field(..., description="Event title")
    start_time: str = Field(..., description="Start time (ISO 8601)")
    end_time: str = Field(..., description="End time (ISO 8601)")
    description: str = Field(default="", description="Event description")
    calendar_id: str = Field(default="primary", description="Calendar ID")
    timezone: str = Field(default="UTC", description="Timezone")


class CalendarUpdateRequest(BaseModel):
    event_id: str = Field(..., description="Event ID")
    summary: Optional[str] = Field(default=None, description="New event title")
    start_time: Optional[str] = Field(default=None, description="New start time")
    end_time: Optional[str] = Field(default=None, description="New end time")
    description: Optional[str] = Field(default=None, description="New description")
    calendar_id: str = Field(default="primary")


class CalendarDeleteRequest(BaseModel):
    event_id: str = Field(..., description="Event ID")
    calendar_id: str = Field(default="primary")


class ContactsSearchRequest(BaseModel):
    query: str = Field(default="", description="Search query")
    page_size: int = Field(default=20, ge=1, le=100)


class ContactGetRequest(BaseModel):
    resource_name: str = Field(..., description="Contact resource name")


# ────────────────────────────────────────────────────────────
# Gmail Tools
# ────────────────────────────────────────────────────────────

@router.post("/gmail/search", operation_id="gmail_search_emails")
async def mcp_gmail_search(
    body: GmailSearchRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.gmail import search_emails
    return await search_emails(user.id, session, body.query, body.max_results)


@router.post("/gmail/read", operation_id="gmail_read_email")
async def mcp_gmail_read(
    body: GmailReadRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.gmail import read_email
    return await read_email(user.id, session, body.message_id)


@router.post("/gmail/send", operation_id="gmail_send_email")
async def mcp_gmail_send(
    body: GmailSendRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.gmail import send_email
    return await send_email(user.id, session, body.to, body.subject, body.body)


@router.post("/gmail/labels", operation_id="gmail_list_labels")
async def mcp_gmail_labels(
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.gmail import list_labels
    return await list_labels(user.id, session)


# ────────────────────────────────────────────────────────────
# Drive Tools
# ────────────────────────────────────────────────────────────

@router.post("/drive/search", operation_id="drive_search_files")
async def mcp_drive_search(
    body: DriveSearchRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.drive import search_files
    return await search_files(user.id, session, body.query, body.max_results)


@router.post("/drive/share", operation_id="drive_share_file")
async def mcp_drive_share(
    body: DriveShareRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.drive import share_file
    return await share_file(user.id, session, body.file_id, body.email, body.role)


@router.post("/drive/create-folder", operation_id="drive_create_folder")
async def mcp_drive_create_folder(
    body: DriveCreateFolderRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.drive import create_folder
    return await create_folder(user.id, session, body.folder_name, body.parent_id)


@router.post("/drive/delete", operation_id="drive_delete_file")
async def mcp_drive_delete(
    body: dict,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.drive import delete_file
    return await delete_file(user.id, session, body.get("file_id", ""))


# ────────────────────────────────────────────────────────────
# Docs Tools
# ────────────────────────────────────────────────────────────

@router.post("/docs/create", operation_id="docs_create_document")
async def mcp_docs_create(
    body: DocsCreateRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.docs import create_document
    return await create_document(user.id, session, body.title)


@router.post("/docs/read", operation_id="docs_read_document")
async def mcp_docs_read(
    body: DocsReadRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.docs import read_document
    return await read_document(user.id, session, body.document_id)


@router.post("/docs/append", operation_id="docs_append_text")
async def mcp_docs_append(
    body: DocsAppendRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.docs import append_text
    return await append_text(user.id, session, body.document_id, body.text)


@router.post("/docs/replace", operation_id="docs_replace_text")
async def mcp_docs_replace(
    body: DocsReplaceRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.docs import replace_text
    return await replace_text(user.id, session, body.document_id, body.find_text, body.replace_text)


# ────────────────────────────────────────────────────────────
# Sheets Tools
# ────────────────────────────────────────────────────────────

@router.post("/sheets/create", operation_id="sheets_create_sheet")
async def mcp_sheets_create(
    body: SheetsCreateRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.sheets import create_sheet
    return await create_sheet(user.id, session, body.title)


@router.post("/sheets/read", operation_id="sheets_read_sheet")
async def mcp_sheets_read(
    body: SheetsReadRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.sheets import read_sheet
    return await read_sheet(user.id, session, body.spreadsheet_id, body.range_name)


@router.post("/sheets/append", operation_id="sheets_append_rows")
async def mcp_sheets_append(
    body: SheetsAppendRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.sheets import append_rows
    return await append_rows(user.id, session, body.spreadsheet_id, body.values, body.range_name)


@router.post("/sheets/update", operation_id="sheets_update_cells")
async def mcp_sheets_update(
    body: SheetsUpdateRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.sheets import update_cells
    return await update_cells(user.id, session, body.spreadsheet_id, body.range_name, body.values)


@router.post("/sheets/clear", operation_id="sheets_clear_sheet")
async def mcp_sheets_clear(
    body: SheetsClearRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.sheets import clear_sheet
    return await clear_sheet(user.id, session, body.spreadsheet_id, body.range_name)


# ────────────────────────────────────────────────────────────
# Slides Tools
# ────────────────────────────────────────────────────────────

@router.post("/slides/create", operation_id="slides_create_presentation")
async def mcp_slides_create(
    body: SlidesCreateRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.slides import create_presentation
    return await create_presentation(user.id, session, body.title)


@router.post("/slides/insert-text", operation_id="slides_insert_text")
async def mcp_slides_insert_text(
    body: dict,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.slides import insert_text
    return await insert_text(user.id, session, body["presentation_id"], body["page_object_id"], body["text"])


@router.post("/slides/add-slide", operation_id="slides_add_slide")
async def mcp_slides_add_slide(
    body: dict,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.slides import add_slide
    return await add_slide(user.id, session, body["presentation_id"], body.get("layout_id"))


@router.post("/slides/export-pdf", operation_id="slides_export_pdf")
async def mcp_slides_export_pdf(
    body: dict,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.slides import export_pdf
    pdf_bytes = await export_pdf(user.id, session, body["presentation_id"])
    import base64
    return {"pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8"), "size_bytes": len(pdf_bytes)}


# ────────────────────────────────────────────────────────────
# Calendar Tools
# ────────────────────────────────────────────────────────────

@router.post("/calendar/list", operation_id="calendar_list_events")
async def mcp_calendar_list(
    body: CalendarListRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.calendar import list_events
    return await list_events(user.id, session, body.calendar_id, body.max_results, body.time_min)


@router.post("/calendar/create", operation_id="calendar_create_event")
async def mcp_calendar_create(
    body: CalendarCreateRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.calendar import create_event
    return await create_event(user.id, session, body.summary, body.start_time, body.end_time, body.description, body.calendar_id, body.timezone)


@router.post("/calendar/update", operation_id="calendar_update_event")
async def mcp_calendar_update(
    body: CalendarUpdateRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.calendar import update_event
    return await update_event(user.id, session, body.event_id, body.summary, body.start_time, body.end_time, body.description, body.calendar_id)


@router.post("/calendar/delete", operation_id="calendar_delete_event")
async def mcp_calendar_delete(
    body: CalendarDeleteRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.calendar import delete_event
    return await delete_event(user.id, session, body.event_id, body.calendar_id)


# ────────────────────────────────────────────────────────────
# People API Tools
# ────────────────────────────────────────────────────────────

@router.post("/people/list", operation_id="people_list_contacts")
async def mcp_people_list(
    body: dict = {},
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.people import list_contacts
    return await list_contacts(user.id, session, body.get("page_size", 20))


@router.post("/people/search", operation_id="people_search_contacts")
async def mcp_people_search(
    body: ContactsSearchRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.people import search_contacts
    return await search_contacts(user.id, session, body.query)


@router.post("/people/get", operation_id="people_get_contact")
async def mcp_people_get(
    body: ContactGetRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    _require_google(user, session)
    from app.google.people import get_contact
    return await get_contact(user.id, session, body.resource_name)
