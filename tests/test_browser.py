"""End to end tests driven through a real browser.

These exist because a whole class of failure here was invisible to everything
else. The backend was healthy and its tests passed. The frontend compiled. The
API contract test proved each call reached a real route. And the app was still
broken, because components read response fields that did not exist, and one
component was imported but never rendered at all. Nothing short of opening the
page and clicking catches that.

Requires the built frontend and a running service:
    cd frontend && npm run build && cd ..
    python -m backend.app &
    python -m pytest tests/test_browser.py -v
"""

import os
import re
import socket
import tempfile
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from contextlib import closing
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest

playwright_api = pytest.importorskip(
    "playwright.sync_api", reason="playwright is not installed"
)
sync_playwright = playwright_api.sync_playwright

BASE_URL = "http://localhost:8001"
DIST = Path(__file__).parent.parent / "frontend" / "dist" / "index.html"


def is_service_running() -> bool:
    try:
        with closing(socket.create_connection(("localhost", 8001), timeout=2)):
            return True
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False


pytestmark = [
    pytest.mark.browser,
    pytest.mark.skipif(
        not is_service_running(),
        reason="awesome-aggregator not running on localhost:8001",
    ),
    pytest.mark.skipif(
        not DIST.exists(),
        reason="frontend/dist is missing, run npm run build",
    ),
]


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture()
def page(browser):
    ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(BASE_URL, wait_until="networkidle", timeout=60000)
    pg.wait_for_selector(".content-panel", timeout=30000)
    yield pg
    assert not errors, f"uncaught JavaScript errors: {errors}"
    ctx.close()


def open_first_article(page):
    """Click the first item title, which opens the reader overlay."""
    page.locator(".item-title a").first.click()
    page.wait_for_selector(".reader-overlay", timeout=30000)


def open_extractable_article(page):
    """Open an article the reader endpoint can actually extract.

    Extraction genuinely fails on some sites, and the iframe fallback is the
    designed response. Roughly one item in five on a typical board lands there,
    so a test that always clicks the first item is a coin toss. Ask the API
    which items extract, then click one of those.
    """
    links = page.locator(".item-title a")
    urls = [
        links.nth(i).get_attribute("href")
        for i in range(min(links.count(), 12))
    ]
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        for url in urls:
            if not url:
                continue
            try:
                res = client.get("/api/reader/extract", params={"url": url})
            except httpx.HTTPError:
                continue
            if res.status_code == 200 and res.json().get("content_html"):
                link = page.locator(f'.item-title a[href="{url}"]').first
                # The feed's title, which is what a bookmark stores. The reader
                # heading shows the extracted title instead, and the two are
                # often different wording for the same article.
                feed_title = link.inner_text().strip()
                link.click()
                page.wait_for_selector(".reader-article", timeout=30000)
                return feed_title
    pytest.skip("no currently loaded article could be extracted")


# --- The board renders --------------------------------------------------------


def test_dashboard_renders_panels_with_content(page):
    panels = page.locator(".content-panel")
    assert panels.count() >= 1
    assert page.locator(".content-item, .gallery-item").count() > 0, \
        "panels should hold fetched items"


def test_no_panel_is_showing_a_fetch_error(page):
    """Every configured source should actually be fetching.

    Reddit failed here for a long time: the default r/technology source sat on
    "403 Blocked" so a new user's first screen had a dead panel.

    A 429 is treated separately. Being rate limited by an upstream service is
    not a defect in this project, and running this suite repeatedly against
    live Reddit will earn one. A 403, a 404 or a parse failure is a real
    problem and still fails.
    """
    errors = page.locator(".error-text")
    messages = [errors.nth(i).inner_text() for i in range(errors.count())]

    throttled = [m for m in messages if "429" in m or "Too Many Requests" in m]
    real = [m for m in messages if m not in throttled]

    assert not real, f"panels reporting errors: {real}"
    if throttled:
        pytest.skip(f"an upstream source is rate limiting us: {throttled}")


def test_reddit_panel_has_items(page):
    """The Reddit adapter, exercised through the running app."""
    panel = page.locator(".content-panel").filter(has_text="r/technology")
    if panel.count() == 0:
        pytest.skip("no Reddit source configured in this database")

    error = panel.first.locator(".error-text")
    if error.count() and "429" in error.first.inner_text():
        pytest.skip("Reddit is rate limiting us, which is not a defect here")

    assert panel.first.locator(".content-item, .gallery-item").count() > 0, \
        "the Reddit panel should hold posts, not an error"


# --- Reader mode --------------------------------------------------------------


def test_clicking_an_article_opens_reader_mode(page):
    open_first_article(page)
    assert page.locator(".reader-overlay").is_visible()


def test_clicking_a_thumbnail_opens_the_article(page):
    """The picture is a click target, and most of it used to be dead.

    react-grid-layout disables pointer events on images inside a grid item, so
    the click has to land on the surrounding anchor. That anchor was inline and
    therefore only as tall as a line of text, about a third of the thumbnail.
    Clicking the middle of a visible image did nothing.
    """
    with_image = page.locator(".content-item.has-image")
    if with_image.count() == 0:
        pytest.skip("no items with thumbnails are loaded")

    link = with_image.first.locator(".item-image-wrap a").first
    box = link.bounding_box()
    wrap = with_image.first.locator(".item-image-wrap").bounding_box()
    assert box["height"] >= wrap["height"] - 1, (
        f"the thumbnail link is {box['height']:.0f}px tall inside a "
        f"{wrap['height']:.0f}px image, so most of the picture is not clickable"
    )

    link.click()
    page.wait_for_selector(".reader-overlay", timeout=30000)


def test_reader_shows_extracted_text_not_an_iframe(page):
    """The clean reader view has to actually be reachable.

    ReaderMode was imported into App.jsx and never rendered, so an inferior
    iframe viewer was used instead. Once it was rendered it still always fell
    through to its own iframe fallback, because it branched on a response field
    the reader endpoint does not return. Both bugs look identical from outside:
    an iframe where the article should be.
    """
    open_extractable_article(page)
    body = page.locator(".reader-article").inner_text().strip()
    assert body, "the extracted article body should not be empty"
    assert page.locator(".reader-overlay iframe").count() == 0, \
        "falling back to an iframe means extraction did not render"


