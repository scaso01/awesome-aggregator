"""Pydantic data models for Awesome Aggregator."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    RSS = "rss"
    YOUTUBE = "youtube"
    REDDIT = "reddit"
    GENERIC = "generic"


class DisplayFormat(str, Enum):
    COMPACT = "compact"        # Thumbnail left, title + meta right (default)
    MAGAZINE = "magazine"      # Large image on top, text below
    HEADLINES = "headlines"    # Title only, no images, ultra-dense
    CARDS = "cards"            # Card per item with image + description
    GALLERY = "gallery"        # Image grid, minimal text overlay
    TEXT_ONLY = "text_only"    # Full text, no images at all


class SourceStatus(str, Enum):
    ACTIVE = "active"
    ERROR = "error"
    PAUSED = "paused"


# --- Request/Response Models ---


class SourceCreate(BaseModel):
    """Request model for creating a new source."""
    name: str = Field(..., min_length=1, max_length=200)
    source_type: SourceType
    url: str
    refresh_seconds: int = Field(default=300, ge=30, le=86400)
    display_format: DisplayFormat = DisplayFormat.COMPACT
    category: str = Field(default="General", max_length=100)


class SourceBatchCreate(BaseModel):
    """Request model for batch creating sources."""
    sources: list[SourceCreate] = Field(..., min_length=1, max_length=50)


class SourceUpdate(BaseModel):
    """Request model for updating a source."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    refresh_seconds: Optional[int] = Field(None, ge=30, le=86400)
    display_format: Optional[DisplayFormat] = None
    category: Optional[str] = Field(None, max_length=100)
    status: Optional[SourceStatus] = None


class SourceResponse(BaseModel):
    """Response model for a source."""
    id: int
    name: str
    source_type: SourceType
    url: str
    refresh_seconds: int
    display_format: DisplayFormat
    category: str
    status: SourceStatus
    last_fetched: Optional[datetime] = None
    last_error: Optional[str] = None
    item_count: int = 0
    created_at: datetime
    updated_at: datetime


class ContentItem(BaseModel):
    """A single piece of content from a source."""
    id: Optional[int] = None
    source_id: int
    title: str
    url: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LayoutPanel(BaseModel):
    """A panel in the dashboard grid layout."""
    source_id: int
    x: int = 0
    y: int = 0
    w: int = 4  # Width in grid units
    h: int = 3  # Height in grid units
    display_format: Optional[DisplayFormat] = None


class LayoutSave(BaseModel):
    """Request model for saving a layout."""
    name: str = Field(default="default", max_length=100)
    panels: list[LayoutPanel]


class LayoutResponse(BaseModel):
    """Response model for a layout."""
    id: int
    name: str
    panels: list[LayoutPanel]
    created_at: datetime
    updated_at: datetime


class ViewCreate(BaseModel):
    """Request model for creating a named view."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    source_ids: list[int] = Field(default_factory=list)
    layout: Optional[LayoutSave] = None
    topic_filters: Optional[list[str]] = None
    exclude_keywords: Optional[list[str]] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None


class ViewResponse(BaseModel):
    """Response model for a named view."""
    id: int
    name: str
    description: Optional[str]
    source_ids: list[int]
    layout: Optional[LayoutResponse] = None
    topic_filters: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    icon: Optional[str] = None
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime


class WebSocketMessage(BaseModel):
    """Message sent over WebSocket."""
    type: str  # "new_content", "source_update", "source_error"
    source_id: int
    data: dict[str, Any] = Field(default_factory=dict)


# --- View Management Models ---


class ViewUpdate(BaseModel):
    """Request model for updating a view."""
    name: Optional[str] = None
    description: Optional[str] = None
    source_ids: Optional[list[int]] = None
    topic_filters: Optional[list[str]] = None
    exclude_keywords: Optional[list[str]] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None


class ViewReorder(BaseModel):
    """Request model for reordering views."""
    view_ids: list[int]


# --- Bookmark Models ---


class BookmarkCreate(BaseModel):
    """Request model for creating a bookmark."""
    content_item_id: int
    source_id: int
    title: str
    url: str
    image_url: Optional[str] = None
    notes: Optional[str] = None


class BookmarkResponse(BaseModel):
    """Response model for a bookmark."""
    id: int
    content_item_id: int
    source_id: int
    title: str
    url: str
    image_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


# --- Hide / Mute Models ---


class HideRequest(BaseModel):
    """Request model for hiding a content item."""
    content_item_id: int


class MuteRequest(BaseModel):
    """Request model for muting a source."""
    source_id: int
    duration: Optional[str] = None  # "24h", "1w", "1m", None=permanent


class MuteResponse(BaseModel):
    """Response model for a muted source."""
    id: int
    source_id: int
    mute_until: Optional[datetime] = None
    created_at: datetime


# --- Reading Stats Models ---


class ReadingEventCreate(BaseModel):
    """Request model for recording a reading event."""
    content_item_id: Optional[int] = None
    source_id: int
    event_type: str  # "click", "read", "bookmark"


# --- Reader / Detection Models ---


class ReaderExtractResponse(BaseModel):
    """Response model for article reader extraction."""
    title: str
    author: Optional[str] = None
    date: Optional[str] = None
    site_name: Optional[str] = None
    hero_image: Optional[str] = None
    content_html: str
    word_count: int
    estimated_read_minutes: int


class DetectRequest(BaseModel):
    """Request model for auto-detecting a source."""
    url: str


class DetectResponse(BaseModel):
    """Response model for auto-detected source."""
    source_type: str
    name: str
    url: str
    preview_items: list[dict] = []


# --- Digest / OPML Models ---


class DigestItem(BaseModel):
    """A single item in a digest ranking."""
    rank: int
    content_item: dict
    score: float


class OPMLImportResponse(BaseModel):
    """Response model for OPML import results."""
    imported: int
    skipped: int
    errors: list[str] = []
