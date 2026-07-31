"""MCP tools for all connectors - Google, GitHub, Notion, Figma, Canva."""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.connectors.token_manager import get_valid_access_token
from app.connectors.registry import connector_registry

logger = logging.getLogger("mcp.connector_tools")
router = APIRouter(prefix="/api/v1/mcp/connectors", tags=["Connector MCP Tools"])


def _get_connector(provider: str):
    conn = connector_registry.get(provider)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Unknown connector: {provider}")
    return conn


async def _require_token(user: User, provider: str, session: Session) -> str:
    token = await get_valid_access_token(user.id, provider, session)
    if not token:
        raise HTTPException(status_code=400, detail=f"{provider.title()} not connected. Please connect first via /connectors/{provider}/login")
    return token


async def _api_get(connector, token: str, url: str, params: dict = None) -> dict:
    return await connector._get(url, token, params=params)


# ────────────────────────────────────────────────────────────
# Google MCP Tools
# ────────────────────────────────────────────────────────────

class GmailSearchRequest(BaseModel):
    query: str = Field(..., description="Gmail search query")
    max_results: int = Field(default=10, ge=1, le=50)

class GmailSendRequest(BaseModel):
    to: str = Field(..., description="Recipient email")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body")

class DriveSearchRequest(BaseModel):
    query: str = Field(default="", description="Drive search query")
    max_results: int = Field(default=10, ge=1, le=100)

class DocsRequest(BaseModel):
    document_id: str = Field(..., description="Google Doc ID")

class DocsAppendRequest(BaseModel):
    document_id: str = Field(..., description="Google Doc ID")
    text: str = Field(..., description="Text to append")

class SheetsReadRequest(BaseModel):
    spreadsheet_id: str = Field(..., description="Spreadsheet ID")
    range_name: str = Field(default="Sheet1", description="Cell range")

class SheetsAppendRequest(BaseModel):
    spreadsheet_id: str = Field(..., description="Spreadsheet ID")
    values: list[list[Any]] = Field(..., description="2D array of values")

class CalendarListRequest(BaseModel):
    max_results: int = Field(default=10, ge=1, le=250)
    time_min: Optional[str] = Field(default=None, description="Start time ISO 8601")

class CalendarCreateRequest(BaseModel):
    summary: str = Field(..., description="Event title")
    start_time: str = Field(..., description="Start time ISO 8601")
    end_time: str = Field(..., description="End time ISO 8601")
    description: str = Field(default="")
    timezone: str = Field(default="UTC")