def test_reader_falls_back_to_an_iframe_when_extraction_fails(page):
    """The fallback is designed behaviour, not a bug, and should stay working.

    Some sites cannot be extracted. The reader is expected to show them in an
    iframe rather than an empty page.
    """
    links = page.locator(".item-title a")
    urls = [links.nth(i).get_attribute("href") for i in range(min(links.count(), 12))]
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        for url in urls:
            if not url:
                continue
            try:
                res = client.get("/api/reader/extract", params={"url": url})
            except httpx.HTTPError:
                continue
            if res.status_code != 200 or not res.json().get("content_html"):
                page.locator(f'.item-title a[href="{url}"]').first.click()
                page.wait_for_selector(".reader-overlay", timeout=30000)
                page.wait_for_selector(".reader-overlay iframe", timeout=30000)
                return
    pytest.skip("every loaded article extracted, nothing exercises the fallback")


def test_reader_heading_falls_back_to_the_feed_title(page):
    """Extraction returns the literal "Untitled" when it finds no heading.

    That string is truthy, so it beat the perfectly good title already on the
    item and the reader displayed a large "Untitled" above the article.
    """
    feed_title = open_extractable_article(page)
    heading = page.locator(".reader-title").inner_text().strip()
    assert heading, "the reader needs a heading"
    if heading == "Untitled":
        assert feed_title == "Untitled", (
            f"reader showed 'Untitled' when the item is called {feed_title!r}"
        )


def test_reader_font_controls_change_the_size(page):
    open_extractable_article(page)
    article = page.locator(".reader-article")
    before = article.evaluate("el => getComputedStyle(el).fontSize")
    page.get_by_role("button", name="A+").click()
    after = article.evaluate("el => getComputedStyle(el).fontSize")
    assert float(after[:-2]) > float(before[:-2])


def test_escape_closes_the_reader(page):
    open_first_article(page)
    page.keyboard.press("Escape")
    page.wait_for_selector(".reader-overlay", state="detached", timeout=10000)


# --- Bookmarks ----------------------------------------------------------------


def test_bookmark_from_reader_reaches_the_bookmarks_tab(page):
    """The full user journey that was dead end to end.

    The button posted to a route that does not exist, the failure was swallowed,
    and the tab never fetched anything anyway.
    """
    feed_title = open_extractable_article(page)

    page.get_by_role("button", name="Bookmark", exact=True).click()
    page.wait_for_selector("button:has-text('Bookmarked')", timeout=15000)
    page.keyboard.press("Escape")

    page.get_by_role("button", name="Bookmarks").click()
    page.wait_for_selector(".digest-item", timeout=15000)
    listed = page.locator(".digest-container").inner_text()
    assert "No bookmarks yet" not in listed
    assert feed_title[:30] in listed, \
        f"expected {feed_title[:30]!r} in the bookmarks tab"


def test_bookmark_can_be_removed(page):
    open_extractable_article(page)
    page.get_by_role("button", name="Bookmark", exact=True).click()
    page.wait_for_selector("button:has-text('Bookmarked')", timeout=15000)
    page.keyboard.press("Escape")

    page.get_by_role("button", name="Bookmarks").click()
    page.wait_for_selector(".digest-item", timeout=15000)
    before = page.locator(".digest-item").count()

    page.locator(".digest-item button:has-text('Remove')").first.click()
    page.wait_for_function(
        f"document.querySelectorAll('.digest-item').length < {before}",
        timeout=15000,
    )


# --- Hide ---------------------------------------------------------------------


def test_every_item_offers_the_action_menu(page):
    """ItemActionMenu was imported by nothing, so this count was zero."""
    items = page.locator(".content-item").count()
    triggers = page.locator(".item-action-trigger").count()
    assert triggers == items, \
        f"{items} items on screen but {triggers} action menus"


def test_action_menu_opens_with_all_its_options(page):
    page.locator(".content-item").first.locator(".item-action-trigger").click()
    page.wait_for_selector(".item-action-menu", timeout=10000)
    menu = page.locator(".item-action-menu").first
    for label in ("Bookmark", "Hide this item", "Mute source", "Open in new tab"):
        assert menu.get_by_text(label, exact=True).count() >= 1, f"missing {label!r}"


def test_muted_sources_manager_opens(page):
    """MutedSources was also orphaned, so there was no way to reach it."""
    page.get_by_role("button", name="Muted").click()
    page.wait_for_selector(".view-editor", timeout=10000)
    assert "Muted Sources" in page.locator(".view-editor").inner_text()
    page.get_by_role("button", name="Close").click()
    page.wait_for_selector(".view-editor", state="detached", timeout=10000)


def test_add_source_offers_a_url_preview(page):
    """SourcePreview was orphaned too, so auto-detect had no entry point."""
    page.get_by_role("button", name="+ Add Source").click()
    page.wait_for_selector(".tab-bar", timeout=10000)
    page.get_by_role("button", name="Custom URL").click()
    preview = page.get_by_role("button", name="Preview")
    assert preview.count() == 1
    assert preview.is_disabled(), "nothing to preview before a URL is typed"

    page.locator('input[type="url"]').fill("https://hnrss.org/frontpage")
    assert preview.is_enabled()
    preview.click()
    page.wait_for_selector(".source-preview", timeout=45000)
    body = page.locator(".source-preview-body")
    body.wait_for(state="visible", timeout=10000)
    page.wait_for_function(
        "() => !document.querySelector('.source-preview-body .loading')",
        timeout=45000,
    )
    assert "rss" in body.inner_text().lower(), "the type should be detected"


# --- Digest -------------------------------------------------------------------


