"""Reddit adapter tests, run against a real captured subreddit Atom feed.

`tests/fixtures/reddit_technology.atom.xml` is genuine output from
https://www.reddit.com/r/technology/hot/.rss, trimmed to four entries and
otherwise untouched. Parsing hand written XML that happens to match the parser
would prove nothing, which is the whole reason the fixture is real.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from backend.sources.reddit import RedditSource

FIXTURE = Path(__file__).parent / "fixtures" / "reddit_technology.atom.xml"


@pytest.fixture()
def feed_xml() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture()
def source() -> RedditSource:
    return RedditSource(url="https://www.reddit.com/r/technology")


async def fetch_with(source: RedditSource, body: str):
    """Run fetch() with the network replaced by a fixed response body."""
    class _Response:
        status = 200

        def raise_for_status(self):
            return None

        async def text(self):
            return body

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    class _Session:
        def get(self, *args, **kwargs):
            return _Response()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    with patch("backend.sources.reddit.aiohttp.ClientSession", lambda *a, **k: _Session()):
        return await source.fetch()


# --- URL construction ---------------------------------------------------------


def test_uses_the_atom_feed(source):
    assert source.feed_url == "https://www.reddit.com/r/technology/hot/.rss?limit=50"


def test_does_not_use_the_blocked_json_endpoints(source):
    """Regression guard for the bug that killed every Reddit panel.

    www.reddit.com/r/<sub>/hot.json returns 403 to unauthenticated clients and
    api.reddit.com blocks after the first request from an IP. Reaching for
    either again would silently break Reddit sources for every user.
    """
    assert ".json" not in source.feed_url
    assert "api.reddit.com" not in source.feed_url


@pytest.mark.parametrize("url,expected", [
    ("https://www.reddit.com/r/technology", "technology"),
    ("https://reddit.com/r/MachineLearning", "MachineLearning"),
    ("https://www.reddit.com/r/python/", "python"),
    ("technology", "technology"),
])
def test_extracts_subreddit(url, expected):
    assert RedditSource._extract_subreddit(url) == expected


# --- Parsing the real feed ----------------------------------------------------


@pytest.mark.asyncio
async def test_parses_every_entry(source, feed_xml):
    items = await fetch_with(source, feed_xml)
    assert len(items) == 4


@pytest.mark.asyncio
async def test_titles_and_permalinks(source, feed_xml):
    items = await fetch_with(source, feed_xml)
    for item in items:
        assert item.title and item.title != "Untitled"
        assert item.url.startswith("https://www.reddit.com/r/technology/comments/")


@pytest.mark.asyncio
async def test_author_has_the_u_prefix_stripped(source, feed_xml):
    items = await fetch_with(source, feed_xml)
    authors = [i.author for i in items]
    assert all(a for a in authors), "every post has an author"
    assert not any(a.startswith("/u/") for a in authors)


@pytest.mark.asyncio
async def test_published_dates_are_present(source, feed_xml):
    items = await fetch_with(source, feed_xml)
    assert all(i.published_at for i in items)
    assert all(i.published_at.startswith("20") for i in items)


@pytest.mark.asyncio
async def test_preview_images_are_extracted(source, feed_xml):
    items = await fetch_with(source, feed_xml)
    images = [i.image_url for i in items if i.image_url]
    assert images, "the fixture posts all carry a media:thumbnail"
    assert all(u.startswith("http") for u in images)


@pytest.mark.asyncio
async def test_external_link_is_captured(source, feed_xml):
    """Link posts point somewhere. That target is what a reader wants."""
    items = await fetch_with(source, feed_xml)
    externals = [i.metadata.get("external_url") for i in items]
    found = [u for u in externals if u]
    assert found, "at least one fixture post is a link post"
    assert all(u.startswith("http") for u in found)
    assert all("[link]" not in u for u in found)


@pytest.mark.asyncio
async def test_description_drops_reddit_boilerplate(source, feed_xml):
    """A link post's body is only the submission table, so it should be empty.

    Leaving it in put "submitted by /u/someone [link] [comments]" under every
    single headline in the panel.
    """
    items = await fetch_with(source, feed_xml)
    for item in items:
        assert "submitted by" not in item.description
        assert "[link]" not in item.description
        assert "[comments]" not in item.description
        assert "<" not in item.description, "markup should be stripped"


@pytest.mark.asyncio
async def test_no_fabricated_engagement_numbers(source, feed_xml):
    """The Atom feed has no scores, so the keys must be absent, not zero.

    The panel renders a score whenever the key exists, so a zero would show a
    confident "0 pts" on every Reddit post in the dashboard.
    """
    items = await fetch_with(source, feed_xml)
    for item in items:
        assert "score" not in item.metadata
        assert "num_comments" not in item.metadata


@pytest.mark.asyncio
async def test_metadata_identifies_the_subreddit(source, feed_xml):
    items = await fetch_with(source, feed_xml)
    assert all(i.metadata["subreddit"] == "technology" for i in items)
    assert all(i.metadata["post_id"] for i in items)


def test_source_type_and_display_name(source):
    assert source.get_source_type() == "reddit"
    assert source.get_display_name() == "r/technology"
