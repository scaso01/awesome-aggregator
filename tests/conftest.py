"""Shared pytest fixtures for Awesome Aggregator tests."""

import asyncio
import json
import os
from pathlib import Path

import pytest
import pytest_asyncio
import aiosqlite
from httpx import AsyncClient, ASGITransport

# Ensure tests use in-memory database - must be set before importing backend
os.environ["DATABASE_PATH"] = ":memory:"

# Patch DB_PATH before backend modules load it
import backend.config
backend.config.DB_PATH = ":memory:"

from backend.app import app
from backend.database import get_db, close_db


@pytest_asyncio.fixture
async def client():
    """Create a test client with a fresh in-memory database."""
    # Reset the database connection so each test gets a fresh DB
    import backend.database as db_mod
    db_mod._db = None

    # Register bookmarks and actions routers if not already mounted
    from backend.api.bookmarks import router as bookmarks_router
    from backend.api.actions import router as actions_router

    _mounted_prefixes = {r.prefix for r in app.router.routes if hasattr(r, "prefix")}
    if "/api/bookmarks" not in _mounted_prefixes:
        app.include_router(bookmarks_router)
    if "/api/actions" not in _mounted_prefixes:
        app.include_router(actions_router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await close_db()


@pytest_asyncio.fixture
async def db():
    """Get a fresh database connection for direct DB tests."""
    import backend.database as db_mod
    db_mod._db = None
    conn = await get_db()
    yield conn
    await close_db()


@pytest.fixture
def sample_bookmark_data():
    """Sample bookmark creation data."""
    return {
        "content_item_id": 1,
        "source_id": 1,
        "title": "Test Article",
        "url": "https://example.com/article-1",
        "image_url": "https://example.com/img.jpg",
        "notes": "Interesting read",
    }


@pytest.fixture
def sample_rss_feed():
    """Sample RSS feed XML for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>A test feed</description>
    <item>
      <title>Test Article 1</title>
      <link>https://example.com/article-1</link>
      <description>First test article description</description>
      <pubDate>Thu, 12 Feb 2026 10:00:00 GMT</pubDate>
      <author>Test Author</author>
    </item>
    <item>
      <title>Test Article 2</title>
      <link>https://example.com/article-2</link>
      <description>Second test article description</description>
      <pubDate>Thu, 12 Feb 2026 09:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def sample_youtube_feed():
    """Sample YouTube RSS feed XML for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/">
  <title>Test Channel</title>
  <entry>
    <yt:videoId>dQw4w9WgXcQ</yt:videoId>
    <title>Test Video 1</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=dQw4w9WgXcQ"/>
    <author><name>Test Channel</name></author>
    <published>2026-02-12T10:00:00+00:00</published>
    <media:group>
      <media:description>Test video description</media:description>
    </media:group>
  </entry>
</feed>"""


@pytest.fixture
def sample_reddit_response():
    """Sample Reddit JSON response for testing."""
    return {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "Test Reddit Post",
                        "permalink": "/r/test/comments/abc123/test_post/",
                        "selftext": "This is a test post on Reddit.",
                        "author": "testuser",
                        "score": 42,
                        "num_comments": 7,
                        "created_utc": 1739347200,
                        "is_self": True,
                        "stickied": False,
                        "domain": "self.test",
                        "thumbnail": "",
                    }
                },
                {
                    "data": {
                        "title": "Stickied Post (should be skipped)",
                        "permalink": "/r/test/comments/xyz/stickied/",
                        "selftext": "",
                        "author": "mod",
                        "score": 100,
                        "num_comments": 0,
                        "created_utc": 1739347200,
                        "is_self": True,
                        "stickied": True,
                        "domain": "self.test",
                    }
                },
            ]
        }
    }


@pytest.fixture
def sample_source_data():
    """Sample source creation data."""
    return {
        "name": "Test RSS Feed",
        "source_type": "rss",
        "url": "https://example.com/feed.xml",
        "refresh_seconds": 300,
        "display_format": "compact",
        "category": "Testing",
    }
