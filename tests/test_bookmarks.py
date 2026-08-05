"""Tests for bookmarks API endpoints."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_bookmark(client, sample_bookmark_data):
    """Creating a bookmark should return 201 with bookmark data."""
    resp = await client.post("/api/bookmarks/", json=sample_bookmark_data)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == sample_bookmark_data["title"]
    assert data["url"] == sample_bookmark_data["url"]
    assert data["content_item_id"] == sample_bookmark_data["content_item_id"]
    assert "id" in data
    assert "created_at" in data


async def test_list_bookmarks(client, sample_bookmark_data):
    """Listing bookmarks should include previously created bookmarks."""
    await client.post("/api/bookmarks/", json=sample_bookmark_data)
    resp = await client.get("/api/bookmarks/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["title"] == sample_bookmark_data["title"]


async def test_list_empty_bookmarks(client):
    """Listing bookmarks when none exist should return an empty list."""
    resp = await client.get("/api/bookmarks/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_delete_bookmark(client, sample_bookmark_data):
    """Deleting a bookmark should remove it from the list."""
    create_resp = await client.post("/api/bookmarks/", json=sample_bookmark_data)
    bm_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/bookmarks/{bm_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
    # Verify it is gone
    resp = await client.get("/api/bookmarks/")
    assert len(resp.json()) == 0


async def test_delete_nonexistent_bookmark(client):
    """Deleting a nonexistent bookmark should return 404."""
    resp = await client.delete("/api/bookmarks/9999")
    assert resp.status_code == 404


async def test_bookmark_with_notes(client):
    """Bookmark should preserve the notes field."""
    resp = await client.post("/api/bookmarks/", json={
        "content_item_id": 2, "source_id": 1,
        "title": "Noted Article", "url": "https://example.com/2",
        "notes": "Very important",
    })
    assert resp.status_code == 201
    assert resp.json()["notes"] == "Very important"


async def test_bookmark_without_optional_fields(client):
    """Bookmark created without optional fields should have None for them."""
    resp = await client.post("/api/bookmarks/", json={
        "content_item_id": 3, "source_id": 1,
        "title": "Minimal", "url": "https://example.com/3",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["image_url"] is None
    assert data["notes"] is None


async def test_bookmark_with_image_url(client):
    """Bookmark should preserve the image_url field."""
    resp = await client.post("/api/bookmarks/", json={
        "content_item_id": 4, "source_id": 1,
        "title": "Image Article", "url": "https://example.com/4",
        "image_url": "https://example.com/hero.jpg",
    })
    assert resp.status_code == 201
    assert resp.json()["image_url"] == "https://example.com/hero.jpg"


async def test_multiple_bookmarks_ordering(client):
    """Bookmarks should be returned newest first."""
    for i in range(3):
        await client.post("/api/bookmarks/", json={
            "content_item_id": i + 10, "source_id": 1,
            "title": f"Article {i}", "url": f"https://example.com/{i + 10}",
        })
    resp = await client.get("/api/bookmarks/")
    data = resp.json()
    assert len(data) == 3
    # Newest (last created) should be first
    assert data[0]["title"] == "Article 2"