def test_digest_rows_are_titled_and_clickable(page):
    """Every row rendered as "Untitled" with no link.

    The endpoint nests the item under content_item and the view read the fields
    off the wrapper, so nothing resolved.
    """
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        expected = len(client.get("/api/digest/today").json())
    if expected == 0:
        pytest.skip("nothing published in the last 24h to rank")

    page.get_by_role("button", name="Digest").click()
    page.wait_for_selector(".digest-container", timeout=20000)
    # The view shows a loading state first, and .digest-container is present
    # throughout it. Counting rows straight away reads zero every time.
    page.wait_for_function(
        "n => document.querySelectorAll('.digest-item').length === n",
        arg=expected,
        timeout=20000,
    )

    rows = page.locator(".digest-item")
    titles = page.locator(".digest-item-title a")
    assert titles.count() == rows.count(), "every row needs a link"
    for i in range(titles.count()):
        text = titles.nth(i).inner_text().strip()
        assert text and text != "Untitled", f"row {i} rendered as {text!r}"
        assert titles.nth(i).get_attribute("href"), f"row {i} has no href"


# --- Reading stats ------------------------------------------------------------


def test_reading_stats_bar_renders_counts(page):
    """Pinned at zero while it read field names the API never returned."""
    values = page.locator(".reading-stats-value")
    assert values.count() >= 2
    for i in range(values.count()):
        assert values.nth(i).inner_text().strip() != "", "a stat rendered blank"


# --- Layout persistence -------------------------------------------------------


def test_a_saved_layout_is_applied_on_load(page):
    """The bug, tested directly: the layout was written and never read back.

    Saving a panel at a known column and reloading is deterministic, unlike
    synthesising a drag, so this fails loudly if the app goes back to
    recomputing the default arrangement and discarding what was stored.
    """
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        sources = [s for s in client.get("/api/sources/").json()
                   if s.get("status") != "paused"]
        if len(sources) < 2:
            pytest.skip("need at least two sources to tell positions apart")

        # Put the first source in the far right column, where the default
        # arrangement would never place it.
        first = sources[0]
        panels = [{"source_id": first["id"], "x": 8, "y": 0, "w": 4, "h": 4}]
        panels += [
            {"source_id": s["id"], "x": (i % 2) * 4, "y": 0, "w": 4, "h": 4}
            for i, s in enumerate(sources[1:])
        ]
        saved = client.put("/api/layouts/default", json={"name": "default", "panels": panels})
        assert saved.status_code == 200, saved.text

    page.reload(wait_until="networkidle")
    page.wait_for_selector(".content-panel", timeout=30000)
    page.wait_for_timeout(1200)

    titles = page.locator(".content-panel .panel-title")
    positions = {
        titles.nth(i).inner_text().strip():
            page.locator(".content-panel").nth(i).bounding_box()["x"]
        for i in range(titles.count())
    }
    assert first["name"] in positions, f"panel {first['name']!r} not on screen"

    others = [x for name, x in positions.items() if name != first["name"]]
    assert others, "need another panel to compare against"
    assert positions[first["name"]] > max(others), (
        f"{first['name']!r} was saved in the rightmost column but came back at "
        f"x={positions[first['name']]:.0f}, left of {max(others):.0f}. The saved "
        f"layout was ignored."
    )


def test_dragging_a_panel_persists_across_a_reload(page):
    """The same property through the real interaction, handle and all."""
    panels = page.locator(".content-panel")
    if panels.count() < 2:
        pytest.skip("need at least two panels to have somewhere to drag to")

    handle = panels.first.locator(".panel-drag-handle")
    before = panels.first.bounding_box()
    grip = handle.bounding_box()

    # Drag towards whichever side has room. A panel already parked in the
    # rightmost column cannot move further right, and reading that as "dragging
    # is broken" would be wrong.
    viewport = page.viewport_size["width"]
    direction = -1 if before["x"] + before["width"] / 2 > viewport / 2 else 1

    page.mouse.move(grip["x"] + grip["width"] / 2, grip["y"] + grip["height"] / 2)
    page.mouse.down()
    # react-grid-layout needs a few moves before it starts tracking a drag.
    for step in range(1, 16):
        page.mouse.move(
            grip["x"] + grip["width"] / 2 + direction * step * 30,
            grip["y"] + grip["height"] / 2,
        )
        page.wait_for_timeout(20)
    page.mouse.up()
    page.wait_for_timeout(2000)

    moved = page.locator(".content-panel").first.bounding_box()
    assert abs(moved["x"] - before["x"]) > 50, (
        f"dragging the panel handle did nothing: x stayed at {before['x']:.0f}. "
        f"Panels are supposed to be draggable."
    )

    page.reload(wait_until="networkidle")
    page.wait_for_selector(".content-panel", timeout=30000)
    page.wait_for_timeout(1500)

    after = page.locator(".content-panel").first.bounding_box()
    assert abs(after["x"] - moved["x"]) < 80, (
        f"layout reset on reload: dragged to x={moved['x']:.0f}, "
        f"came back at x={after['x']:.0f}"
    )


# --- Hide, last on purpose ----------------------------------------------------
#
# --- Nothing reaches the screen still encoded ---------------------------------

# A character reference: &#8217; &#x2019; &amp; and friends. Deliberately not a
# bare "&", which is ordinary in a headline (AT&T, Barnes & Noble).
HTML_ENTITY = re.compile(r"&(#\d+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]{1,10});")


def test_no_item_shows_a_raw_html_entity(page):
    """Caught by looking at a screenshot, not by any test that existed.

    The RSS adapter stripped tags from descriptions without decoding entities,
    so a TechCrunch summary rendered as "written.&#160;It&#8217;s&#160;a trend"
    on the board. Checking the rendered text covers every adapter and every
    display format at once, which is the right altitude for this: the bug is
    "encoded text reached a human", wherever it came from.
    """
    texts = page.locator(".content-item").all_inner_texts()
    assert texts, "no items on the board to check"

    offenders = [t for t in texts if HTML_ENTITY.search(t)]
    assert not offenders, (
        "these items are showing undecoded HTML entities: "
        f"{[HTML_ENTITY.search(t).group(0) + ' in ' + t[:70] for t in offenders[:3]]}"
    )


