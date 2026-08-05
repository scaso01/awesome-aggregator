"""Tests for content actions API (hide, mute)."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_hide_item(client):
    """Hiding an item should return a hidden status."""
    resp = await client.post("/api/actions/hide", json={"content_item_id": 1})
    assert resp.status_code == 200
    assert resp.json()["status"] == "hidden"


async def test_hide_duplicate_idempotent(client):
    """Hiding the same item twice should not error (idempotent)."""
    await client.post("/api/actions/hide", json={"content_item_id": 1})
    resp = await client.post("/api/actions/hide", json={"content_item_id": 1})
    assert resp.status_code == 200
    assert resp.json()["status"] == "hidden"


async def test_mute_source_permanent(client):
    """Muting a source without duration should set mute_until to null."""
    resp = await client.post("/api/actions/mute", json={"source_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "muted"
    assert data["mute_until"] is None


async def test_mute_source_24h(client):
    """Muting with 24h duration should set a future mute_until timestamp."""
    resp = await client.post("/api/actions/mute", json={
        "source_id": 2, "duration": "24h",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "muted"
    assert data["mute_until"] is not None


async def test_mute_source_1w(client):
    """Muting with 1w duration should set a mute_until timestamp."""
    resp = await client.post("/api/actions/mute", json={
        "source_id": 3, "duration": "1w",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "muted"
    assert data["mute_until"] is not None


async def test_mute_source_1m(client):
    """Muting with 1m duration should set a mute_until timestamp."""
    resp = await client.post("/api/actions/mute", json={
        "source_id": 4, "duration": "1m",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "muted"
    assert data["mute_until"] is not None


async def test_mute_source_invalid_duration(client):
    """Muting with an unknown duration should act as permanent (no mute_until)."""
    resp = await client.post("/api/actions/mute", json={
        "source_id": 5, "duration": "99z",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["mute_until"] is None


async def test_unmute_source(client):
    """Unmuting a previously muted source should succeed."""
    await client.post("/api/actions/mute", json={"source_id": 1})
    resp = await client.delete("/api/actions/mute/1")
    assert resp.status_code == 200
    assert resp.json()["status"] == "unmuted"


async def test_unmute_nonexistent(client):
    """Unmuting a source that is not muted should return 404."""
    resp = await client.delete("/api/actions/mute/9999")
    assert resp.status_code == 404


async def test_list_muted_sources_empty(client):
    """Listing muted sources when none are muted should return empty list."""
    resp = await client.get("/api/actions/muted")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_muted_sources(client):
    """Listing muted sources should include all currently muted sources."""
    # First create real sources so the JOIN in get_muted_sources works
    await client.post("/api/sources/", json={
        "name": "Muted Source 1", "source_type": "rss",
        "url": "https://muted1.com/feed", "refresh_seconds": 300,
        "display_format": "compact",
    })
    await client.post("/api/sources/", json={
        "name": "Muted Source 2", "source_type": "rss",
        "url": "https://muted2.com/feed", "refresh_seconds": 300,
        "display_format": "compact",
    })

    # Get the actual source IDs
    sources_resp = await client.get("/api/sources/")
    sources = sources_resp.json()
    sid1 = sources[0]["id"]
    sid2 = sources[1]["id"]

    await client.post("/api/actions/mute", json={"source_id": sid1})
    await client.post("/api/actions/mute", json={"source_id": sid2, "duration": "24h"})
    resp = await client.get("/api/actions/muted")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
