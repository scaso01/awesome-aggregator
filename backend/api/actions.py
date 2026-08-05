"""API routes for content actions (hide, mute)."""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from backend.database import hide_item, mute_source, unmute_source, get_muted_sources
from backend.models import HideRequest, MuteRequest

router = APIRouter(prefix="/api/actions", tags=["actions"])

DURATION_MAP = {
    "24h": timedelta(hours=24),
    "1w": timedelta(weeks=1),
    "1m": timedelta(days=30),
}


@router.post("/hide")
async def hide_content_item(data: HideRequest):
    """Hide a content item from all feeds."""
    await hide_item(data.content_item_id)
    return {"status": "hidden"}


@router.post("/mute")
async def mute_content_source(data: MuteRequest):
    """Mute a source for a duration or permanently."""
    mute_until = None
    if data.duration and data.duration in DURATION_MAP:
        mute_until = (datetime.utcnow() + DURATION_MAP[data.duration]).isoformat()
    await mute_source(data.source_id, mute_until=mute_until)
    return {"status": "muted", "mute_until": mute_until}


@router.delete("/mute/{source_id}")
async def unmute_content_source(source_id: int):
    """Unmute a previously muted source."""
    if not await unmute_source(source_id):
        raise HTTPException(status_code=404, detail="Muted source not found")
    return {"status": "unmuted"}


@router.get("/muted")
async def list_muted_sources():
    """Get all currently muted sources."""
    return await get_muted_sources()