def test_the_entity_check_can_actually_fail():
    """Guards the guard, so a broken regex cannot pass everything silently."""
    assert HTML_ENTITY.search("written.&#160;It&#8217;s a trend")
    assert HTML_ENTITY.search("Fish &amp; chips")
    assert not HTML_ENTITY.search("AT&T and Barnes & Noble")
    assert not HTML_ENTITY.search("Perfectly ordinary headline")


# --- Display formats ----------------------------------------------------------
#
# Six formats are advertised and only one of them was ever opened. Each is its
# own branch in ContentPanel.renderItem, and the three dot menu is grafted onto
# whatever that branch returns by cloneElement, which works on a host element
# and silently does nothing on anything else. That is not a hypothetical: the
# gallery branch returns a component, so it genuinely gets no menu. Five formats
# were one refactor away from the same silent hole with no test to notice.

# label in the picker -> a selector that only that format produces
FORMAT_MARKERS = {
    "Compact": ".content-item",
    "Magazine": ".fmt-magazine",
    "Headlines": ".fmt-headlines",
    "Cards": ".fmt-card",
    "Gallery": ".gallery-item",
    "Text Only": ".fmt-text",
}

# Gallery is a bare image tile with nowhere to put a menu, and ContentPanel
# documents that exclusion. Every other format must carry one.
FORMATS_WITHOUT_A_MENU = {"Gallery"}


@pytest.fixture()
def formats_restored():
    """Put every source's display format back, whatever the test did to it.

    Format is persisted server side, so a failure midway through would other-
    wise leave the board in the last format tried and quietly change what every
    later test is looking at.
    """
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        before = {
            s["id"]: (s.get("display_format") or "compact")
            for s in client.get("/api/sources/").json()
        }
    yield
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        current = {
            s["id"]: (s.get("display_format") or "compact")
            for s in client.get("/api/sources/").json()
        }
        for source_id, fmt in before.items():
            # Only touch what actually changed. Patching a source reschedules
            # its fetch, and putting every source back after every format test
            # refetched the lot, which was enough on its own to get the Reddit
            # feed rate limited into an error state.
            if current.get(source_id, fmt) != fmt:
                client.patch(
                    f"/api/sources/{source_id}", json={"display_format": fmt}
                )


def choose_format(page, label):
    """Pick a display format the way a user does, through the gear menu."""
    panel = page.locator(".content-panel").first
    panel.locator(".btn-icon").first.click()
    page.wait_for_selector(".format-menu", timeout=10000)
    page.locator(
        f'.format-option:has(.format-label:text-is("{label}"))'
    ).first.click()


@pytest.mark.parametrize("label", list(FORMAT_MARKERS))
def test_every_display_format_renders_its_items(page, formats_restored, label):
    choose_format(page, label)
    panel = page.locator(".content-panel").first
    marker = FORMAT_MARKERS[label]
    panel.locator(marker).first.wait_for(state="visible", timeout=15000)
    assert panel.locator(marker).count() > 0, (
        f"the {label} format produced no items"
    )


@pytest.mark.parametrize(
    "label", [f for f in FORMAT_MARKERS if f not in FORMATS_WITHOUT_A_MENU]
)
def test_every_display_format_keeps_the_action_menu(page, formats_restored, label):
    choose_format(page, label)
    panel = page.locator(".content-panel").first
    panel.locator(FORMAT_MARKERS[label]).first.wait_for(
        state="visible", timeout=15000
    )
    assert panel.locator(".item-action-trigger").count() > 0, (
        f"the {label} format renders items with no action menu on them, so "
        f"bookmark, hide and mute are unreachable in that format"
    )


def test_the_gallery_exclusion_is_the_only_one(page, formats_restored):
    """Pins the documented exception so it cannot quietly spread.

    If a later change makes gallery carry a menu, this fails and the exclusion
    list above should lose an entry. That is the point.
    """
    choose_format(page, "Gallery")
    panel = page.locator(".content-panel").first
    panel.locator(".gallery-item").first.wait_for(state="visible", timeout=15000)
    assert panel.locator(".item-action-trigger").count() == 0


# --- OPML round trip ----------------------------------------------------------
#
# The backend has had working import and export endpoints, and tests for them,
# the whole time. The README advertised the feature. There was no way to reach
# it from the page, which makes the endpoints and their green tests worth
# nothing to anybody actually using this.


def test_opml_export_downloads_the_current_sources(page):
    with page.expect_download(timeout=30000) as download_info:
        page.get_by_role("link", name="Export").click()
    download = download_info.value

    target = Path(tempfile.gettempdir()) / f"opml-{uuid.uuid4().hex[:8]}.opml"
    download.save_as(target)
    try:
        root = ET.parse(target).getroot()
        assert root.tag == "opml"
        feeds = root.findall(".//outline[@xmlUrl]")
        assert feeds, "the export carried no feeds"
        assert all(f.get("xmlUrl") for f in feeds)
    finally:
        target.unlink(missing_ok=True)


def test_opml_import_adds_the_feeds_in_the_file(page):
    marker = uuid.uuid4().hex[:8]
    name = f"Imported {marker}"
    opml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<opml version="2.0"><head><title>t</title></head><body>'
        f'<outline text="{name}" title="{name}" type="rss" '
        f'xmlUrl="http://127.0.0.1:9/{marker}.xml" />'
        "</body></opml>"
    )
    path = Path(tempfile.gettempdir()) / f"import-{marker}.opml"
    path.write_text(opml, encoding="utf-8")

    try:
        page.set_input_files('input[type="file"]', str(path))
        # The status line is the only feedback the header gives, so it is also
        # the thing a user relies on to know the import worked. Wait for the
        # finished text, not merely for the element: it appears immediately
        # saying "Importing...", which is not an outcome.
        page.wait_for_selector(
            '.opml-status:has-text("Imported")', timeout=30000
        )
        status = page.locator(".opml-status").inner_text()
        assert "Imported 1" in status, f"import reported: {status!r}"

        with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
            names = [s["name"] for s in client.get("/api/sources/").json()]
        assert name in names, "the import reported success but created nothing"
    finally:
        path.unlink(missing_ok=True)
        # The imported feed points at a dead port on purpose, so it would sit
        # on the board as a permanently failing panel and break the "no panel
        # is in error" test for every later run.
        with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
            for source in client.get("/api/sources/").json():
                if source["name"] == name:
                    client.delete(f"/api/sources/{source['id']}")


