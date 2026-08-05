"""API routes for content source management."""

from fastapi import APIRouter, HTTPException

from backend.database import (
    create_source, create_sources_batch, get_source, get_all_sources,
    update_source, delete_source
)
from backend.models import SourceCreate, SourceBatchCreate, SourceUpdate, SourceResponse
from backend.scheduler import schedule_source, unschedule_source

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("/", response_model=list[dict])
async def list_sources():
    """Get all configured content sources."""
    return await get_all_sources()


@router.get("/{source_id}")
async def get_source_detail(source_id: int):
    """Get a specific source by ID."""
    source = await get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/", status_code=201)
async def add_source(data: SourceCreate):
    """Add a new content source."""
    source = await create_source(
        name=data.name,
        source_type=data.source_type.value,
        url=data.url,
        refresh_seconds=data.refresh_seconds,
        display_format=data.display_format.value,
        category=data.category,
    )

    # Schedule the new source for periodic refresh
    schedule_source(
        source_id=source["id"],
        source_type=source["source_type"],
        url=source["url"],
        name=source["name"],
        interval_seconds=source["refresh_seconds"],
    )

    return source


@router.post("/batch", status_code=201)
async def add_sources_batch(data: SourceBatchCreate):
    """Batch add multiple content sources at once."""
    source_dicts = [
        {
            "name": s.name,
            "source_type": s.source_type.value,
            "url": s.url,
            "refresh_seconds": s.refresh_seconds,
            "display_format": s.display_format.value,
            "category": s.category,
        }
        for s in data.sources
    ]

    created = await create_sources_batch(source_dicts)

    # Schedule each newly created source
    for source in created:
        schedule_source(
            source_id=source["id"],
            source_type=source["source_type"],
            url=source["url"],
            name=source["name"],
            interval_seconds=source["refresh_seconds"],
        )

    skipped = len(data.sources) - len(created)
    return {"created": created, "count": len(created), "skipped": skipped}


@router.patch("/{source_id}")
async def update_source_detail(source_id: int, data: SourceUpdate):
    """Update a source's configuration."""
    existing = await get_source(source_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Source not found")

    updates = data.model_dump(exclude_none=True)
    if "display_format" in updates:
        updates["display_format"] = updates["display_format"].value
    if "status" in updates:
        updates["status"] = updates["status"].value

    source = await update_source(source_id, **updates)

    # Reschedule if refresh interval changed or status changed
    if source["status"] == "active":
        schedule_source(
            source_id=source["id"],
            source_type=source["source_type"],
            url=source["url"],
            name=source["name"],
            interval_seconds=source["refresh_seconds"],
        )
    else:
        unschedule_source(source_id)

    return source


@router.delete("/{source_id}", status_code=204)
async def remove_source(source_id: int):
    """Delete a content source and all its content."""
    unschedule_source(source_id)
    deleted = await delete_source(source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Source not found")
