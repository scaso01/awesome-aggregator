"""Each user action, driven against the live service with the payload the UI sends.

The route contract test proves the frontend calls a URL that exists. It cannot
prove the body is right, and two actions were broken on exactly that: Hide sent
`item_id` where the API wants `content_item_id`, and tab reordering sent
`{order: [...]}` where the API wants `{view_ids: [...]}`. Both returned 422 into
a bare catch, so the menu closed and nothing happened.

Every request below is byte for byte what the corresponding component sends. If
someone changes a field name on either side, one of these turns red.

Run with the service up:
    python -m backend.app &
    python -m pytest tests/test_ui_actions.py -v
"""

import json
import time

import httpx
import pytest
from websockets.sync.client import connect

BASE_URL = "http://localhost:8001"


def is_service_running() -> bool:
    """True only if awesome-aggregator's own health check answers, not just any program on 8001."""
    try:
        body = httpx.get(f"{BASE_URL}/api/health", timeout=2).json()
    except (httpx.HTTPError, ValueError):
        return False
    return isinstance(body, dict) and body.get("status") == "ok" and "websocket_clients" in body


pytestmark = [
    pytest.mark.dashboard,
    pytest.mark.skipif(
        not is_service_running(),
        reason="awesome-aggregator not running on localhost:8001",
    ),
]


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as c:
        yield c


@pytest.fixture()
def a_source(client):
    """A throwaway source, removed afterwards."""
    payload = {
        "name": f"UI Action Source {time.monotonic_ns()}",
        "source_type": "rss",
        "url": f"https://example.com/ui-{time.monotonic_ns()}.xml",
        "refresh_seconds": 300,
        "display_format": "compact",
    }
    created = client.post("/api/sources/", json=payload)
    assert created.status_code in (200, 201), created.text
    source = created.json()
    yield source
    client.delete(f"/api/sources/{source['id']}")


@pytest.fixture()
def an_item(client):
    """A real content item from whichever source has one."""
    sources = client.get("/api/sources/").json()
    for source in sources:
        items = client.get(f"/api/content/source/{source['id']}?limit=1").json()
        if items:
            return items[0]
    pytest.skip("no content has been fetched yet, so there is no item to act on")


# --- Bookmark, the three dot menu and reader mode -----------------------------


def test_bookmark_uses_a_route_that_exists(client, an_item):
    """The UI posted to /api/actions/bookmark for months. It is a 405."""
    dead = client.post(
        "/api/actions/bookmark",
        json={"content_item_id": an_item["id"], "url": an_item["url"]},
    )
    assert dead.status_code >= 400, (
        "if /api/actions/bookmark ever becomes real, revisit which route the UI "
        "should use, but it must not be silently reintroduced"
    )


def test_bookmark_round_trip(client, an_item):
    """Exactly the body ItemActionMenu and ReaderMode send."""
    body = {
        "content_item_id": an_item["id"],
        "source_id": an_item["source_id"],
        "title": an_item["title"],
        "url": an_item["url"],
        "image_url": an_item.get("image_url"),
    }
    created = client.post("/api/bookmarks/", json=body)
    assert created.status_code == 201, created.text
    bookmark = created.json()

    listed = client.get("/api/bookmarks/")
    assert listed.status_code == 200
    assert any(b["id"] == bookmark["id"] for b in listed.json()), \
        "a new bookmark must appear in the list the Bookmarks tab reads"

    removed = client.delete(f"/api/bookmarks/{bookmark['id']}")
    assert removed.status_code == 200
    assert not any(b["id"] == bookmark["id"] for b in client.get("/api/bookmarks/").json())


def test_removing_a_missing_bookmark_is_a_404(client):
    assert client.delete("/api/bookmarks/99999999").status_code == 404


def test_bookmarking_the_same_item_twice_is_not_an_error(client, an_item):
    """content_item_id is UNIQUE, and the second insert used to be a 500.

    Users bookmark the same thing twice, and one item can appear in two panels
    at once, so this has to be idempotent rather than an unhandled
    IntegrityError.
    """
    body = {
        "content_item_id": an_item["id"],
        "source_id": an_item["source_id"],
        "title": an_item["title"],
        "url": an_item["url"],
    }
    first = client.post("/api/bookmarks/", json=body)
    assert first.status_code == 201, first.text

    second = client.post("/api/bookmarks/", json=body)
    assert second.status_code == 201, second.text
    assert second.json()["id"] == first.json()["id"], "should return the same row"

    listed = client.get("/api/bookmarks/").json()
    matching = [b for b in listed if b["content_item_id"] == an_item["id"]]
    assert len(matching) == 1, "no duplicate rows"

    client.delete(f"/api/bookmarks/{first.json()['id']}")


# --- Hide ---------------------------------------------------------------------


def test_hide_accepts_the_payload_the_menu_sends(client, an_item):
    res = client.post("/api/actions/hide", json={"content_item_id": an_item["id"]})
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "hidden"


def test_hide_rejects_the_old_wrong_field(client, an_item):
    """Regression guard. Sending item_id was the bug, and it 422s."""
    res = client.post("/api/actions/hide", json={"item_id": an_item["id"]})
    assert res.status_code == 422


# --- Mute and unmute ----------------------------------------------------------