def test_a_refused_add_says_why(page):
    """A rejected add used to leave the dialog open and silent.

    `addSource` acted only on success, so any refusal did nothing visible at
    all: the dialog stayed exactly as it was and the user had no way to tell
    whether the click had registered. Re-adding a feed already on the board is
    the ordinary way to reach it, and until now that was also a 500.
    """
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        existing = client.get("/api/sources/").json()
    assert existing, "no sources to duplicate"
    duplicate_url = existing[0]["url"]

    page.get_by_role("button", name="+ Add Source").click()
    page.wait_for_selector(".tab-bar", timeout=15000)
    page.get_by_role("button", name="Custom URL").click()
    page.locator('input[type="text"]').first.fill("A feed I already follow")
    page.locator('input[type="url"]').fill(duplicate_url)
    page.get_by_role("button", name="Add Source", exact=True).click()

    page.wait_for_selector(".add-source-error", timeout=20000)
    message = page.locator(".add-source-error").inner_text()
    assert "already exists" in message.lower(), f"unhelpful message: {message!r}"


# --- Live updates over the WebSocket ------------------------------------------
#
# CI proves the /ws route completes a handshake. That is the easy half. Nothing
# proved that a fetch actually reaches an open page, which is the whole promise
# of "updates in real time" and involves the scheduler, the broadcast, the
# client's onmessage and a refetch, any one of which can be broken alone.


@pytest.fixture()
def live_feed():
    """An RSS feed this test owns and can rewrite mid test.

    Served from a stdlib server on an ephemeral port, so it needs no fixture
    server, no network, and cannot collide with anything else running.
    """
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)

    def write(titles):
        items = "".join(
            f"<item><title>{t}</title>"
            f"<link>https://example.invalid/{i}</link>"
            f"<guid>https://example.invalid/{i}</guid>"
            f"<description>{t}</description></item>"
            for i, t in enumerate(titles)
        )
        (root / "feed.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<rss version="2.0"><channel><title>Live Feed</title>'
            "<link>https://example.invalid</link>"
            f"<description>live</description>{items}</channel></rss>",
            encoding="utf-8",
        )

    write(["Live feed first story", "Live feed second story"])

    httpd = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(root))
    )
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}/feed.xml", write
    finally:
        httpd.shutdown()
        httpd.server_close()
        tmp.cleanup()


