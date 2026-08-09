"""Search history endpoints."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.search_history import SearchHistory
from app.models.search_history_result import SearchHistoryResult
from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.schemas.search_history import (
    DeepSearchRequest,
    DeepSearchResponse,
    SearchHistoryCreate,
    SearchHistoryItem,
    SearchHistoryListResponse,
    SearchHistoryResponse,
    SearchHistoryResultsResponse,
    SearchTitleGenerateRequest,
    SearchTitleGenerateResponse,
)
from app.services.deep_search_service import DeepSearchService

logger = logging.getLogger("app.routers.search_history")

router = APIRouter(prefix="/search", tags=["Search History"])

_STOP_WORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "search",
    "the",
    "to",
    "with",
    "best",
    "top",
    "new",
    "latest",
}


def _clean_title(value: str) -> str:
    title = re.sub(r"\s+", " ", value).strip()
    if not title:
        return "Untitled Search"
    return title[:120].strip()


def _generate_title_from_query(query: str, source: str | None = None, results: list[dict[str, Any]] | None = None) -> str:
    if results:
        for item in results:
            if isinstance(item, dict):
                candidate = str(item.get("title") or item.get("name") or item.get("label") or "").strip()
                if candidate:
                    return _clean_title(candidate)

    tokens = re.findall(r"[A-Za-z0-9]+", query or "")
    meaningful = [token for token in tokens if token.lower() not in _STOP_WORDS]
    chosen = meaningful[:5] if meaningful else tokens[:5]

    if not chosen and source:
        chosen = re.findall(r"[A-Za-z0-9]+", source)[:4]

    if not chosen:
        return "Untitled Search"

    return _clean_title(" ".join(chosen).title())


def _serialize_results(results: list[dict[str, Any]]) -> str:
    return json.dumps(results, ensure_ascii=False, default=str)


def _deserialize_results(blob: str) -> list[dict[str, Any]]:
    raw = json.loads(blob)
    return raw if isinstance(raw, list) else []


def _to_item(entry: SearchHistory, result_count: int = 0) -> SearchHistoryItem:
    return SearchHistoryItem(
        id=entry.id,
        title=entry.title,
        query=entry.query,
        source=entry.source,
        notes=entry.notes,
        result_count=result_count,
        created_at=entry.created_at,
    )


def _get_result_counts(session: Session, history_ids: list[int]) -> dict[int, int]:
    if not history_ids:
        return {}

    rows = session.exec(
        select(SearchHistoryResult).where(SearchHistoryResult.history_id.in_(history_ids))
    ).all()
    return {row.history_id: row.result_count for row in rows}


@router.post("/history", response_model=SearchHistoryResponse)
async def save_search_history(
    body: SearchHistoryCreate,
    request: Request,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Save a search title/query pair for the current user."""
    try:
        entry = SearchHistory(
            user_id=user.id,
            title=body.title,
            query=body.query,
            source=body.source,
            notes=body.notes,
        )
        session.add(entry)
        session.flush()

        result_count = len(body.results)
        if result_count:
            session.add(
                SearchHistoryResult(
                    history_id=entry.id,
                    result_count=result_count,
                    results_json=_serialize_results(body.results),
                )
            )

        session.commit()
        session.refresh(entry)

        logger.info(
            "Saved search history entry id=%s user_id=%s ip=%s",
            entry.id,
            user.id,
            getattr(request.client, "host", None),
        )

        return {
            "success": True,
            "message": "Search history saved successfully",
            "data": _to_item(entry, result_count=result_count),
        }
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        logger.exception("Failed to save search history for user_id=%s", user.id)
        raise HTTPException(status_code=500, detail="Failed to save search history") from exc


@router.get("/history", response_model=SearchHistoryListResponse)
async def list_search_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """List saved search history for the current user."""
    query = select(SearchHistory).where(SearchHistory.user_id == user.id)
    query = query.order_by(SearchHistory.created_at.desc())

    entries = session.exec(query).all()
    total = len(entries)
    offset = (page - 1) * limit
    page_entries = entries[offset : offset + limit]
    result_counts = _get_result_counts(session, [entry.id for entry in page_entries])

    return {
        "success": True,
        "data": [
            _to_item(entry, result_counts.get(entry.id, 0))
            for entry in page_entries
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": max(1, -(-total // limit)),
        },
    }


@router.get("/history/{history_id}/results", response_model=SearchHistoryResultsResponse)
async def get_search_history_results(
    history_id: int,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Return the stored result payload for a history item."""
    entry = session.get(SearchHistory, history_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Search history not found")

    result_row = session.exec(
        select(SearchHistoryResult).where(SearchHistoryResult.history_id == history_id)
    ).first()
    if not result_row:
        return {
            "success": True,
            "history_id": history_id,
            "title": entry.title,
            "result_count": 0,
            "results": [],
        }

    try:
        results = _deserialize_results(result_row.results_json)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode stored search results for history_id=%s", history_id)
        raise HTTPException(status_code=500, detail="Stored search results are corrupted") from exc

    return {
        "success": True,
        "history_id": history_id,
        "title": entry.title,
        "result_count": result_row.result_count,
        "results": results,
    }


@router.post("/title/generate", response_model=SearchTitleGenerateResponse)
async def generate_search_title(body: SearchTitleGenerateRequest):
    """Generate a short title from a search query or result payload."""
    title = _generate_title_from_query(body.query, body.source, body.results)
    return {
        "success": True,
        "title": title,
        "source": body.source,
    }


@router.post("/deep", response_model=DeepSearchResponse)
async def execute_deep_search(
    body: DeepSearchRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Perform Deep Search intelligence research with query decomposition, multi-source retrieval, and LLM synthesis."""
    try:
        result = await DeepSearchService.deep_search(query=body.query, depth=body.depth or "deep")

        history_id = None
        if body.save_history:
            title = _clean_title(f"Deep Search: {body.query}")
            entry = SearchHistory(
                user_id=user.id,
                title=title,
                query=body.query,
                source="deep_search",
                notes=f"Subqueries: {', '.join(result.get('subqueries', []))}",
            )
            session.add(entry)
            session.flush()

            if result.get("sources"):
                session.add(
                    SearchHistoryResult(
                        history_id=entry.id,
                        result_count=len(result["sources"]),
                        results_json=_serialize_results(result["sources"]),
                    )
                )

            session.commit()
            session.refresh(entry)
            history_id = entry.id

        return {
            "success": True,
            "query": result["query"],
            "subqueries": result["subqueries"],
            "report": result["report"],
            "sources": result["sources"],
            "total_sources_found": result["total_sources_found"],
            "history_id": history_id,
        }
    except Exception as exc:
        session.rollback()
        logger.exception("Deep search failed for query='%s'", body.query)
        raise HTTPException(status_code=500, detail=f"Deep search failed: {str(exc)}") from exc
