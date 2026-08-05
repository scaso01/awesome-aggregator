"""Tests for views API endpoints."""

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


async def _create_source(client, name="Test RSS", url="https://example.com/feed.xml"):
    """Helper to create a source for testing."""
    resp = await client.post("/api/sources/", json={
        "name": name, "source_type": "rss", "url": url,
        "refresh_seconds": 300, "display_format": "compact",
    })
    return resp.json()


async def test_create_view(client):
    """Creating a view should return 201 with the view data."""
    resp = await client.post("/api/views/", json={
        "name": "My View", "description": "Test view", "source_ids": [],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My View"
    assert data["description"] == "Test view"
    assert data["source_ids"] == []
    assert "id" in data


async def test_create_view_with_source_ids(client):
    """View should store and return the provided source_ids."""
    resp = await client.post("/api/views/", json={
        "name": "Sourced View", "source_ids": [1, 2, 3],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_ids"] == [1, 2, 3]


async def test_get_all_views(client):
    """Listing views should return all created views."""
    await client.post("/api/views/", json={"name": "View 1", "source_ids": []})
    await client.post("/api/views/", json={"name": "View 2", "source_ids": []})
    resp = await client.get("/api/views/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    names = [v["name"] for v in data]
    assert "View 1" in names
    assert "View 2" in names


async def test_get_single_view(client):
    """Getting a view by ID should return its full details."""
    create_resp = await client.post("/api/views/", json={
        "name": "Detail View", "description": "Has details", "source_ids": [],
    })
    view_id = create_resp.json()["id"]
    resp = await client.get(f"/api/views/{view_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Detail View"
    assert data["description"] == "Has details"


async def test_update_view_name(client):
    """PATCH should update only provided fields."""
    create_resp = await client.post("/api/views/", json={
        "name": "Old Name", "source_ids": [],
    })
    view_id = create_resp.json()["id"]
    resp = await client.patch(f"/api/views/{view_id}", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


async def test_update_view_source_ids(client):
    """PATCH should update source_ids when provided."""
    create_resp = await client.post("/api/views/", json={
        "name": "Update Sources", "source_ids": [],
    })
    view_id = create_resp.json()["id"]
    resp = await client.patch(f"/api/views/{view_id}", json={"source_ids": [5, 10]})
    assert resp.status_code == 200
    assert resp.json()["source_ids"] == [5, 10]


async def test_update_view_keywords(client):
    """PATCH should update topic_filters and exclude_keywords."""
    create_resp = await client.post("/api/views/", json={
        "name": "Filter View", "source_ids": [],
    })
    view_id = create_resp.json()["id"]
    resp = await client.patch(f"/api/views/{view_id}", json={
        "topic_filters": ["python", "rust"],
        "exclude_keywords": ["clickbait"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["topic_filters"] == ["python", "rust"]
    assert data["exclude_keywords"] == ["clickbait"]


async def test_update_view_icon(client):
    """PATCH should update the icon field."""
    create_resp = await client.post("/api/views/", json={
        "name": "Icon View", "source_ids": [],
    })
    view_id = create_resp.json()["id"]
    resp = await client.patch(f"/api/views/{view_id}", json={"icon": "fire"})
    assert resp.status_code == 200
    assert resp.json()["icon"] == "fire"


async def test_delete_view(client):
    """DELETE should remove the view and subsequent GET should 404."""
    create_resp = await client.post("/api/views/", json={
        "name": "Deletable", "source_ids": [],
    })
    view_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/views/{view_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
    # Verify it is gone
    resp = await client.get(f"/api/views/{view_id}")
    assert resp.status_code == 404


async def test_delete_view_not_found(client):
    """DELETE on a nonexistent view should return 404."""
    resp = await client.delete("/api/views/9999")
    assert resp.status_code == 404


async def test_reorder_views(client):
    """PUT /reorder should accept a list of view IDs and return ok."""
    r1 = await client.post("/api/views/", json={"name": "First", "source_ids": []})
    r2 = await client.post("/api/views/", json={"name": "Second", "source_ids": []})
    id1, id2 = r1.json()["id"], r2.json()["id"]
    resp = await client.put("/api/views/reorder", json={"view_ids": [id2, id1]})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_view_not_found(client):
    """GET on a nonexistent view ID should return 404."""
    resp = await client.get("/api/views/9999")
    assert resp.status_code == 404


async def test_view_content_empty_sources(client):
    """View with no source_ids should return an empty content list."""
    create_resp = await client.post("/api/views/", json={
        "name": "Empty View", "source_ids": [],
    })
    view_id = create_resp.json()["id"]
    resp = await client.get(f"/api/content/view/{view_id}")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_view_content_not_found(client):
    """Content endpoint for a nonexistent view should return 404."""
    resp = await client.get("/api/content/view/9999")
    assert resp.status_code == 404
