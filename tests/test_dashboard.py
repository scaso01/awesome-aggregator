"""Functional dashboard regression tests for Awesome Aggregator.

These tests hit the LIVE service over HTTP. They are all marked with
``@pytest.mark.dashboard`` and skipped automatically when the service
is not running on ``http://localhost:8001``.

Run with:
    python -m pytest tests/test_dashboard.py -v -m dashboard
"""

import json
import socket
import time
import xml.etree.ElementTree as ET
from contextlib import closing

import httpx
import pytest

# ---------------------------------------------------------------------------
# Service liveness detection
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8001"


def is_service_running() -> bool:
    """Return True if awesome-aggregator is accepting connections on port 8001."""
    try:
        with closing(socket.create_connection(("localhost", 8001), timeout=2)):
            return True
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False


skip_unless_live = pytest.mark.skipif(
    not is_service_running(),
    reason="awesome-aggregator not running on localhost:8001",
)

pytestmark = [pytest.mark.dashboard, skip_unless_live]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    """Synchronous httpx client pointed at the live service."""
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as c:
        yield c


@pytest.fixture()
def unique_url():
    """Generate a unique URL to avoid UNIQUE constraint collisions between tests."""
    return f"https://example.com/feed-{time.monotonic_ns()}.xml"


@pytest.fixture()
def source_payload(unique_url):
    """Minimal valid source creation payload."""
    return {
        "name": f"Regression Source {time.monotonic_ns()}",
        "source_type": "rss",
        "url": unique_url,
        "refresh_seconds": 300,
        "display_format": "compact",
        "category": "Testing",
    }


@pytest.fixture()
def view_payload():
    """Minimal valid view creation payload."""
    return {
        "name": f"Regression View {time.monotonic_ns()}",
        "description": "Created by regression tests",
        "source_ids": [],
    }