@router.post("/google/gmail/search", operation_id="connector_gmail_search")
async def mcp_gmail_search(body: GmailSearchRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("google")
    token = await _require_token(user, "google", session)
    return await _api_get(conn, token, "https://gmail.googleapis.com/gmail/v1/users/me/messages", {"q": body.query, "maxResults": body.max_results})


@router.post("/google/gmail/read", operation_id="connector_gmail_read")
async def mcp_gmail_read(body: dict, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("google")
    token = await _require_token(user, "google", session)
    return await _api_get(conn, token, f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{body['message_id']}", {"format": "full"})


@router.post("/google/gmail/send", operation_id="connector_gmail_send")
async def mcp_gmail_send(body: GmailSendRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    import base64
    conn = _get_connector("google")
    token = await _require_token(user, "google", session)
    msg = f"To: {body.to}\nSubject: {body.subject}\nMIME-Version: 1.0\nContent-Type: text/plain; charset=utf-8\n\n{body.body}"
    raw = base64.urlsafe_b64encode(msg.encode()).decode()
    return await conn._get("https://gmail.googleapis.com/gmail/v1/users/me/messages/send", token)


@router.post("/google/gmail/labels", operation_id="connector_gmail_labels")
async def mcp_gmail_labels(user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("google")
    token = await _require_token(user, "google", session)
    return await _api_get(conn, token, "https://gmail.googleapis.com/gmail/v1/users/me/labels")


@router.post("/google/drive/search", operation_id="connector_drive_search")
async def mcp_drive_search(body: DriveSearchRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("google")
    token = await _require_token(user, "google", session)
    return await _api_get(conn, token, "https://www.googleapis.com/drive/v3/files", {"q": body.query, "pageSize": body.max_results})


@router.post("/google/docs/read", operation_id="connector_docs_read")
async def mcp_docs_read(body: DocsRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("google")
    token = await _require_token(user, "google", session)
    return await _api_get(conn, token, f"https://docs.googleapis.com/v1/documents/{body.document_id}")


@router.post("/google/docs/append", operation_id="connector_docs_append")
async def mcp_docs_append(body: DocsAppendRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("google")
    token = await _require_token(user, "google", session)
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://docs.googleapis.com/v1/documents/{body.document_id}:batchUpdate",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"requests": [{"insertText": {"location": {"index": -1}, "text": body.text}}]},
        )
    return resp.json()


@router.post("/google/sheets/read", operation_id="connector_sheets_read")
async def mcp_sheets_read(body: SheetsReadRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("google")
    token = await _require_token(user, "google", session)
    return await _api_get(conn, token, f"https://sheets.googleapis.com/v4/spreadsheets/{body.spreadsheet_id}/values/{body.range_name}")


@router.post("/google/sheets/append", operation_id="connector_sheets_append")
async def mcp_sheets_append(body: SheetsAppendRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("google")
    token = await _require_token(user, "google", session)
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{body.spreadsheet_id}/values/Sheet1:append",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"values": body.values, "majorDimension": "ROWS"},
            params={"valueInputOption": "USER_ENTERED"},
        )
    return resp.json()


@router.post("/google/calendar/list", operation_id="connector_calendar_list")
async def mcp_calendar_list(body: CalendarListRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("google")
    token = await _require_token(user, "google", session)
    params = {"maxResults": body.max_results, "singleEvents": True, "orderBy": "startTime"}
    if body.time_min:
        params["timeMin"] = body.time_min
    return await _api_get(conn, token, "https://www.googleapis.com/calendar/v3/calendars/primary/events", params)


@router.post("/google/calendar/create", operation_id="connector_calendar_create")
async def mcp_calendar_create(body: CalendarCreateRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("google")
    token = await _require_token(user, "google", session)
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"summary": body.summary, "description": body.description, "start": {"dateTime": body.start_time, "timeZone": body.timezone}, "end": {"dateTime": body.end_time, "timeZone": body.timezone}},
        )
    return resp.json()


# ────────────────────────────────────────────────────────────
# GitHub MCP Tools
# ────────────────────────────────────────────────────────────

class GitHubRepoRequest(BaseModel):
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")

class GitHubIssuesRequest(BaseModel):
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    state: str = Field(default="open", description="open, closed, or all")
    per_page: int = Field(default=30, ge=1, le=100)


@router.post("/github/repos", operation_id="connector_github_list_repos")
async def mcp_github_repos(user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("github")
    token = await _require_token(user, "github", session)
    return await _api_get(conn, token, "https://api.github.com/user/repos", {"per_page": 30, "sort": "updated"})


@router.post("/github/repo", operation_id="connector_github_get_repo")
async def mcp_github_repo(body: GitHubRepoRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("github")
    token = await _require_token(user, "github", session)
    return await _api_get(conn, token, f"https://api.github.com/repos/{body.owner}/{body.repo}")


@router.post("/github/commits", operation_id="connector_github_list_commits")
async def mcp_github_commits(body: GitHubRepoRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("github")
    token = await _require_token(user, "github", session)
    return await _api_get(conn, token, f"https://api.github.com/repos/{body.owner}/{body.repo}/commits", {"per_page": 20})


@router.post("/github/branches", operation_id="connector_github_list_branches")
async def mcp_github_branches(body: GitHubRepoRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("github")
    token = await _require_token(user, "github", session)
    return await _api_get(conn, token, f"https://api.github.com/repos/{body.owner}/{body.repo}/branches")


@router.post("/github/issues", operation_id="connector_github_list_issues")
async def mcp_github_issues(body: GitHubIssuesRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("github")
    token = await _require_token(user, "github", session)
    return await _api_get(conn, token, f"https://api.github.com/repos/{body.owner}/{body.repo}/issues", {"state": body.state, "per_page": body.per_page})


@router.post("/github/pull-requests", operation_id="connector_github_list_prs")
async def mcp_github_prs(body: GitHubRepoRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("github")
    token = await _require_token(user, "github", session)
    return await _api_get(conn, token, f"https://api.github.com/repos/{body.owner}/{body.repo}/pulls", {"state": "all", "per_page": 20})


@router.post("/github/releases", operation_id="connector_github_list_releases")
async def mcp_github_releases(body: GitHubRepoRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("github")
    token = await _require_token(user, "github", session)
    return await _api_get(conn, token, f"https://api.github.com/repos/{body.owner}/{body.repo}/releases", {"per_page": 10})


# ────────────────────────────────────────────────────────────
# Notion MCP Tools
# ────────────────────────────────────────────────────────────

class NotionSearchRequest(BaseModel):
    query: str = Field(default="", description="Search query")
    page_size: int = Field(default=20, ge=1, le=100)

class NotionPageRequest(BaseModel):
    page_id: str = Field(..., description="Notion page ID")

class NotionCreatePageRequest(BaseModel):
    parent_id: str = Field(..., description="Parent page or database ID")
    title: str = Field(..., description="Page title")
    content: str = Field(default="", description="Page content")


@router.post("/notion/search", operation_id="connector_notion_search")
async def mcp_notion_search(body: NotionSearchRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("notion")
    token = await _require_token(user, "notion", session)
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.notion.com/v1/search",
            headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"},
            json={"query": body.query, "page_size": body.page_size},
        )
    return resp.json()


@router.post("/notion/read", operation_id="connector_notion_read_page")
async def mcp_notion_read(body: NotionPageRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("notion")
    token = await _require_token(user, "notion", session)
    return await _api_get(conn, token, f"https://api.notion.com/v1/pages/{body.page_id}")


@router.post("/notion/blocks", operation_id="connector_notion_read_blocks")
async def mcp_notion_blocks(body: NotionPageRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("notion")
    token = await _require_token(user, "notion", session)
    return await _api_get(conn, token, f"https://api.notion.com/v1/blocks/{body.page_id}/children")


@router.post("/notion/databases", operation_id="connector_notion_list_databases")
async def mcp_notion_databases(body: NotionSearchRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("notion")
    token = await _require_token(user, "notion", session)
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.notion.com/v1/search",
            headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"},
            json={"filter": {"property": "object", "value": "database"}, "page_size": body.page_size},
        )
    return resp.json()


# ────────────────────────────────────────────────────────────
# Figma MCP Tools
# ────────────────────────────────────────────────────────────

class FigmaFileRequest(BaseModel):
    file_key: str = Field(..., description="Figma file key")


@router.post("/figma/files", operation_id="connector_figma_list_files")
async def mcp_figma_files(user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("figma")
    token = await _require_token(user, "figma", session)
    return await _api_get(conn, token, "https://api.figma.com/v1/me")


@router.post("/figma/file", operation_id="connector_figma_get_file")
async def mcp_figma_file(body: FigmaFileRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("figma")
    token = await _require_token(user, "figma", session)
    return await _api_get(conn, token, f"https://api.figma.com/v1/files/{body.file_key}", {"depth": 2})


@router.post("/figma/comments", operation_id="connector_figma_comments")
async def mcp_figma_comments(body: FigmaFileRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("figma")
    token = await _require_token(user, "figma", session)
    return await _api_get(conn, token, f"https://api.figma.com/v1/files/{body.file_key}/comments")


@router.post("/figma/components", operation_id="connector_figma_components")
async def mcp_figma_components(body: FigmaFileRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("figma")
    token = await _require_token(user, "figma", session)
    return await _api_get(conn, token, f"https://api.figma.com/v1/files/{body.file_key}/components")


@router.post("/figma/styles", operation_id="connector_figma_styles")
async def mcp_figma_styles(body: FigmaFileRequest, user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("figma")
    token = await _require_token(user, "figma", session)
    return await _api_get(conn, token, f"https://api.figma.com/v1/files/{body.file_key}/styles")


# ────────────────────────────────────────────────────────────
# Canva MCP Tools
# ────────────────────────────────────────────────────────────

@router.post("/canva/designs", operation_id="connector_canva_list_designs")
async def mcp_canva_designs(user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("canva")
    token = await _require_token(user, "canva", session)
    return await _api_get(conn, token, "https://api.canva.com/rest/v1/designs")


@router.post("/canva/folders", operation_id="connector_canva_folders")
async def mcp_canva_folders(user: User = Depends(get_current_user_auth), session: Session = Depends(get_session)):
    conn = _get_connector("canva")
    token = await _require_token(user, "canva", session)
    return await _api_get(conn, token, "https://api.canva.com/rest/v1/folders")
