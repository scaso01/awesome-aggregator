"""API routes for dashboard layout management."""

from fastapi import APIRouter, HTTPException

from backend.database import save_layout, get_layout
from backend.models import LayoutSave

router = APIRouter(prefix="/api/layouts", tags=["layouts"])


@router.get("/{name}")
async def get_layout_detail(name: str):
    """Get a saved layout by name."""
    layout = await get_layout(name)
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    return layout


@router.put("/{name}")
async def save_layout_detail(name: str, data: LayoutSave):
    """Save or update a dashboard layout."""
    panels = [p.model_dump() for p in data.panels]
    return await save_layout(name, panels)
