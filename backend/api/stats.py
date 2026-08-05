"""API routes for reading statistics."""

from fastapi import APIRouter

from backend.database import record_reading_event, get_reading_stats_summary
from backend.models import ReadingEventCreate

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.post("/event")
async def record_event(data: ReadingEventCreate):
    """Record a reading event (click, read, bookmark)."""
    await record_reading_event(
        content_item_id=data.content_item_id,
        source_id=data.source_id,
        event_type=data.event_type,
    )
    return {"status": "recorded"}


@router.get("/summary")
async def get_summary():
    """Get reading activity summary (today/week counts, top sources, categories)."""
    return await get_reading_stats_summary()
