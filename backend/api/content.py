"""API routes for content retrieval."""

from fastapi import APIRouter, HTTPException, Query

from backend.database import get_content_items, get_all_content, get_source, get_view, get_content_for_sources

router = APIRouter(prefix="/api/content", tags=["content"])


@router.get("/")
async def get_feed(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Get all content items across sources, newest first."""
    return await get_all_content(limit=limit, offset=offset)


@router.get("/source/{source_id}")
async def get_source_content(
    source_id: int,
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Get content items for a specific source."""
    source = await get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return await get_content_items(source_id, limit=limit, offset=offset)


@router.get("/view/{view_id}")
async def get_view_content(
    view_id: int,
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Get content items for a named view, filtered by its source_ids and keywords."""
    view = await get_view(view_id)
    if not view:
        raise HTTPException(status_code=404, detail="View not found")

    source_ids = view.get("source_ids", [])
    if not source_ids:
        return []

    items = await get_content_for_sources(source_ids, limit=limit, offset=offset)

    # Apply keyword filters
    topic_filters = view.get("topic_filters", [])
    exclude_keywords = view.get("exclude_keywords", [])

    if topic_filters:
        items = [item for item in items if any(
            kw.lower() in (item.get("title", "") + " " + (item.get("description") or "")).lower()
            for kw in topic_filters
        )]

    if exclude_keywords:
        items = [item for item in items if not any(
            kw.lower() in (item.get("title", "") + " " + (item.get("description") or "")).lower()
            for kw in exclude_keywords
        )]

    return items