def wait_for_items(client, source_id, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = client.get(f"/api/content/source/{source_id}", params={"limit": 50})
        if res.status_code == 200 and res.json():
            return res.json()
        time.sleep(1)
    pytest.fail(f"source {source_id} never produced any items")


def test_a_new_story_reaches_an_open_page_with_no_reload(browser, live_feed):
    feed_url, write = live_feed
    name = f"Live Feed {uuid.uuid4().hex[:6]}"

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        created = client.post(
            "/api/sources/",
            json={
                "name": name,
                "source_type": "rss",
                "url": feed_url,
                "refresh_seconds": 300,
            },
        )
        assert created.status_code in (200, 201), created.text
        source_id = created.json()["id"]

        try:
            wait_for_items(client, source_id)

            ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
            pg = ctx.new_page()
            try:
                pg.goto(BASE_URL, wait_until="networkidle", timeout=60000)
                pg.wait_for_selector(".content-panel", timeout=30000)
                pg.wait_for_selector('text="Live feed first story"', timeout=30000)

                headline = f"Breaking {uuid.uuid4().hex[:8]}"
                write(
                    [
                        "Live feed first story",
                        "Live feed second story",
                        headline,
                    ]
                )
                # A source only refetches on its own interval, and the shortest
                # allowed is well past any sane test timeout. Patching it
                # reschedules the job to run within seconds, which is the only
                # handle the API gives for "fetch this now".
                patched = client.patch(
                    f"/api/sources/{source_id}", json={"refresh_seconds": 301}
                )
                assert patched.status_code == 200, patched.text

                # No reload anywhere in this test. If the headline shows up, it
                # was pushed.
                pg.wait_for_selector(f'text="{headline}"', timeout=90000)
            finally:
                ctx.close()
        finally:
            client.delete(f"/api/sources/{source_id}")


# --- View keyword filters -----------------------------------------------------
#
# Views carry include and exclude keyword lists, applied server side when the
# tab's content is fetched. Backend tests cover the filtering. Nothing covered
# a user making a view and seeing a filtered board, which is the part that
# spans the tab bar, the fetch on tab change and the render.


@pytest.fixture()
def temp_view():
    created = []

    def make(**payload):
        with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
            res = client.post("/api/views/", json=payload)
            assert res.status_code in (200, 201), res.text
            view = res.json()
            created.append(view["id"])
            return view

    yield make

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        for view_id in created:
            client.delete(f"/api/views/{view_id}")


def pick_filter_word():
    """A word that is in some current headlines but not all of them.

    Hard coding a keyword would make the test depend on what happens to be in
    the news. Choosing from live titles keeps it honest, and requiring that it
    not match everything is what makes the assertion meaningful.
    """
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        sources = client.get("/api/sources/").json()
        source_ids = [s["id"] for s in sources]
        items = client.get("/api/content/", params={"limit": 100}).json()

    haystacks = [
        (i.get("title", "") + " " + (i.get("description") or "")).lower()
        for i in items
    ]
    if len(haystacks) < 4:
        pytest.skip("not enough content loaded to build a meaningful filter")

    for raw in haystacks[0].split():
        word = "".join(ch for ch in raw if ch.isalnum())
        if len(word) < 5:
            continue
        hits = sum(1 for h in haystacks if word in h)
        if 0 < hits < len(haystacks):
            return word, source_ids
    pytest.skip("no word in the current headlines separates the items")


def test_a_view_tab_shows_only_items_matching_its_include_filter(browser, temp_view):
    word, source_ids = pick_filter_word()
    view = temp_view(
        name=f"Include {uuid.uuid4().hex[:6]}",
        source_ids=source_ids,
        topic_filters=[word],
    )

    ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
    pg = ctx.new_page()
    try:
        pg.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        pg.locator(".view-tab", has_text=view["name"]).first.click()
        pg.wait_for_selector(".digest-item", timeout=30000)

        titles = pg.locator(".digest-item-title").all_inner_texts()
        assert titles, "the filtered view showed nothing at all"
        missing = [t for t in titles if word not in t.lower()]
        # The filter matches on description too, so a title alone need not
        # contain the word. Check the ones that do not against the API rather
        # than calling them failures.
        if missing:
            with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
                allowed = {
                    i.get("title", "")
                    for i in client.get(f"/api/content/view/{view['id']}").json()
                }
            unexpected = [t for t in missing if t not in allowed]
            assert not unexpected, (
                f"the view tab showed items the filter excludes: {unexpected[:3]}"
            )
    finally:
        ctx.close()


def test_a_view_tab_drops_items_matching_its_exclude_filter(browser, temp_view):
    word, source_ids = pick_filter_word()
    view = temp_view(
        name=f"Exclude {uuid.uuid4().hex[:6]}",
        source_ids=source_ids,
        exclude_keywords=[word],
    )

    ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
    pg = ctx.new_page()
    try:
        pg.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        pg.locator(".view-tab", has_text=view["name"]).first.click()
        pg.wait_for_selector(".digest-item", timeout=30000)

        titles = pg.locator(".digest-item-title").all_inner_texts()
        assert titles, "the exclude view emptied the board completely"
        offenders = [t for t in titles if word in t.lower()]
        assert not offenders, (
            f"the view tab kept items its exclude filter should have dropped: "
            f"{offenders[:3]}"
        )
    finally:
        ctx.close()


# --- Views, built the way a user builds them ----------------------------------
#
# Everything below was reached only through the API before. The editor modal
# itself had never been opened by a test, and it was sending include keywords
# under a field name the API does not have, so pydantic dropped them, answered
# 201, and every include filter a user typed was silently thrown away.


def open_view_editor(page):
    page.locator(".view-tab-add").click()
    page.wait_for_selector(".view-editor", timeout=15000)


def fill_view_editor(page, name, include=None, exclude=None, all_sources=True):
    page.locator('.view-editor input[placeholder="e.g. Morning Briefing"]').fill(name)
    if all_sources:
        boxes = page.locator('.view-editor .toggle-row input[type="checkbox"]')
        for i in range(boxes.count()):
            if not boxes.nth(i).is_checked():
                boxes.nth(i).check()
    for label, word in (("Include Keywords", include), ("Exclude Keywords", exclude)):
        if not word:
            continue
        field = page.locator(
            f'.view-editor .form-group:has(label:text-is("{label}")) '
            f'input[placeholder="Type and press Enter"]'
        )
        field.fill(word)
        field.press("Enter")


def test_a_view_built_in_the_editor_keeps_its_include_filter(page):
    word, _ = pick_filter_word()
    name = f"Editor {uuid.uuid4().hex[:6]}"

    open_view_editor(page)
    fill_view_editor(page, name, include=word)
    page.locator(".view-editor-footer .btn-primary").click()
    page.wait_for_selector(".view-editor", state="detached", timeout=20000)

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        views = client.get("/api/views/").json()
        made = [v for v in views if v["name"] == name]
        assert made, "the editor reported saving but no view was created"
        view = made[0]
        try:
            assert view["topic_filters"] == [word], (
                f"the include keyword never reached the server. Saved "
                f"topic_filters={view['topic_filters']!r}, expected [{word!r}]. "
                f"The editor used to send this as include_keywords, which is "
                f"not a field the API has, so it was dropped and the view "
                f"saved with no include filter at all."
            )
            # And it has to actually filter once you are looking at it.
            page.locator(".view-tab", has_text=name).first.click()
            page.wait_for_selector(".digest-item", timeout=30000)
            shown = page.locator(".digest-item-title").all_inner_texts()
            allowed = {
                i.get("title", "")
                for i in client.get(f"/api/content/view/{view['id']}").json()
            }
            assert shown, "the new view showed nothing at all"
            assert not [t for t in shown if t not in allowed]
        finally:
            client.delete(f"/api/views/{view['id']}")


def test_a_view_built_in_the_editor_keeps_its_exclude_filter(page):
    word, _ = pick_filter_word()
    name = f"Editor {uuid.uuid4().hex[:6]}"

    open_view_editor(page)
    fill_view_editor(page, name, exclude=word)
    page.locator(".view-editor-footer .btn-primary").click()
    page.wait_for_selector(".view-editor", state="detached", timeout=20000)

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        view = [v for v in client.get("/api/views/").json() if v["name"] == name][0]
        try:
            assert view["exclude_keywords"] == [word]
        finally:
            client.delete(f"/api/views/{view['id']}")


def test_an_existing_view_can_be_edited(page, temp_view):
    """The editor's whole Edit mode had no way in.

    `setEditingView` was only ever called with null, so a view could not be
    renamed, re-scoped, or have its keywords changed after it was made, and the
    prefilled editor that does all of that was dead code.
    """
    view = temp_view(
        name=f"Editable {uuid.uuid4().hex[:6]}",
        source_ids=[],
        topic_filters=["alpha"],
        exclude_keywords=["beta"],
    )
    page.reload(wait_until="networkidle")
    page.locator(".view-tab", has_text=view["name"]).first.click()
    page.locator(".view-tab-edit").first.click()
    page.wait_for_selector(".view-editor", timeout=15000)

    assert "Edit View" in page.locator(".view-editor-header").inner_text()
    chips = page.locator(".view-editor .keyword-chip").all_inner_texts()
    joined = " ".join(chips)
    assert "alpha" in joined, (
        f"the saved include keyword did not load into the editor: {chips!r}. "
        f"It read view.include_keywords, which the API never returns."
    )
    assert "beta" in joined

    renamed = f"{view['name']} renamed"
    page.locator('.view-editor input[placeholder="e.g. Morning Briefing"]').fill(renamed)
    page.locator(".view-editor-footer .btn-primary").click()
    page.wait_for_selector(".view-editor", state="detached", timeout=20000)

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        after = client.get(f"/api/views/{view['id']}").json()
    assert after["name"] == renamed
    assert after["topic_filters"] == ["alpha"], "editing wiped the include filter"


def test_a_view_can_be_deleted_from_the_editor(page):
    """A view made by accident used to be permanent.

    The delete endpoint existed and nothing in the interface called it.
    """
    name = f"Throwaway {uuid.uuid4().hex[:6]}"
    open_view_editor(page)
    fill_view_editor(page, name, all_sources=False)
    page.locator(".view-editor-footer .btn-primary").click()
    page.wait_for_selector(".view-editor", state="detached", timeout=20000)

    page.locator(".view-tab", has_text=name).first.click()
    page.locator(".view-tab-edit").first.click()
    page.wait_for_selector(".view-editor", timeout=15000)
    page.locator(".view-editor-footer .btn-danger").click()
    page.wait_for_selector(".view-editor", state="detached", timeout=20000)

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        names = [v["name"] for v in client.get("/api/views/").json()]
    assert name not in names, "delete closed the dialog but kept the view"


def test_view_tabs_reorder_by_dragging(page, temp_view):
    first = temp_view(name=f"AAA {uuid.uuid4().hex[:4]}", source_ids=[])
    second = temp_view(name=f"ZZZ {uuid.uuid4().hex[:4]}", source_ids=[])
    page.reload(wait_until="networkidle")

    tabs = lambda: [
        t for t in page.locator(".view-tab").all_inner_texts()
        if t.strip() in (first["name"], second["name"])
    ]
    before = tabs()
    assert before == [first["name"], second["name"]], f"unexpected start order: {before}"

    page.locator(".view-tab", has_text=second["name"]).first.drag_to(
        page.locator(".view-tab", has_text=first["name"]).first
    )
    page.wait_for_function(
        "names => Array.from(document.querySelectorAll('.view-tab'))"
        ".map(t => t.textContent.trim()).filter(t => names.includes(t))[0] === names[1]",
        arg=[first["name"], second["name"]],
        timeout=15000,
    )

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        order = [
            v["name"] for v in client.get("/api/views/").json()
            if v["name"] in (first["name"], second["name"])
        ]
    assert order == [second["name"], first["name"]], (
        f"the drag did not persist, server order is {order}"
    )


# --- Sources: mute, hide, restore, and the types on the tin --------------------


def test_muting_a_source_clears_the_board_and_the_manager_brings_it_back(page):
    """Mute is well covered against the API and had never been clicked."""
    panel = page.locator(".content-panel").first
    name = panel.locator(".panel-title").inner_text()
    before = page.locator(".content-panel").count()

    panel.locator(".content-item").first.locator(".item-action-trigger").click()
    page.wait_for_selector(".item-action-menu", timeout=10000)
    page.get_by_role("button", name="Mute source").click()
    page.get_by_role("button", name="24 hours").click()

    page.wait_for_function(
        "n => document.querySelectorAll('.content-panel').length === n - 1",
        arg=before, timeout=20000,
    )

    page.get_by_role("button", name="Muted").click()
    page.wait_for_selector(".muted-source-row", timeout=15000)
    row = page.locator(".muted-source-row", has_text=name).first
    assert row.count() > 0, f"{name} was muted but is not in the manager"
    row.get_by_role("button", name="Unmute").click()
    page.locator(".view-editor .btn-close").click()

    page.wait_for_function(
        "n => document.querySelectorAll('.content-panel').length === n",
        arg=before, timeout=20000,
    )


def test_a_hidden_source_comes_back_from_the_tray(page):
    panel = page.locator(".content-panel").first
    name = panel.locator(".panel-title").inner_text()
    before = page.locator(".content-panel").count()

    panel.locator('.btn-close[title="Hide panel"]').click()
    page.wait_for_function(
        "n => document.querySelectorAll('.content-panel').length === n - 1",
        arg=before, timeout=20000,
    )

    page.locator(".header-actions .btn", has_text="hidden").first.click()
    page.wait_for_selector(".hidden-tray", timeout=15000)
    tray_row = page.locator(".hidden-source", has_text=name).first
    assert tray_row.count() > 0, f"{name} was hidden but is not in the tray"
    tray_row.get_by_role("button", name="Show").click()

    page.wait_for_function(
        "n => document.querySelectorAll('.content-panel').length === n",
        arg=before, timeout=20000,
    )


def test_a_plain_web_page_can_be_added_as_a_source(page):
    """Generic pages are one of the four advertised source types.

    Detection had tests. Adding one and seeing it on the board did not.
    """
    name = f"Web Page {uuid.uuid4().hex[:6]}"
    page.get_by_role("button", name="+ Add Source").click()
    page.wait_for_selector(".tab-bar", timeout=15000)
    page.get_by_role("button", name="Custom URL").click()
    page.locator('input[placeholder="My Feed"]').fill(name)
    page.locator('.custom-form select').first.select_option("generic")
    page.locator('input[type="url"]').fill("https://example.com")
    page.get_by_role("button", name="Add Source", exact=True).click()

    try:
        page.wait_for_selector(f'.panel-title:text-is("{name}")', timeout=30000)
        panel = page.locator(".content-panel", has_text=name).first
        assert "Web" in panel.locator(".panel-badge").inner_text()
    finally:
        with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
            for source in client.get("/api/sources/").json():
                if source["name"] == name:
                    client.delete(f"/api/sources/{source['id']}")


# --- The rest of the panel controls -------------------------------------------


def test_the_custom_format_builder_applies(page, formats_restored):
    panel = page.locator(".content-panel").first
    panel.locator(".btn-icon").first.click()
    page.wait_for_selector(".format-menu", timeout=10000)
    page.locator('.format-option:has(.format-label:text-is("Custom"))').click()
    page.wait_for_selector(".custom-builder", timeout=10000)

    # Turn the description off, which is the most visible of the toggles.
    # Click the label rather than the input: the input sits inside a scrolling
    # menu and is not reliably actionable on its own, and a label click is what
    # a person does anyway.
    toggle = page.locator('.custom-builder .toggle-row', has_text="Description").first
    toggle.scroll_into_view_if_needed()
    toggle.locator("span").click()
    assert not toggle.locator('input[type="checkbox"]').is_checked()
    page.get_by_role("button", name="Apply Custom").click()

    page.wait_for_selector(".format-menu", state="detached", timeout=10000)
    panel.locator(".content-item").first.wait_for(state="visible", timeout=15000)
    assert panel.locator(".item-description").count() == 0, (
        "the custom builder said it applied and the descriptions are still there"
    )


def test_a_resized_panel_keeps_its_size_across_a_reload(page):
    grid_item = page.locator(".dashboard-grid .react-grid-item").first
    before = grid_item.bounding_box()

    handle = grid_item.locator(".react-resizable-handle").first
    handle.hover()
    page.mouse.down()
    page.mouse.move(before["x"] + before["width"] + 40,
                    before["y"] + before["height"] + 120, steps=12)
    page.mouse.up()

    page.wait_for_function(
        "h => document.querySelector('.dashboard-grid .react-grid-item')"
        ".getBoundingClientRect().height > h + 20",
        arg=before["height"], timeout=15000,
    )
    grown = grid_item.bounding_box()["height"]

    page.reload(wait_until="networkidle")
    page.wait_for_selector(".content-panel", timeout=30000)
    page.wait_for_timeout(1500)
    after = page.locator(".dashboard-grid .react-grid-item").first.bounding_box()["height"]
    assert after > before["height"] + 20, (
        f"the resize did not survive a reload: {before['height']} -> {grown} -> {after}"
    )


def test_the_search_tab_finds_something_to_add(page):
    page.get_by_role("button", name="+ Add Source").click()
    page.wait_for_selector(".tab-bar", timeout=15000)
    page.get_by_role("button", name="Search").click()
    box = page.locator('input[placeholder^="Search sources"]')
    box.fill("python")
    box.press("Enter")
    page.wait_for_selector(".source-card", timeout=30000)
    assert page.locator(".source-card").count() > 0


# Hiding is the one action here with no undo. There is no unhide endpoint, so
# every run of this permanently removes an item from the pool that the digest
# and the panels above draw on. Running it last keeps it from starving the
# tests that need content on screen.


def test_hiding_an_item_removes_it_from_the_panel(page):
    """Scoped to one panel deliberately.

    Hiding acts on a content item id, so two sources carrying the same feed each
    hold their own copy of an article and only the one acted on disappears.
    Asserting on the headline text alone would call that a failure.
    """
    panel = page.locator(".content-panel").first
    before = panel.locator(".content-item").count()
    if before < 2:
        # Hiding has no undo, so each local run permanently shrinks the pool.
        # CI starts from an empty database and always has items here.
        pytest.skip("not enough items left in this database to hide one")

    panel.locator(".content-item").first.locator(".item-action-trigger").click()
    page.wait_for_selector(".item-action-menu", timeout=10000)
    page.get_by_role("button", name="Hide this item").click()

    page.wait_for_function(
        "n => document.querySelector('.content-panel')"
        ".querySelectorAll('.content-item').length === n - 1",
        arg=before,
        timeout=15000,
    )


# --- First run ----------------------------------------------------------------
#
# Last on purpose. The topic picker only appears on an empty board, so this is
# the one test that has to clear the sources out and put them back, and doing
# that mid file would pull the content out from under everything above.
#
# It earns the disruption: this screen is the first thing anybody who clones
# the repository sees, and nothing had ever opened it.


@pytest.fixture()
def emptied_board():
    """Take every source away, then put them all back afterwards.

    Gated behind an environment variable because it is the only test here that
    touches every source at once. CI runs against a throwaway database and sets
    it; a person running this against the instance they actually read would
    otherwise have their board emptied and rebuilt underneath them, losing the
    fetched articles even though the sources come back.
    """
    if not os.getenv("AGGREGATOR_E2E_DESTRUCTIVE"):
        pytest.skip(
            "needs AGGREGATOR_E2E_DESTRUCTIVE=1, it empties and rebuilds the board"
        )

    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        saved = [
            {
                "name": s["name"],
                "source_type": s["source_type"],
                "url": s["url"],
                "refresh_seconds": s["refresh_seconds"],
                "display_format": s.get("display_format") or "compact",
                "category": s.get("category") or "General",
            }
            for s in client.get("/api/sources/").json()
        ]
        for source in client.get("/api/sources/").json():
            client.delete(f"/api/sources/{source['id']}")

    yield

    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        for source in client.get("/api/sources/").json():
            client.delete(f"/api/sources/{source['id']}")
        for payload in saved:
            client.post("/api/sources/", json=payload)


def test_the_first_run_screen_offers_topics_and_builds_a_board(browser, emptied_board):
    ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto(BASE_URL, wait_until="networkidle", timeout=60000)

        # An empty board goes straight to the picker rather than to a welcome
        # screen with a button on it.
        pg.wait_for_selector(".onboarding-overlay", timeout=30000)
        assert pg.locator(".onboarding-topic").count() > 0, (
            "the topic picker opened with nothing to pick"
        )

        # Every topic must offer something. A topic whose sources were all
        # removed would sit there looking clickable and add nothing.
        counts = pg.locator(".onboarding-topic-count").all_inner_texts()
        empty = [c for c in counts if c.strip().startswith("0 ")]
        assert not empty, f"topics offering no sources: {empty}"

        pg.locator(".onboarding-topic").first.click()
        cta = pg.get_by_role("button", name="Get Started")
        assert cta.is_enabled(), "a topic is selected and Get Started is still disabled"
        cta.click()

        pg.wait_for_selector(".content-panel", timeout=60000)
        assert pg.locator(".content-panel").count() > 0

        with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
            assert client.get("/api/sources/").json(), (
                "the picker finished but created no sources"
            )
    finally:
        assert not errors, f"uncaught JavaScript errors: {errors}"
        ctx.close()
