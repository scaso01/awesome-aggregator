"""SQLite database layer with async support."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite

from backend.config import DB_PATH, logger

_db: Optional[aiosqlite.Connection] = None


async def get_db() -> aiosqlite.Connection:
    """Get or create the database connection."""
    global _db
    if _db is None:
        _db = await aiosqlite.connect(str(DB_PATH))
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await _init_tables(_db)
    return _db


async def close_db():
    """Close the database connection."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None


async def _maybe_add_column(db, table, column, col_type, default=None):
    """Add a column to a table if it doesn't already exist."""
    cursor = await db.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in await cursor.fetchall()]
    if column not in columns:
        default_clause = f" DEFAULT {default}" if default is not None else ""
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}")


async def _init_tables(db: aiosqlite.Connection):
    """Create tables if they don't exist."""
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            refresh_seconds INTEGER NOT NULL DEFAULT 300,
            display_format TEXT NOT NULL DEFAULT 'compact',
            category TEXT NOT NULL DEFAULT 'General',
            status TEXT NOT NULL DEFAULT 'active',
            last_fetched TEXT,
            last_error TEXT,
            item_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS content_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            description TEXT,
            image_url TEXT,
            author TEXT,
            published_at TEXT,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
            metadata TEXT DEFAULT '{}',
            FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE,
            UNIQUE(source_id, url)
        );

        CREATE TABLE IF NOT EXISTS layouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            panels TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            source_ids TEXT NOT NULL DEFAULT '[]',
            layout_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (layout_id) REFERENCES layouts(id)
        );

        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_item_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            image_url TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(content_item_id)
        );

        CREATE TABLE IF NOT EXISTS hidden_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_item_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(content_item_id)
        );

        CREATE TABLE IF NOT EXISTS muted_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            mute_until TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(source_id)
        );

        CREATE TABLE IF NOT EXISTS reading_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_item_id INTEGER,
            source_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_content_source ON content_items(source_id);
        CREATE INDEX IF NOT EXISTS idx_content_published ON content_items(published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_content_fetched ON content_items(fetched_at DESC);
    """)

    # Migrate views table with new columns
    await _maybe_add_column(db, "views", "sort_order", "INTEGER", 0)
    await _maybe_add_column(db, "views", "topic_filters", "TEXT", "'[]'")
    await _maybe_add_column(db, "views", "exclude_keywords", "TEXT", "'[]'")
    await _maybe_add_column(db, "views", "icon", "TEXT", "NULL")

    await db.commit()
    logger.info("Database tables initialized")


# --- Source CRUD ---


async def create_source(name: str, source_type: str, url: str,
                        refresh_seconds: int = 300, display_format: str = "compact",
                        category: str = "General") -> dict:
    """Create a new content source."""
    db = await get_db()
    now = datetime.utcnow().isoformat()
    cursor = await db.execute(
        """INSERT INTO sources (name, source_type, url, refresh_seconds,
           display_format, category, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, source_type, url, refresh_seconds, display_format, category, now, now)
    )
    await db.commit()
    return await get_source(cursor.lastrowid)


