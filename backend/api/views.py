"""API routes for named view management."""

from fastapi import APIRouter, HTTPException

from backend.database import create_view, get_view, get_all_views, update_view, delete_view, reorder_views
from backend.models import ViewCreate, ViewUpdate, ViewReorder

router = APIRouter(prefix="/api/views", tags=["views"])


@router.get("/")
async def list_views():
    """Get all named views."""
    return await get_all_views()


@router.get("/{view_id}")
async def get_view_detail(view_id: int):
    """Get a specific view by ID."""
    view = await get_view(view_id)
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    return view


@router.post("/", status_code=201)
async def add_view(data: ViewCreate):
    """Create a new named view."""
    return await create_view(
        name=data.name,
        description=data.description,
        source_ids=data.source_ids,
        topic_filters=data.topic_filters,
        exclude_keywords=data.exclude_keywords,
        icon=data.icon,
        sort_order=data.sort_order or 0,
    )


@router.patch("/{view_id}")
async def update_view_endpoint(view_id: int, data: ViewUpdate):
    """Update a view's configuration."""
    view = await get_view(view_id)
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    updates = data.model_dump(exclude_unset=True)
    return await update_view(view_id, **updates)


@router.delete("/{view_id}")
async def delete_view_endpoint(view_id: int):
    """Delete a named view."""
    if not await delete_view(view_id):
        raise HTTPException(status_code=404, detail="View not found")
    return {"status": "deleted"}


@router.put("/reorder")
async def reorder_views_endpoint(data: ViewReorder):
    """Reorder views by providing the desired order of view IDs."""
    await reorder_views(data.view_ids)
    return {"status": "ok"}