@pytest.fixture()
def bookmark_payload():
    """Minimal valid bookmark creation payload."""
    return {
        "content_item_id": 999999,
        "source_id": 999999,
        "title": f"Bookmark {time.monotonic_ns()}",
        "url": f"https://example.com/bm-{time.monotonic_ns()}",
        "image_url": None,
        "notes": "regression test bookmark",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_source(client: httpx.Client, payload: dict) -> dict:
    """Create a source via API and return the response dict."""
    resp = client.post("/api/sources/", json=payload)
    assert resp.status_code == 201, f"Source creation failed: {resp.text}"
    return resp.json()


def _delete_source(client: httpx.Client, source_id: int) -> None:
    """Delete a source, ignoring 404 (already deleted)."""
    resp = client.delete(f"/api/sources/{source_id}")
    assert resp.status_code in (204, 404)


def _create_view(client: httpx.Client, payload: dict) -> dict:
    """Create a view via API and return the response dict."""
    resp = client.post("/api/views/", json=payload)
    assert resp.status_code == 201, f"View creation failed: {resp.text}"
    return resp.json()


def _delete_view(client: httpx.Client, view_id: int) -> None:
    """Delete a view, ignoring 404."""
    resp = client.delete(f"/api/views/{view_id}")
    assert resp.status_code in (200, 404)


def _create_bookmark(client: httpx.Client, payload: dict) -> dict:
    """Create a bookmark via API and return the response dict."""
    resp = client.post("/api/bookmarks/", json=payload)
    assert resp.status_code == 201, f"Bookmark creation failed: {resp.text}"
    return resp.json()


def _delete_bookmark(client: httpx.Client, bookmark_id: int) -> None:
    """Delete a bookmark, ignoring 404."""
    resp = client.delete(f"/api/bookmarks/{bookmark_id}")
    assert resp.status_code in (200, 404)


# ===================================================================
# POSITIVE TESTS
# ===================================================================


class TestHealthEndpoint:
    """Health check endpoint."""

    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_has_status_ok(self, client):
        data = client.get("/api/health").json()
        assert data["status"] == "ok"

    def test_health_has_websocket_clients_field(self, client):
        data = client.get("/api/health").json()
        assert "websocket_clients" in data
        assert isinstance(data["websocket_clients"], int)


# -------------------------------------------------------------------
# Sources CRUD
# -------------------------------------------------------------------


class TestSourcesCRUD:
    """Source create / read / update / delete."""

    def test_list_sources_returns_list(self, client):
        resp = client.get("/api/sources/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_source(self, client, source_payload):
        source = _create_source(client, source_payload)
        try:
            assert source["name"] == source_payload["name"]
            assert source["source_type"] == "rss"
            assert source["url"] == source_payload["url"]
            assert source["refresh_seconds"] == 300
            assert source["display_format"] == "compact"
            assert source["category"] == "Testing"
            assert "id" in source
            assert "created_at" in source
            assert source["status"] == "active"
        finally:
            _delete_source(client, source["id"])

    def test_get_source_by_id(self, client, source_payload):
        source = _create_source(client, source_payload)
        try:
            resp = client.get(f"/api/sources/{source['id']}")
            assert resp.status_code == 200
            assert resp.json()["id"] == source["id"]
            assert resp.json()["name"] == source_payload["name"]
        finally:
            _delete_source(client, source["id"])

    def test_update_source_name(self, client, source_payload):
        source = _create_source(client, source_payload)
        try:
            resp = client.patch(
                f"/api/sources/{source['id']}",
                json={"name": "Updated Name"},
            )
            assert resp.status_code == 200
            assert resp.json()["name"] == "Updated Name"
        finally:
            _delete_source(client, source["id"])

    def test_update_source_display_format(self, client, source_payload):
        source = _create_source(client, source_payload)
        try:
            resp = client.patch(
                f"/api/sources/{source['id']}",
                json={"display_format": "magazine"},
            )
            assert resp.status_code == 200
            assert resp.json()["display_format"] == "magazine"
        finally:
            _delete_source(client, source["id"])

    def test_update_source_status_to_paused(self, client, source_payload):
        source = _create_source(client, source_payload)
        try:
            resp = client.patch(
                f"/api/sources/{source['id']}",
                json={"status": "paused"},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "paused"
        finally:
            _delete_source(client, source["id"])

    def test_delete_source(self, client, source_payload):
        source = _create_source(client, source_payload)
        resp = client.delete(f"/api/sources/{source['id']}")
        assert resp.status_code == 204
        # Confirm gone
        resp = client.get(f"/api/sources/{source['id']}")
        assert resp.status_code == 404

    def test_batch_create_sources(self, client):
        ts = time.monotonic_ns()
        batch = {
            "sources": [
                {
                    "name": f"Batch A {ts}",
                    "source_type": "rss",
                    "url": f"https://example.com/batch-a-{ts}.xml",
                    "refresh_seconds": 300,
                    "display_format": "compact",
                    "category": "BatchTest",
                },
                {
                    "name": f"Batch B {ts}",
                    "source_type": "rss",
                    "url": f"https://example.com/batch-b-{ts}.xml",
                    "refresh_seconds": 600,
                    "display_format": "headlines",
                    "category": "BatchTest",
                },
            ]
        }
        resp = client.post("/api/sources/batch", json=batch)
        assert resp.status_code == 201
        data = resp.json()
        assert "created" in data
        assert "count" in data
        assert data["count"] == 2
        # Cleanup
        for src in data["created"]:
            _delete_source(client, src["id"])

    def test_batch_create_duplicate_url_skipped(self, client, source_payload):
        source = _create_source(client, source_payload)
        try:
            batch = {"sources": [source_payload]}
            resp = client.post("/api/sources/batch", json=batch)
            assert resp.status_code == 201
            data = resp.json()
            assert data["skipped"] >= 1
        finally:
            _delete_source(client, source["id"])


# -------------------------------------------------------------------
# Content Feed
# -------------------------------------------------------------------


class TestContentFeed:
    """Content retrieval endpoints."""

    def test_get_all_content(self, client):
        resp = client.get("/api/content/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_content_with_limit(self, client):
        resp = client.get("/api/content/", params={"limit": 5, "offset": 0})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_get_content_with_offset(self, client):
        resp = client.get("/api/content/", params={"limit": 10, "offset": 0})
        assert resp.status_code == 200

    def test_get_content_for_source(self, client, source_payload):
        source = _create_source(client, source_payload)
        try:
            resp = client.get(f"/api/content/source/{source['id']}")
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)
        finally:
            _delete_source(client, source["id"])

    def test_content_pagination_params(self, client):
        """limit and offset are respected (does not crash)."""
        resp = client.get("/api/content/", params={"limit": 1, "offset": 999})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# -------------------------------------------------------------------
# Views CRUD
# -------------------------------------------------------------------


class TestViewsCRUD:
    """Named view create / read / update / delete."""

    def test_list_views(self, client):
        resp = client.get("/api/views/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_view(self, client, view_payload):
        view = _create_view(client, view_payload)
        try:
            assert view["name"] == view_payload["name"]
            assert view["description"] == view_payload["description"]
            assert view["source_ids"] == []
            assert "id" in view
        finally:
            _delete_view(client, view["id"])

    def test_get_view_by_id(self, client, view_payload):
        view = _create_view(client, view_payload)
        try:
            resp = client.get(f"/api/views/{view['id']}")
            assert resp.status_code == 200
            assert resp.json()["id"] == view["id"]
        finally:
            _delete_view(client, view["id"])

    def test_update_view_name(self, client, view_payload):
        view = _create_view(client, view_payload)
        try:
            resp = client.patch(
                f"/api/views/{view['id']}",
                json={"name": "Renamed View"},
            )
            assert resp.status_code == 200
            assert resp.json()["name"] == "Renamed View"
        finally:
            _delete_view(client, view["id"])

    def test_update_view_topic_filters(self, client, view_payload):
        view = _create_view(client, view_payload)
        try:
            resp = client.patch(
                f"/api/views/{view['id']}",
                json={"topic_filters": ["python", "rust"]},
            )
            assert resp.status_code == 200
            assert resp.json()["topic_filters"] == ["python", "rust"]
        finally:
            _delete_view(client, view["id"])

    def test_update_view_exclude_keywords(self, client, view_payload):
        view = _create_view(client, view_payload)
        try:
            resp = client.patch(
                f"/api/views/{view['id']}",
                json={"exclude_keywords": ["sponsored", "ad"]},
            )
            assert resp.status_code == 200
            assert resp.json()["exclude_keywords"] == ["sponsored", "ad"]
        finally:
            _delete_view(client, view["id"])

    def test_update_view_icon(self, client, view_payload):
        view = _create_view(client, view_payload)
        try:
            resp = client.patch(
                f"/api/views/{view['id']}",
                json={"icon": "star"},
            )
            assert resp.status_code == 200
            assert resp.json()["icon"] == "star"
        finally:
            _delete_view(client, view["id"])

    def test_delete_view(self, client, view_payload):
        view = _create_view(client, view_payload)
        resp = client.delete(f"/api/views/{view['id']}")
        assert resp.status_code == 200
        # Confirm gone
        resp = client.get(f"/api/views/{view['id']}")
        assert resp.status_code == 404

    def test_reorder_views(self, client):
        v1 = _create_view(client, {
            "name": f"Reorder-A-{time.monotonic_ns()}",
            "source_ids": [],
        })
        v2 = _create_view(client, {
            "name": f"Reorder-B-{time.monotonic_ns()}",
            "source_ids": [],
        })
        try:
            resp = client.put(
                "/api/views/reorder",
                json={"view_ids": [v2["id"], v1["id"]]},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

            # Verify order
            a = client.get(f"/api/views/{v1['id']}").json()
            b = client.get(f"/api/views/{v2['id']}").json()
            assert b["sort_order"] < a["sort_order"]
        finally:
            _delete_view(client, v1["id"])
            _delete_view(client, v2["id"])

    def test_view_content_endpoint(self, client, view_payload):
        view = _create_view(client, view_payload)
        try:
            resp = client.get(f"/api/content/view/{view['id']}")
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)
        finally:
            _delete_view(client, view["id"])


# -------------------------------------------------------------------
# Layouts
# -------------------------------------------------------------------


class TestLayouts:
    """Layout save / load."""

    def test_save_layout(self, client):
        name = f"test-layout-{time.monotonic_ns()}"
        payload = {
            "name": name,
            "panels": [
                {"source_id": 1, "x": 0, "y": 0, "w": 4, "h": 3},
            ],
        }
        resp = client.put(f"/api/layouts/{name}", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == name
        assert isinstance(data["panels"], list)
        assert len(data["panels"]) == 1

    def test_get_layout(self, client):
        name = f"test-layout-get-{time.monotonic_ns()}"
        payload = {
            "name": name,
            "panels": [
                {"source_id": 1, "x": 0, "y": 0, "w": 6, "h": 4},
                {"source_id": 2, "x": 6, "y": 0, "w": 6, "h": 4},
            ],
        }
        client.put(f"/api/layouts/{name}", json=payload)
        resp = client.get(f"/api/layouts/{name}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == name
        assert len(data["panels"]) == 2

    def test_save_layout_overwrites(self, client):
        name = f"test-layout-overwrite-{time.monotonic_ns()}"
        payload1 = {
            "name": name,
            "panels": [{"source_id": 1, "x": 0, "y": 0, "w": 4, "h": 3}],
        }
        payload2 = {
            "name": name,
            "panels": [
                {"source_id": 1, "x": 0, "y": 0, "w": 4, "h": 3},
                {"source_id": 2, "x": 4, "y": 0, "w": 4, "h": 3},
                {"source_id": 3, "x": 8, "y": 0, "w": 4, "h": 3},
            ],
        }
        client.put(f"/api/layouts/{name}", json=payload1)
        client.put(f"/api/layouts/{name}", json=payload2)
        data = client.get(f"/api/layouts/{name}").json()
        assert len(data["panels"]) == 3

    def test_save_empty_panels(self, client):
        name = f"test-layout-empty-{time.monotonic_ns()}"
        payload = {"name": name, "panels": []}
        resp = client.put(f"/api/layouts/{name}", json=payload)
        assert resp.status_code == 200
        assert resp.json()["panels"] == []


# -------------------------------------------------------------------
# Bookmarks
# -------------------------------------------------------------------


class TestBookmarks:
    """Bookmark create / list / delete."""

    def test_list_bookmarks(self, client):
        resp = client.get("/api/bookmarks/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_bookmark(self, client, bookmark_payload):
        bm = _create_bookmark(client, bookmark_payload)
        try:
            assert bm["title"] == bookmark_payload["title"]
            assert bm["url"] == bookmark_payload["url"]
            assert "id" in bm
            assert "created_at" in bm
        finally:
            _delete_bookmark(client, bm["id"])

    def test_delete_bookmark(self, client, bookmark_payload):
        bm = _create_bookmark(client, bookmark_payload)
        resp = client.delete(f"/api/bookmarks/{bm['id']}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_bookmark_list_pagination(self, client):
        resp = client.get("/api/bookmarks/", params={"limit": 2, "offset": 0})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# -------------------------------------------------------------------
# Actions (Hide / Mute)
# -------------------------------------------------------------------


class TestActions:
    """Hide and mute actions."""

    def test_hide_item(self, client):
        resp = client.post("/api/actions/hide", json={"content_item_id": 999999})
        assert resp.status_code == 200
        assert resp.json()["status"] == "hidden"

    def test_mute_source_permanent(self, client, source_payload):
        source = _create_source(client, source_payload)
        try:
            resp = client.post(
                "/api/actions/mute",
                json={"source_id": source["id"]},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "muted"
            assert data["mute_until"] is None
        finally:
            # Unmute then delete
            client.delete(f"/api/actions/mute/{source['id']}")
            _delete_source(client, source["id"])

    def test_mute_source_with_duration_24h(self, client, source_payload):
        source = _create_source(client, source_payload)
        try:
            resp = client.post(
                "/api/actions/mute",
                json={"source_id": source["id"], "duration": "24h"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "muted"
            assert data["mute_until"] is not None
        finally:
            client.delete(f"/api/actions/mute/{source['id']}")
            _delete_source(client, source["id"])

    def test_mute_source_with_duration_1w(self, client, source_payload):
        source = _create_source(client, source_payload)
        try:
            resp = client.post(
                "/api/actions/mute",
                json={"source_id": source["id"], "duration": "1w"},
            )
            assert resp.status_code == 200
            assert resp.json()["mute_until"] is not None
        finally:
            client.delete(f"/api/actions/mute/{source['id']}")
            _delete_source(client, source["id"])

    def test_mute_source_with_duration_1m(self, client, source_payload):
        source = _create_source(client, source_payload)
        try:
            resp = client.post(
                "/api/actions/mute",
                json={"source_id": source["id"], "duration": "1m"},
            )
            assert resp.status_code == 200
            assert resp.json()["mute_until"] is not None
        finally:
            client.delete(f"/api/actions/mute/{source['id']}")
            _delete_source(client, source["id"])

    def test_unmute_source(self, client, source_payload):
        source = _create_source(client, source_payload)
        try:
            client.post(
                "/api/actions/mute",
                json={"source_id": source["id"]},
            )
            resp = client.delete(f"/api/actions/mute/{source['id']}")
            assert resp.status_code == 200
            assert resp.json()["status"] == "unmuted"
        finally:
            _delete_source(client, source["id"])

    def test_list_muted_sources(self, client):
        resp = client.get("/api/actions/muted")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# -------------------------------------------------------------------
# Digest
# -------------------------------------------------------------------


class TestDigest:
    """Daily digest endpoint."""

    def test_digest_today(self, client):
        resp = client.get("/api/digest/today")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_digest_items_have_rank_and_score(self, client):
        resp = client.get("/api/digest/today")
        for item in resp.json():
            assert "rank" in item
            assert "score" in item
            assert "content_item" in item
            assert isinstance(item["rank"], int)
            assert isinstance(item["score"], (int, float))

    def test_digest_max_10_items(self, client):
        resp = client.get("/api/digest/today")
        assert len(resp.json()) <= 10

    def test_digest_items_ordered_by_rank(self, client):
        items = client.get("/api/digest/today").json()
        if len(items) >= 2:
            ranks = [i["rank"] for i in items]
            assert ranks == sorted(ranks)


# -------------------------------------------------------------------
# Stats
# -------------------------------------------------------------------


class TestStats:
    """Reading stats endpoints."""

    def test_record_event(self, client):
        resp = client.post("/api/stats/event", json={
            "source_id": 1,
            "event_type": "click",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "recorded"

    def test_record_event_with_content_item(self, client):
        resp = client.post("/api/stats/event", json={
            "content_item_id": 1,
            "source_id": 1,
            "event_type": "read",
        })
        assert resp.status_code == 200

    def test_stats_summary(self, client):
        resp = client.get("/api/stats/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "today_count" in data
        assert "week_count" in data
        assert "top_sources" in data
        assert "category_breakdown" in data
        assert isinstance(data["today_count"], int)
        assert isinstance(data["week_count"], int)
        assert isinstance(data["top_sources"], list)
        assert isinstance(data["category_breakdown"], dict)


# -------------------------------------------------------------------
# OPML Export
# -------------------------------------------------------------------


class TestOPML:
    """OPML import / export."""

    def test_export_opml(self, client):
        resp = client.get("/api/opml/export")
        assert resp.status_code == 200
        assert "xml" in resp.headers.get("content-type", "")
        # Parse the XML to verify structure
        root = ET.fromstring(resp.text)
        assert root.tag == "opml"
        assert root.find("head") is not None
        assert root.find("body") is not None

    def test_export_opml_has_title(self, client):
        resp = client.get("/api/opml/export")
        root = ET.fromstring(resp.text)
        title = root.find("head/title")
        assert title is not None
        assert title.text == "Awesome Aggregator Sources"

    def test_import_opml_valid(self, client):
        opml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head><title>Test Import</title></head>
  <body>
    <outline text="Tech" title="Tech">
      <outline type="rss" text="Import Feed"
               xmlUrl="https://example.com/import-test-UNIQUE.xml"
               htmlUrl="https://example.com"/>
    </outline>
  </body>
</opml>"""
        # Make the URL unique to avoid collision
        nonce = str(time.monotonic_ns()).encode()
        unique_opml = opml_content.replace(b"UNIQUE", nonce)
        imported_url = f"https://example.com/import-test-{nonce.decode()}.xml"
        try:
            resp = client.post(
                "/api/opml/import",
                files={"file": ("test.opml", unique_opml, "text/xml")},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "imported" in data
            assert "skipped" in data
        finally:
            # Every other test here removes what it creates. This one did not,
            # so each run left one more "Import Feed" row behind in whatever
            # database the service was pointed at.
            for src in client.get("/api/sources/").json():
                if src.get("url") == imported_url:
                    _delete_source(client, src["id"])


# -------------------------------------------------------------------
# Detect
# -------------------------------------------------------------------


class TestDetect:
    """URL auto-detection endpoint."""

    def test_detect_url_endpoint_exists(self, client):
        resp = client.post("/api/detect/url", json={"url": "https://example.com"})
        # Should not 404/405 -- it may return an error for a non-feed URL
        assert resp.status_code == 200

    def test_detect_returns_source_type(self, client):
        resp = client.post(
            "/api/detect/url",
            json={"url": "https://example.com"},
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "source_type" in data
            assert "name" in data
            assert "url" in data
            assert "preview_items" in data


# -------------------------------------------------------------------
# Reader
# -------------------------------------------------------------------


class TestReader:
    """Reader mode article extraction."""

    def test_reader_extract_endpoint_exists(self, client):
        """Endpoint exists and returns a response (may be 502 for unreachable URL)."""
        resp = client.get("/api/reader/extract", params={"url": "https://example.com"})
        # 200 = extracted, 502 = fetch fail, 503 = trafilatura missing, 422 = no content
        assert resp.status_code in (200, 422, 502, 503)

    def test_reader_extract_missing_url_param(self, client):
        resp = client.get("/api/reader/extract")
        assert resp.status_code == 422


# -------------------------------------------------------------------
# Frontend Serving
# -------------------------------------------------------------------


class TestFrontend:
    """Frontend static files (requires built frontend in frontend/dist/)."""

    def test_root_serves_html_or_api(self, client):
        """Root URL returns either the frontend HTML or the API docs."""
        resp = client.get("/")
        # If frontend is built: 200 HTML. If not: 404 (no static mount).
        assert resp.status_code in (200, 404)

    def test_root_content_type_if_served(self, client):
        resp = client.get("/")
        if resp.status_code == 200:
            ct = resp.headers.get("content-type", "")
            assert "text/html" in ct


# -------------------------------------------------------------------
# Data Layer Integrity
# -------------------------------------------------------------------


class TestDataLayerIntegrity:
    """Verify database tables and schema via API behavior."""

    def test_sources_table_supports_all_types(self, client):
        """All four source types can be created."""
        created_ids = []
        ts = time.monotonic_ns()
        for stype in ("rss", "youtube", "reddit", "generic"):
            payload = {
                "name": f"Type Test {stype} {ts}",
                "source_type": stype,
                "url": f"https://example.com/{stype}-type-test-{ts}",
                "refresh_seconds": 300,
                "display_format": "compact",
                "category": "TypeTest",
            }
            source = _create_source(client, payload)
            created_ids.append(source["id"])
            assert source["source_type"] == stype

        # Cleanup
        for sid in created_ids:
            _delete_source(client, sid)

    def test_sources_table_supports_all_display_formats(self, client):
        """All six display formats are accepted."""
        created_ids = []
        ts = time.monotonic_ns()
        for fmt in ("compact", "magazine", "headlines", "cards", "gallery", "text_only"):
            payload = {
                "name": f"Format {fmt} {ts}",
                "source_type": "rss",
                "url": f"https://example.com/fmt-{fmt}-{ts}",
                "refresh_seconds": 300,
                "display_format": fmt,
                "category": "FormatTest",
            }
            source = _create_source(client, payload)
            created_ids.append(source["id"])
            assert source["display_format"] == fmt

        for sid in created_ids:
            _delete_source(client, sid)

    def test_source_url_uniqueness(self, client, source_payload):
        """Creating two sources with the same URL should fail or be handled."""
        source = _create_source(client, source_payload)
        try:
            resp = client.post("/api/sources/", json=source_payload)
            # Should fail -- either 409 Conflict or 500 integrity error
            assert resp.status_code in (400, 409, 422, 500)
        finally:
            _delete_source(client, source["id"])

    def test_source_fields_persisted(self, client):
        """All source fields round-trip correctly."""
        ts = time.monotonic_ns()
        payload = {
            "name": f"Field Test {ts}",
            "source_type": "reddit",
            "url": f"https://reddit.com/r/python-{ts}",
            "refresh_seconds": 600,
            "display_format": "cards",
            "category": "PersistenceTest",
        }
        source = _create_source(client, payload)
        try:
            fetched = client.get(f"/api/sources/{source['id']}").json()
            assert fetched["name"] == payload["name"]
            assert fetched["source_type"] == payload["source_type"]
            assert fetched["url"] == payload["url"]
            assert fetched["refresh_seconds"] == payload["refresh_seconds"]
            assert fetched["display_format"] == payload["display_format"]
            assert fetched["category"] == payload["category"]
        finally:
            _delete_source(client, source["id"])

    def test_view_source_ids_json_roundtrip(self, client, source_payload):
        """source_ids list serializes/deserializes through the DB correctly."""
        source = _create_source(client, source_payload)
        try:
            view = _create_view(client, {
                "name": f"JSON Test {time.monotonic_ns()}",
                "source_ids": [source["id"]],
            })
            fetched = client.get(f"/api/views/{view['id']}").json()
            assert fetched["source_ids"] == [source["id"]]
            _delete_view(client, view["id"])
        finally:
            _delete_source(client, source["id"])

    def test_cascade_delete_source_removes_content(self, client, source_payload):
        """Deleting a source should not leave orphan content rows accessible."""
        source = _create_source(client, source_payload)
        sid = source["id"]
        # Get content before delete (should be empty for a new source)
        resp = client.get(f"/api/content/source/{sid}")
        assert resp.status_code == 200
        _delete_source(client, sid)
        # After delete, fetching content for that source should 404
        resp = client.get(f"/api/content/source/{sid}")
        assert resp.status_code == 404


# ===================================================================
# NEGATIVE TESTS
# ===================================================================


class TestNegativeSourceEndpoints:
    """Negative tests for source endpoints."""

    def test_get_nonexistent_source(self, client):
        resp = client.get("/api/sources/999999999")
        assert resp.status_code == 404

    def test_delete_nonexistent_source(self, client):
        resp = client.delete("/api/sources/999999999")
        assert resp.status_code == 404

    def test_update_nonexistent_source(self, client):
        resp = client.patch(
            "/api/sources/999999999",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404

    def test_create_source_missing_name(self, client):
        resp = client.post("/api/sources/", json={
            "source_type": "rss",
            "url": "https://example.com/missing-name",
        })
        assert resp.status_code == 422

    def test_create_source_missing_url(self, client):
        resp = client.post("/api/sources/", json={
            "name": "No URL",
            "source_type": "rss",
        })
        assert resp.status_code == 422

    def test_create_source_missing_type(self, client):
        resp = client.post("/api/sources/", json={
            "name": "No Type",
            "url": "https://example.com/no-type",
        })
        assert resp.status_code == 422

    def test_create_source_invalid_type(self, client):
        resp = client.post("/api/sources/", json={
            "name": "Bad Type",
            "source_type": "invalid_type",
            "url": "https://example.com/bad-type",
        })
        assert resp.status_code == 422

    def test_create_source_invalid_display_format(self, client):
        resp = client.post("/api/sources/", json={
            "name": "Bad Format",
            "source_type": "rss",
            "url": "https://example.com/bad-format",
            "display_format": "does_not_exist",
        })
        assert resp.status_code == 422

    def test_create_source_name_too_long(self, client):
        resp = client.post("/api/sources/", json={
            "name": "x" * 201,
            "source_type": "rss",
            "url": "https://example.com/long-name",
        })
        assert resp.status_code == 422

    def test_create_source_empty_name(self, client):
        resp = client.post("/api/sources/", json={
            "name": "",
            "source_type": "rss",
            "url": "https://example.com/empty-name",
        })
        assert resp.status_code == 422

    def test_create_source_refresh_below_minimum(self, client):
        resp = client.post("/api/sources/", json={
            "name": "Fast Refresh",
            "source_type": "rss",
            "url": "https://example.com/fast",
            "refresh_seconds": 5,
        })
        assert resp.status_code == 422

    def test_create_source_refresh_above_maximum(self, client):
        resp = client.post("/api/sources/", json={
            "name": "Slow Refresh",
            "source_type": "rss",
            "url": "https://example.com/slow",
            "refresh_seconds": 100000,
        })
        assert resp.status_code == 422

    def test_batch_create_empty_list(self, client):
        resp = client.post("/api/sources/batch", json={"sources": []})
        assert resp.status_code == 422


class TestNegativeViewEndpoints:
    """Negative tests for view endpoints."""

    def test_get_nonexistent_view(self, client):
        resp = client.get("/api/views/999999999")
        assert resp.status_code == 404

    def test_delete_nonexistent_view(self, client):
        resp = client.delete("/api/views/999999999")
        assert resp.status_code == 404

    def test_update_nonexistent_view(self, client):
        resp = client.patch(
            "/api/views/999999999",
            json={"name": "Ghost View"},
        )
        assert resp.status_code == 404

    def test_create_view_missing_name(self, client):
        resp = client.post("/api/views/", json={
            "description": "No name",
            "source_ids": [],
        })
        assert resp.status_code == 422

    def test_create_view_empty_name(self, client):
        resp = client.post("/api/views/", json={
            "name": "",
            "source_ids": [],
        })
        assert resp.status_code == 422

    def test_view_content_nonexistent(self, client):
        resp = client.get("/api/content/view/999999999")
        assert resp.status_code == 404


class TestNegativeBookmarkEndpoints:
    """Negative tests for bookmark endpoints."""

    def test_delete_nonexistent_bookmark(self, client):
        resp = client.delete("/api/bookmarks/999999999")
        assert resp.status_code == 404

    def test_create_bookmark_missing_fields(self, client):
        resp = client.post("/api/bookmarks/", json={
            "title": "Incomplete",
        })
        assert resp.status_code == 422

    def test_create_bookmark_missing_title(self, client):
        resp = client.post("/api/bookmarks/", json={
            "content_item_id": 1,
            "source_id": 1,
            "url": "https://example.com/no-title",
        })
        assert resp.status_code == 422

    def test_create_bookmark_missing_url(self, client):
        resp = client.post("/api/bookmarks/", json={
            "content_item_id": 1,
            "source_id": 1,
            "title": "No URL",
        })
        assert resp.status_code == 422


class TestNegativeActionEndpoints:
    """Negative tests for action endpoints."""

    def test_unmute_nonexistent_source(self, client):
        resp = client.delete("/api/actions/mute/999999999")
        assert resp.status_code == 404

    def test_hide_missing_content_item_id(self, client):
        resp = client.post("/api/actions/hide", json={})
        assert resp.status_code == 422

    def test_mute_missing_source_id(self, client):
        resp = client.post("/api/actions/mute", json={})
        assert resp.status_code == 422


class TestNegativeLayoutEndpoints:
    """Negative tests for layout endpoints."""

    def test_get_nonexistent_layout(self, client):
        resp = client.get("/api/layouts/nonexistent-layout-99999")
        assert resp.status_code == 404

    def test_save_layout_missing_panels(self, client):
        resp = client.put("/api/layouts/bad-layout", json={})
        assert resp.status_code == 422

    def test_save_layout_invalid_panel_schema(self, client):
        resp = client.put(
            "/api/layouts/bad-schema",
            json={"panels": [{"not_a_valid_field": True}]},
        )
        assert resp.status_code == 422


class TestNegativeContentEndpoints:
    """Negative tests for content endpoints."""

    def test_content_for_nonexistent_source(self, client):
        resp = client.get("/api/content/source/999999999")
        assert resp.status_code == 404

    def test_content_limit_exceeds_max(self, client):
        """limit > 1000 should be rejected by validation."""
        resp = client.get("/api/content/", params={"limit": 5000})
        assert resp.status_code == 422

    def test_content_negative_limit(self, client):
        resp = client.get("/api/content/", params={"limit": -1})
        assert resp.status_code == 422

    def test_content_negative_offset(self, client):
        resp = client.get("/api/content/", params={"offset": -1})
        assert resp.status_code == 422


class TestNegativeDetect:
    """Negative tests for detect endpoint."""

    def test_detect_missing_url(self, client):
        resp = client.post("/api/detect/url", json={})
        assert resp.status_code == 422

    def test_detect_empty_url(self, client):
        resp = client.post("/api/detect/url", json={"url": ""})
        # Pydantic may allow empty string; the endpoint should handle it
        assert resp.status_code in (200, 422)


class TestNegativeReader:
    """Negative tests for reader endpoint."""

    def test_reader_url_too_short(self, client):
        resp = client.get("/api/reader/extract", params={"url": "ab"})
        assert resp.status_code == 422

    def test_reader_missing_url(self, client):
        resp = client.get("/api/reader/extract")
        assert resp.status_code == 422


class TestNegativeStats:
    """Negative tests for stats endpoint."""

    def test_record_event_missing_source_id(self, client):
        resp = client.post("/api/stats/event", json={
            "event_type": "click",
        })
        assert resp.status_code == 422

    def test_record_event_missing_event_type(self, client):
        resp = client.post("/api/stats/event", json={
            "source_id": 1,
        })
        assert resp.status_code == 422


class TestNegativeOPML:
    """Negative tests for OPML endpoints."""

    def test_import_invalid_xml(self, client):
        resp = client.post(
            "/api/opml/import",
            files={"file": ("bad.opml", b"not xml at all", "text/xml")},
        )
        assert resp.status_code == 400

    def test_import_xml_without_body(self, client):
        opml = b"""<?xml version="1.0"?>
<opml version="2.0"><head><title>No Body</title></head></opml>"""
        resp = client.post(
            "/api/opml/import",
            files={"file": ("nobody.opml", opml, "text/xml")},
        )
        assert resp.status_code == 400

    def test_import_opml_no_feeds(self, client):
        opml = b"""<?xml version="1.0"?>
<opml version="2.0">
  <head><title>Empty</title></head>
  <body><outline text="Category"/></body>
</opml>"""
        resp = client.post(
            "/api/opml/import",
            files={"file": ("empty.opml", opml, "text/xml")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 0


# -------------------------------------------------------------------
# HTTP Method Enforcement
# -------------------------------------------------------------------


class TestWrongHTTPMethods:
    """Verify that wrong HTTP methods return 405 Method Not Allowed."""

    def test_post_to_health(self, client):
        resp = client.post("/api/health")
        assert resp.status_code == 405

    def test_put_to_sources_list(self, client):
        resp = client.put("/api/sources/")
        assert resp.status_code == 405

    def test_delete_to_sources_list(self, client):
        resp = client.delete("/api/sources/")
        assert resp.status_code == 405

    def test_post_to_content_feed(self, client):
        resp = client.post("/api/content/")
        assert resp.status_code == 405

    def test_put_to_views_list(self, client):
        resp = client.put("/api/views/")
        assert resp.status_code == 405

    def test_post_to_digest(self, client):
        resp = client.post("/api/digest/today")
        assert resp.status_code == 405

    def test_put_to_bookmarks_list(self, client):
        resp = client.put("/api/bookmarks/")
        assert resp.status_code == 405

    def test_post_to_stats_summary(self, client):
        resp = client.post("/api/stats/summary")
        assert resp.status_code == 405

    def test_put_to_opml_export(self, client):
        resp = client.put("/api/opml/export")
        assert resp.status_code == 405


# -------------------------------------------------------------------
# Invalid API Paths
# -------------------------------------------------------------------


class TestInvalidPaths:
    """Non-existent API paths should return 404."""

    def test_nonexistent_api_path(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_typo_in_sources_path(self, client):
        resp = client.get("/api/source/")
        assert resp.status_code == 404

    def test_nonexistent_nested_path(self, client):
        resp = client.get("/api/sources/1/nonexistent")
        assert resp.status_code == 404

    def test_double_api_prefix(self, client):
        resp = client.get("/api/api/sources/")
        assert resp.status_code == 404


# -------------------------------------------------------------------
# XSS / Injection Resistance
# -------------------------------------------------------------------


class TestInputSanitization:
    """Ensure potentially malicious input does not produce unsafe output."""

    def test_xss_in_source_name(self, client):
        xss_name = '<script>alert("xss")</script>'
        ts = time.monotonic_ns()
        payload = {
            "name": xss_name,
            "source_type": "rss",
            "url": f"https://example.com/xss-test-{ts}",
            "refresh_seconds": 300,
            "display_format": "compact",
            "category": "XSS",
        }
        resp = client.post("/api/sources/", json=payload)
        if resp.status_code == 201:
            data = resp.json()
            # The name is stored -- verify it does not get executed
            # (API returns JSON, not HTML, so XSS is inherently mitigated)
            assert data["name"] == xss_name
            fetched = client.get(f"/api/sources/{data['id']}").json()
            assert fetched["name"] == xss_name
            _delete_source(client, data["id"])
        else:
            # If the server rejects XSS input, that is also acceptable
            assert resp.status_code in (400, 422)

    def test_xss_in_view_name(self, client):
        xss_name = '<img src=x onerror=alert(1)>'
        resp = client.post("/api/views/", json={
            "name": xss_name,
            "source_ids": [],
        })
        if resp.status_code == 201:
            data = resp.json()
            assert data["name"] == xss_name
            _delete_view(client, data["id"])

    def test_xss_in_bookmark_notes(self, client):
        xss_notes = '"><img src=x onerror=alert(document.cookie)>'
        ts = time.monotonic_ns()
        payload = {
            "content_item_id": int(ts % 100000),
            "source_id": 1,
            "title": "XSS Bookmark",
            "url": f"https://example.com/xss-bm-{ts}",
            "notes": xss_notes,
        }
        resp = client.post("/api/bookmarks/", json=payload)
        if resp.status_code == 201:
            data = resp.json()
            assert data["notes"] == xss_notes
            _delete_bookmark(client, data["id"])

    def test_sql_injection_in_source_name(self, client):
        """SQL injection in source name should be safely parameterized."""
        sqli_name = "'; DROP TABLE sources; --"
        ts = time.monotonic_ns()
        payload = {
            "name": sqli_name,
            "source_type": "rss",
            "url": f"https://example.com/sqli-{ts}",
            "refresh_seconds": 300,
            "display_format": "compact",
            "category": "SQLi",
        }
        resp = client.post("/api/sources/", json=payload)
        if resp.status_code == 201:
            data = resp.json()
            # Sources table still works
            all_sources = client.get("/api/sources/").json()
            assert isinstance(all_sources, list)
            assert any(s["id"] == data["id"] for s in all_sources)
            _delete_source(client, data["id"])

    def test_sql_injection_in_view_filters(self, client):
        """SQL injection in topic_filters should be safely handled."""
        sqli_filter = ["'; DROP TABLE views; --"]
        resp = client.post("/api/views/", json={
            "name": f"SQLi View {time.monotonic_ns()}",
            "source_ids": [],
            "topic_filters": sqli_filter,
        })
        if resp.status_code == 201:
            data = resp.json()
            assert data["topic_filters"] == sqli_filter
            # Views table still works
            all_views = client.get("/api/views/").json()
            assert isinstance(all_views, list)
            _delete_view(client, data["id"])

    def test_sql_injection_in_layout_name(self, client):
        sqli_name = "layout'; DROP TABLE layouts;--"
        payload = {
            "name": sqli_name,
            "panels": [{"source_id": 1, "x": 0, "y": 0, "w": 4, "h": 3}],
        }
        resp = client.put(f"/api/layouts/{sqli_name}", json=payload)
        assert resp.status_code == 200
        # Layouts table still exists
        resp2 = client.get(f"/api/layouts/{sqli_name}")
        assert resp2.status_code == 200


# -------------------------------------------------------------------
# Malformed JSON
# -------------------------------------------------------------------


class TestMalformedJSON:
    """Requests with malformed JSON bodies should be handled gracefully."""

    def test_malformed_json_create_source(self, client):
        resp = client.post(
            "/api/sources/",
            content=b"{not valid json}",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_malformed_json_create_view(self, client):
        resp = client.post(
            "/api/views/",
            content=b"{{broken",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_malformed_json_create_bookmark(self, client):
        resp = client.post(
            "/api/bookmarks/",
            content=b"[truncated",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_malformed_json_hide_action(self, client):
        resp = client.post(
            "/api/actions/hide",
            content=b"{{{{",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_malformed_json_mute_action(self, client):
        resp = client.post(
            "/api/actions/mute",
            content=b"garbage",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_malformed_json_stats_event(self, client):
        resp = client.post(
            "/api/stats/event",
            content=b"{'single': 'quotes'}",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_malformed_json_detect(self, client):
        resp = client.post(
            "/api/detect/url",
            content=b"null",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_malformed_json_save_layout(self, client):
        resp = client.put(
            "/api/layouts/bad",
            content=b"{broken",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_malformed_json_reorder_views(self, client):
        resp = client.put(
            "/api/views/reorder",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422
