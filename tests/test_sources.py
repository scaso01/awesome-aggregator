"""Tests for content source adapters."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.sources.rss import RSSSource
from backend.sources.youtube import YouTubeSource
from backend.sources.reddit import RedditSource
from backend.sources.base import SourceFetchError
from backend.sources import create_source_adapter, get_available_types


# --- Source Registry Tests ---


def test_available_types():
    """Should return all registered source types."""
    types = get_available_types()
    assert "rss" in types
    assert "youtube" in types
    assert "reddit" in types


def test_create_rss_adapter():
    """Should create an RSS adapter."""
    adapter = create_source_adapter("rss", "https://example.com/feed.xml")
    assert isinstance(adapter, RSSSource)
    assert adapter.url == "https://example.com/feed.xml"


def test_create_youtube_adapter():
    """Should create a YouTube adapter."""
    adapter = create_source_adapter("youtube", "https://www.youtube.com/channel/UCtest123")
    assert isinstance(adapter, YouTubeSource)


def test_create_reddit_adapter():
    """Should create a Reddit adapter."""
    adapter = create_source_adapter("reddit", "https://www.reddit.com/r/technology")
    assert isinstance(adapter, RedditSource)


def test_create_unknown_type():
    """Should raise ValueError for unknown source type."""
    with pytest.raises(ValueError, match="Unknown source type"):
        create_source_adapter("tiktok", "https://tiktok.com/@user")


# --- RSS Source Tests ---


class TestRSSSource:

    def test_source_type(self):
        source = RSSSource(url="https://example.com/feed.xml")
        assert source.get_source_type() == "rss"

    def test_clean_description_strips_html(self):
        html = "<p>Hello <strong>world</strong></p>"
        result = RSSSource._clean_description(html)
        assert result == "Hello world"

    def test_clean_description_truncates(self):
        long_text = "x" * 1000
        result = RSSSource._clean_description(long_text)
        assert len(result) == 500

    def test_clean_description_empty(self):
        assert RSSSource._clean_description("") == ""

    def test_clean_description_decodes_character_references(self):
        """Straight from a TechCrunch summary that shipped in a screenshot.

        Stripping tags without decoding entities put "&#8217;" and "&#160;" on
        screen as literal text in the middle of a sentence. The Reddit adapter
        decoded all along, so this was one adapter out of step.
        """
        raw = "written.&#160;It&#8217;s&#160;a trend that&#8217;s been building"
        result = RSSSource._clean_description(raw)
        # &#8217; is a right single quotation mark, not an ASCII apostrophe.
        assert result == "written. It’s a trend that’s been building"
        assert "&#" not in result

    def test_clean_description_decodes_named_entities(self):
        result = RSSSource._clean_description("<p>Fish &amp; chips &mdash; cheap</p>")
        assert result == "Fish & chips — cheap"

    def test_clean_description_folds_a_non_breaking_space(self):
        """&#160; has to end up as an ordinary space, not a stray \\xa0."""
        result = RSSSource._clean_description("one&#160;&#160;two")
        assert result == "one two"
        assert "\xa0" not in result


# --- YouTube Source Tests ---


class TestYouTubeSource:

    def test_source_type(self):
        source = YouTubeSource(url="https://www.youtube.com/channel/UCtest")
        assert source.get_source_type() == "youtube"

    def test_extract_channel_id_from_url(self):
        cid = YouTubeSource._extract_channel_id(
            "https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx"
        )
        assert cid == "UCxxxxxxxxxxxxxxxxxxxxxx"

    def test_extract_channel_id_from_feed_url(self):
        cid = YouTubeSource._extract_channel_id(
            "https://www.youtube.com/feeds/videos.xml?channel_id=UCtest123"
        )
        assert cid == "UCtest123"

    def test_extract_channel_id_raw(self):
        cid = YouTubeSource._extract_channel_id("UCxxxxxxxxxxxxxxxxxxxxxx")
        assert cid == "UCxxxxxxxxxxxxxxxxxxxxxx"

    def test_extract_channel_id_invalid(self):
        cid = YouTubeSource._extract_channel_id("not-a-youtube-url")
        assert cid is None

    def test_feed_url_construction(self):
        source = YouTubeSource(url="https://www.youtube.com/channel/UCtest123")
        assert "channel_id=UCtest123" in source.feed_url


# --- Reddit Source Tests ---


class TestRedditSource:
    """Adapter identity only.

    Reddit dropped its unauthenticated .json API, so the adapter now parses the
    subreddit Atom feed. Everything about that parse, including image and author
    extraction, is covered in tests/test_reddit_source.py against a real
    captured feed. The dict-shaped image tests that used to live here described
    the .json payload and no longer had anything to run against.
    """

    def test_source_type(self):
        source = RedditSource(url="https://www.reddit.com/r/technology")
        assert source.get_source_type() == "reddit"

    def test_extract_subreddit_from_url(self):
        sub = RedditSource._extract_subreddit("https://www.reddit.com/r/technology")
        assert sub == "technology"

    def test_extract_subreddit_from_name(self):
        sub = RedditSource._extract_subreddit("technology")
        assert sub == "technology"