async def create_sources_batch(sources: list[dict]) -> list[dict]:
    """Batch create sources. Uses INSERT OR IGNORE to skip duplicate URLs.
    Returns only successfully created rows."""
    if not sources:
        return []

    db = await get_db()
    now = datetime.utcnow().isoformat()
    created = []

    for src in sources:
        try:
            cursor = await db.execute(
                """INSERT OR IGNORE INTO sources
                   (name, source_type, url, refresh_seconds, display_format, category, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (src["name"], src["source_type"], src["url"],
                 src.get("refresh_seconds", 300),
                 src.get("display_format", "compact"),
                 src.get("category", "General"), now, now)
            )
            if cursor.rowcount > 0:
                row = await get_source(cursor.lastrowid)
                if row:
                    created.append(row)
        except Exception as e:
            logger.warning(f"Batch insert failed for '{src.get('name', '?')}': {e}")

    await db.commit()
    return created


async def get_source(source_id: int) -> Optional[dict]:
    """Get a source by ID."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM sources WHERE id = ?", (source_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_all_sources() -> list[dict]:
    """Get all sources."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM sources ORDER BY category, name")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_active_sources() -> list[dict]:
    """Get all active sources."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM sources WHERE status = 'active' ORDER BY category, name"
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def update_source(source_id: int, **kwargs) -> Optional[dict]:
    """Update a source. Only provided fields are updated."""
    if not kwargs:
        return await get_source(source_id)

    kwargs["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [source_id]

    db = await get_db()
    await db.execute(f"UPDATE sources SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return await get_source(source_id)


async def delete_source(source_id: int) -> bool:
    """Delete a source and its content items."""
    db = await get_db()
    cursor = await db.execute("DELETE FROM sources WHERE id = ?", (source_id,))
    await db.commit()
    return cursor.rowcount > 0


# --- Content Item CRUD ---


async def upsert_content_items(source_id: int, items: list[dict]) -> int:
    """Insert or update content items. Returns count of new items."""
    if not items:
        return 0

    db = await get_db()
    new_count = 0
    for item in items:
        try:
            await db.execute(
                """INSERT INTO content_items
                   (source_id, title, url, description, image_url, author,
                    published_at, fetched_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source_id, url) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    image_url=excluded.image_url,
                    fetched_at=excluded.fetched_at,
                    metadata=excluded.metadata""",
                (
                    source_id, item["title"], item["url"],
                    item.get("description"), item.get("image_url"),
                    item.get("author"), item.get("published_at"),
                    item.get("fetched_at", datetime.utcnow().isoformat()),
                    json.dumps(item.get("metadata", {}))
                )
            )
            new_count += 1
        except Exception as e:
            logger.warning(f"Failed to upsert item '{item.get('title', '?')}': {e}")

    await db.commit()

    # Update source item count
    cursor = await db.execute(
        "SELECT COUNT(*) FROM content_items WHERE source_id = ?", (source_id,)
    )
    row = await cursor.fetchone()
    count = row[0] if row else 0
    await update_source(source_id, item_count=count,
                        last_fetched=datetime.utcnow().isoformat())
    return new_count


async def get_content_items(source_id: int, limit: int = 50,
                            offset: int = 0) -> list[dict]:
    """Get content items for a source, newest first. Excludes hidden/muted."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT ci.* FROM content_items ci
           LEFT JOIN hidden_items hi ON ci.id = hi.content_item_id
           LEFT JOIN muted_sources ms ON ci.source_id = ms.source_id
               AND (ms.mute_until IS NULL OR ms.mute_until > datetime('now'))
           WHERE ci.source_id = ? AND hi.id IS NULL AND ms.id IS NULL
           ORDER BY ci.published_at DESC, ci.fetched_at DESC
           LIMIT ? OFFSET ?""",
        (source_id, limit, offset)
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        if d.get("metadata"):
            try:
                d["metadata"] = json.loads(d["metadata"])
            except (json.JSONDecodeError, TypeError):
                d["metadata"] = {}
        result.append(d)
    return result


async def get_all_content(limit: int = 100, offset: int = 0) -> list[dict]:
    """Get all content items across sources, newest first. Excludes hidden/muted."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT ci.*, s.name as source_name, s.source_type
           FROM content_items ci
           JOIN sources s ON ci.source_id = s.id
           LEFT JOIN hidden_items hi ON ci.id = hi.content_item_id
           LEFT JOIN muted_sources ms ON ci.source_id = ms.source_id
               AND (ms.mute_until IS NULL OR ms.mute_until > datetime('now'))
           WHERE hi.id IS NULL AND ms.id IS NULL
           ORDER BY ci.published_at DESC, ci.fetched_at DESC
           LIMIT ? OFFSET ?""",
        (limit, offset)
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        if d.get("metadata"):
            try:
                d["metadata"] = json.loads(d["metadata"])
            except (json.JSONDecodeError, TypeError):
                d["metadata"] = {}
        result.append(d)
    return result


# --- Layout CRUD ---


async def save_layout(name: str, panels: list[dict]) -> dict:
    """Save or update a layout."""
    db = await get_db()
    now = datetime.utcnow().isoformat()
    panels_json = json.dumps(panels)

    await db.execute(
        """INSERT INTO layouts (name, panels, created_at, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(name) DO UPDATE SET
            panels=excluded.panels, updated_at=excluded.updated_at""",
        (name, panels_json, now, now)
    )
    await db.commit()
    return await get_layout(name)


async def get_layout(name: str) -> Optional[dict]:
    """Get a layout by name."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM layouts WHERE name = ?", (name,))
    row = await cursor.fetchone()
    if row:
        d = dict(row)
        d["panels"] = json.loads(d["panels"])
        return d
    return None


# --- View CRUD ---


async def create_view(name: str, description: str = None,
                      source_ids: list[int] = None,
                      topic_filters: list[str] = None,
                      exclude_keywords: list[str] = None,
                      icon: str = None,
                      sort_order: int = 0) -> dict:
    """Create a named view."""
    db = await get_db()
    now = datetime.utcnow().isoformat()
    ids_json = json.dumps(source_ids or [])
    topic_json = json.dumps(topic_filters or [])
    exclude_json = json.dumps(exclude_keywords or [])

    cursor = await db.execute(
        """INSERT INTO views (name, description, source_ids, topic_filters,
           exclude_keywords, icon, sort_order, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, description, ids_json, topic_json, exclude_json,
         icon, sort_order, now, now)
    )
    await db.commit()
    return await get_view(cursor.lastrowid)


async def get_view(view_id: int) -> Optional[dict]:
    """Get a view by ID."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM views WHERE id = ?", (view_id,))
    row = await cursor.fetchone()
    if row:
        d = dict(row)
        d["source_ids"] = json.loads(d["source_ids"])
        d["topic_filters"] = json.loads(d.get("topic_filters") or "[]")
        d["exclude_keywords"] = json.loads(d.get("exclude_keywords") or "[]")
        return d
    return None


async def get_all_views() -> list[dict]:
    """Get all views, ordered by sort_order then name."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM views ORDER BY sort_order, name")
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["source_ids"] = json.loads(d["source_ids"])
        d["topic_filters"] = json.loads(d.get("topic_filters") or "[]")
        d["exclude_keywords"] = json.loads(d.get("exclude_keywords") or "[]")
        result.append(d)
    return result


async def update_view(view_id: int, **kwargs) -> Optional[dict]:
    """Update a view. Only provided fields are updated."""
    if not kwargs:
        return await get_view(view_id)

    # Serialize list fields to JSON
    for key in ("source_ids", "topic_filters", "exclude_keywords"):
        if key in kwargs and isinstance(kwargs[key], list):
            kwargs[key] = json.dumps(kwargs[key])

    kwargs["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [view_id]

    db = await get_db()
    await db.execute(f"UPDATE views SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return await get_view(view_id)


async def delete_view(view_id: int) -> bool:
    """Delete a view by ID."""
    db = await get_db()
    cursor = await db.execute("DELETE FROM views WHERE id = ?", (view_id,))
    await db.commit()
    return cursor.rowcount > 0


async def reorder_views(view_ids: list[int]) -> None:
    """Reorder views by updating sort_order based on position in list."""
    db = await get_db()
    for idx, vid in enumerate(view_ids):
        await db.execute(
            "UPDATE views SET sort_order = ? WHERE id = ?", (idx, vid)
        )
    await db.commit()


# --- Content for Sources ---


async def get_content_for_sources(source_ids: list[int], limit: int = 50,
                                  offset: int = 0) -> list[dict]:
    """Get content items for multiple sources. Excludes hidden/muted."""
    if not source_ids:
        return []

    db = await get_db()
    placeholders = ",".join("?" for _ in source_ids)
    cursor = await db.execute(
        f"""SELECT ci.*, s.name as source_name, s.source_type
            FROM content_items ci
            JOIN sources s ON ci.source_id = s.id
            LEFT JOIN hidden_items hi ON ci.id = hi.content_item_id
            LEFT JOIN muted_sources ms ON ci.source_id = ms.source_id
                AND (ms.mute_until IS NULL OR ms.mute_until > datetime('now'))
            WHERE ci.source_id IN ({placeholders})
                AND hi.id IS NULL AND ms.id IS NULL
            ORDER BY ci.published_at DESC, ci.fetched_at DESC
            LIMIT ? OFFSET ?""",
        (*source_ids, limit, offset)
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        if d.get("metadata"):
            try:
                d["metadata"] = json.loads(d["metadata"])
            except (json.JSONDecodeError, TypeError):
                d["metadata"] = {}
        result.append(d)
    return result


# --- Bookmark CRUD ---


async def create_bookmark(content_item_id: int, source_id: int, title: str,
                          url: str, image_url: str = None,
                          notes: str = None) -> dict:
    """Create a bookmark for a content item, or return the existing one.

    content_item_id is UNIQUE. A plain INSERT therefore raised
    sqlite3.IntegrityError the second time anyone bookmarked the same article,
    which surfaced as a 500. Bookmarking something already bookmarked is a
    perfectly ordinary thing for a user to do, and the same item can appear in
    two panels at once, so this is idempotent instead.
    """
    db = await get_db()
    now = datetime.utcnow().isoformat()
    await db.execute(
        """INSERT INTO bookmarks (content_item_id, source_id, title, url,
           image_url, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(content_item_id) DO NOTHING""",
        (content_item_id, source_id, title, url, image_url, notes, now)
    )
    await db.commit()

    cursor = await db.execute(
        "SELECT * FROM bookmarks WHERE content_item_id = ?", (content_item_id,)
    )
    row = await cursor.fetchone()
    return dict(row)


async def get_bookmarks(limit: int = 50, offset: int = 0) -> list[dict]:
    """Get all bookmarks, newest first."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT * FROM bookmarks ORDER BY created_at DESC
           LIMIT ? OFFSET ?""",
        (limit, offset)
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def delete_bookmark(bookmark_id: int) -> bool:
    """Delete a bookmark by ID."""
    db = await get_db()
    cursor = await db.execute(
        "DELETE FROM bookmarks WHERE id = ?", (bookmark_id,)
    )
    await db.commit()
    return cursor.rowcount > 0


# --- Hide / Mute Actions ---


async def hide_item(content_item_id: int) -> None:
    """Hide a content item from feeds."""
    db = await get_db()
    await db.execute(
        "INSERT OR IGNORE INTO hidden_items (content_item_id) VALUES (?)",
        (content_item_id,)
    )
    await db.commit()


async def get_hidden_ids() -> set[int]:
    """Get the set of hidden content item IDs."""
    db = await get_db()
    cursor = await db.execute("SELECT content_item_id FROM hidden_items")
    rows = await cursor.fetchall()
    return {row[0] for row in rows}


async def mute_source(source_id: int, mute_until: str = None) -> dict:
    """Mute a source. If mute_until is None, mute permanently."""
    db = await get_db()
    now = datetime.utcnow().isoformat()
    await db.execute(
        """INSERT OR REPLACE INTO muted_sources (source_id, mute_until, created_at)
           VALUES (?, ?, ?)""",
        (source_id, mute_until, now)
    )
    await db.commit()
    return {"source_id": source_id, "mute_until": mute_until, "created_at": now}


async def unmute_source(source_id: int) -> bool:
    """Unmute a source."""
    db = await get_db()
    cursor = await db.execute(
        "DELETE FROM muted_sources WHERE source_id = ?", (source_id,)
    )
    await db.commit()
    return cursor.rowcount > 0


async def get_muted_sources() -> list[dict]:
    """Get all currently muted sources with source info."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT ms.*, s.name as source_name, s.source_type
           FROM muted_sources ms
           JOIN sources s ON ms.source_id = s.id
           ORDER BY ms.created_at DESC"""
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def cleanup_expired_mutes() -> int:
    """Delete muted_sources entries whose mute_until has passed. Returns count."""
    db = await get_db()
    cursor = await db.execute(
        "DELETE FROM muted_sources WHERE mute_until IS NOT NULL AND mute_until < datetime('now')"
    )
    await db.commit()
    return cursor.rowcount


# --- Reading Stats ---


async def record_reading_event(content_item_id: int, source_id: int,
                               event_type: str) -> None:
    """Record a reading event (click, read, bookmark)."""
    db = await get_db()
    await db.execute(
        """INSERT INTO reading_events (content_item_id, source_id, event_type)
           VALUES (?, ?, ?)""",
        (content_item_id, source_id, event_type)
    )
    await db.commit()


async def get_reading_stats_summary() -> dict:
    """Get a summary of reading activity."""
    db = await get_db()

    # Today count
    cursor = await db.execute(
        "SELECT COUNT(*) FROM reading_events WHERE created_at >= date('now')"
    )
    today_count = (await cursor.fetchone())[0]

    # Week count
    cursor = await db.execute(
        "SELECT COUNT(*) FROM reading_events WHERE created_at >= date('now', '-7 days')"
    )
    week_count = (await cursor.fetchone())[0]

    # Top 5 sources
    cursor = await db.execute(
        """SELECT s.name, COUNT(*) as cnt
           FROM reading_events re
           JOIN sources s ON re.source_id = s.id
           GROUP BY re.source_id
           ORDER BY cnt DESC LIMIT 5"""
    )
    top_sources = [{"name": row[0], "count": row[1]} for row in await cursor.fetchall()]

    # Category breakdown
    cursor = await db.execute(
        """SELECT s.category, COUNT(*) as cnt
           FROM reading_events re
           JOIN sources s ON re.source_id = s.id
           GROUP BY s.category
           ORDER BY cnt DESC"""
    )
    category_breakdown = {row[0]: row[1] for row in await cursor.fetchall()}

    return {
        "today_count": today_count,
        "week_count": week_count,
        "top_sources": top_sources,
        "category_breakdown": category_breakdown,
    }