@pytest.mark.parametrize("duration", ["24h", "1w", "1m", "permanent"])
def test_mute_every_duration_the_menu_offers(client, a_source, duration):
    res = client.post(
        "/api/actions/mute",
        json={"source_id": a_source["id"], "duration": duration},
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "muted"

    if duration == "permanent":
        assert res.json()["mute_until"] is None
    else:
        assert res.json()["mute_until"], f"{duration} should set an expiry"

    assert client.delete(f"/api/actions/mute/{a_source['id']}").status_code == 200


def test_muted_list_reflects_a_mute(client, a_source):
    client.post("/api/actions/mute", json={"source_id": a_source["id"], "duration": "24h"})
    muted = client.get("/api/actions/muted").json()
    assert any(m["source_id"] == a_source["id"] for m in muted)
    client.delete(f"/api/actions/mute/{a_source['id']}")


# --- Views and tab reordering -------------------------------------------------


def test_reorder_accepts_the_payload_the_tab_bar_sends(client):
    """PUT with view_ids. The UI used to POST with {order: [...]}."""
    made = []
    for name in ("UI Reorder A", "UI Reorder B"):
        res = client.post("/api/views/", json={"name": name, "source_ids": [], "keywords": []})
        assert res.status_code in (200, 201), res.text
        made.append(res.json()["id"])

    try:
        reordered = client.put("/api/views/reorder", json={"view_ids": list(reversed(made))})
        assert reordered.status_code == 200, reordered.text

        wrong_field = client.put("/api/views/reorder", json={"order": made})
        assert wrong_field.status_code == 422, "the old body must not quietly work"

        wrong_method = client.post("/api/views/reorder", json={"view_ids": made})
        assert wrong_method.status_code >= 400, "the old method must not quietly work"
    finally:
        for view_id in made:
            client.delete(f"/api/views/{view_id}")


# --- Layout persistence -------------------------------------------------------


def test_layout_survives_a_save_and_reload(client, a_source):
    """The dashboard saved this on every drag and never read it back."""
    panels = [{"source_id": a_source["id"], "x": 4, "y": 8, "w": 6, "h": 5}]
    saved = client.put("/api/layouts/default", json={"name": "default", "panels": panels})
    assert saved.status_code == 200, saved.text

    loaded = client.get("/api/layouts/default")
    assert loaded.status_code == 200, "the app reads this back on startup"
    got = loaded.json()["panels"]
    assert len(got) == 1
    assert (got[0]["x"], got[0]["y"], got[0]["w"], got[0]["h"]) == (4, 8, 6, 5)


# --- Digest -------------------------------------------------------------------


def test_digest_rows_carry_a_nested_content_item(client):
    """The shape the digest view has to unwrap.

    Reading title and url off the top level gave a list of "Untitled" rows with
    no links, which is what the tab actually showed.
    """
    res = client.get("/api/digest/today")
    assert res.status_code == 200
    rows = res.json()
    if not rows:
        pytest.skip("no items in the last 24h to rank")

    for row in rows:
        assert "content_item" in row, "the payload nests the item"
        assert "rank" in row and "score" in row
        assert row["content_item"].get("title"), "a row needs a title to render"
        assert row["content_item"].get("url"), "a row needs a url to be clickable"
    assert [r["rank"] for r in rows] == sorted(r["rank"] for r in rows)


# --- Reading stats ------------------------------------------------------------


def test_reading_event_then_summary(client, an_item):
    res = client.post(
        "/api/stats/event",
        json={
            "content_item_id": an_item["id"],
            "source_id": an_item["source_id"],
            "event_type": "click",
        },
    )
    assert res.status_code in (200, 201), res.text

    summary = client.get("/api/stats/summary")
    assert summary.status_code == 200
    body = summary.json()

    # ReadingStats.jsx renders exactly these. It used to read articles_today,
    # articles_week and a scalar top_source, so the bar was pinned at zero.
    assert "today_count" in body
    assert "week_count" in body
    assert isinstance(body.get("top_sources"), list)
    assert body["today_count"] >= 1, "the event just recorded should count"
    if body["top_sources"]:
        assert "name" in body["top_sources"][0]


# --- Reader extraction --------------------------------------------------------


def test_reader_extract_answers_for_a_real_article(client):
    res = client.get("/api/reader/extract", params={"url": "https://example.com"})
    assert res.status_code == 200, res.text
    body = res.json()

    # ReaderMode.jsx decides between the clean reader view and the iframe
    # fallback on content_html, and renders the rest of these. It used to test
    # `data.content`, which this endpoint has never returned, so the extracted
    # view was unreachable and every article opened as a plain iframe.
    assert "content_html" in body, "reader mode branches on this key"
    assert body["content_html"], "example.com does extract to something"
    for key in ("title", "author", "date", "site_name", "hero_image",
                "estimated_read_minutes"):
        assert key in body, f"ReaderMode renders {key}"


# --- The WebSocket carries traffic, not just a handshake ----------------------


def test_the_socket_delivers_scheduler_events(client, a_source):
    """CI proves /ws completes a handshake. This proves it then carries events.

    A socket that upgrades cleanly and never broadcasts looks identical from
    outside, and would leave the board frozen until someone reloaded, which is
    the one thing live updates are there to avoid.

    The throwaway source points at a URL that cannot be fetched, which is what
    makes this deterministic: the refresh is guaranteed to finish and report,
    with no dependency on a real feed having published anything.
    """
    with connect(f"{BASE_URL.replace('http', 'ws')}/ws", open_timeout=15) as ws:
        # Patching reschedules the job to run within seconds. It is the only
        # handle the API offers for "refresh this now".
        patched = client.patch(
            f"/api/sources/{a_source['id']}", json={"refresh_seconds": 301}
        )
        assert patched.status_code == 200, patched.text

        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                raw = ws.recv(timeout=10)
            except TimeoutError:
                continue
            message = json.loads(raw)
            if message.get("source_id") == a_source["id"]:
                assert message["type"] in ("source_update", "new_content")
                return

    pytest.fail("the refresh produced no WebSocket message for that source")
