"""API routes for bookmark management."""

from fastapi import APIRouter, HTTPException

from backend.database import create_bookmark, get_bookmarks, delete_bookmark
from backend.models import BookmarkCreate

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


@router.get("/")
async def list_bookmarks(limit: int = 50, offset: int = 0):
    """Get all bookmarks, newest first."""
    return await get_bookmarks(limit=limit, offset=offset)


@router.post("/", status_code=201)
async def add_bookmark(data: BookmarkCreate):
    """Bookmark a content item."""
    return await create_bookmark(
        content_item_id=data.content_item_id,
        source_id=data.source_id,
        title=data.title,
        url=data.url,
        image_url=data.image_url,
        notes=data.notes,
    )


@router.delete("/{bookmark_id}")
async def remove_bookmark(bookmark_id: int):
    """Remove a bookmark."""
    if not await delete_bookmark(bookmark_id):
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"status": "deleted"}
