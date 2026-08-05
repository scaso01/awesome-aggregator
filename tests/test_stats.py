"""Tests for reading statistics.

Tests use the database layer directly for recording events
and the API endpoints where available.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def _create_source_for_stats(client, name, url):
    """Helper to create a source for stats testing."""
    resp = await client.post("/api/sources/", json={
        "name": name, "source_type": "rss", "url": url,
        "refresh_seconds": 300, "display_format": "compact",
    })
    return resp.json()


async def test_record_reading_event_via_db(db):
    """Recording a reading event should insert a row into reading_events."""
    from backend.database import record_reading_event
    await record_reading_event(content_item_id=1, source_id=1, event_type="click")
    cursor = await db.execute("SELECT COUNT(*) FROM reading_events")
    count = (await cursor.fetchone())[0]
    assert count == 1


async def test_record_multiple_event_types(db):
    """Different event types should all be recorded."""
    from backend.database import record_reading_event
    await record_reading_event(content_item_id=1, source_id=1, event_type="click")
    await record_reading_event(content_item_id=2, source_id=1, event_type="read")
    await record_reading_event(content_item_id=3, source_id=1, event_type="bookmark")
    cursor = await db.execute("SELECT COUNT(*) FROM reading_events")
    count = (await cursor.fetchone())[0]
    assert count == 3


async def test_summary_empty(db):
    """Summary with no events should return zero counts."""
    from backend.database import get_reading_stats_summary
    summary = await get_reading_stats_summary()
    assert summary["today_count"] == 0
    assert summary["week_count"] == 0
    assert summary["top_sources"] == []
    assert summary["category_breakdown"] == {}


async def test_summary_today_count(db):
    """Summary should count events from today."""
    from backend.database import record_reading_event, get_reading_stats_summary, create_source
    # Create a real source so the JOIN works
    await create_source(name="Stats Source", source_type="rss",
                        url="https://stats.example.com/feed")
    # Get its ID
    cursor = await db.execute("SELECT id FROM sources LIMIT 1")
    source_id = (await cursor.fetchone())[0]

    await record_reading_event(content_item_id=1, source_id=source_id, event_type="click")
    await record_reading_event(content_item_id=2, source_id=source_id, event_type="click")
    summary = await get_reading_stats_summary()
    assert summary["today_count"] >= 2


async def test_summary_week_count(db):
    """Summary week_count should include all events from the past 7 days."""
    from backend.database import record_reading_event, get_reading_stats_summary, create_source
    await create_source(name="Week Source", source_type="rss",
                        url="https://week.example.com/feed")
    cursor = await db.execute("SELECT id FROM sources LIMIT 1")
    source_id = (await cursor.fetchone())[0]

    for i in range(5):
        await record_reading_event(content_item_id=i, source_id=source_id, event_type="click")
    summary = await get_reading_stats_summary()
    assert summary["week_count"] >= 5


async def test_summary_top_sources(db):
    """Summary should rank sources by event count."""
    from backend.database import record_reading_event, get_reading_stats_summary, create_source
    src1 = await create_source(name="Popular", source_type="rss",
                               url="https://popular.example.com/feed")
    src2 = await create_source(name="Less Popular", source_type="rss",
                               url="https://less.example.com/feed")

    # More events for source 1
    for i in range(10):
        await record_reading_event(content_item_id=i + 100, source_id=src1["id"], event_type="click")
    for i in range(3):
        await record_reading_event(content_item_id=i + 200, source_id=src2["id"], event_type="click")

    summary = await get_reading_stats_summary()
    assert len(summary["top_sources"]) >= 2
    assert summary["top_sources"][0]["name"] == "Popular"
    assert summary["top_sources"][0]["count"] == 10


async def test_summary_category_breakdown(db):
    """Summary should break down events by source category."""
    from backend.database import record_reading_event, get_reading_stats_summary, create_source
    await create_source(name="News Feed", source_type="rss",
                        url="https://news.example.com/feed", category="News")
    await create_source(name="Tech Feed", source_type="rss",
                        url="https://tech.example.com/feed", category="Tech")

    cursor = await db.execute("SELECT id, category FROM sources ORDER BY id")
    rows = await cursor.fetchall()
    news_id = rows[0][0]
    tech_id = rows[1][0]

    for i in range(4):
        await record_reading_event(content_item_id=i + 300, source_id=news_id, event_type="click")
    for i in range(2):
        await record_reading_event(content_item_id=i + 400, source_id=tech_id, event_type="read")

    summary = await get_reading_stats_summary()
    assert "News" in summary["category_breakdown"]
    assert "Tech" in summary["category_breakdown"]
    assert summary["category_breakdown"]["News"] == 4
    assert summary["category_breakdown"]["Tech"] == 2
