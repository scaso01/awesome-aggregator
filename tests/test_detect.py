"""Tests for URL auto-detection logic.

Tests the URL pattern matching for identifying source types
(YouTube, Reddit, RSS) from URLs without making real HTTP calls.
"""

import pytest
import re


# URL detection patterns matching the backend logic
YOUTUBE_PATTERNS = [
    re.compile(r"youtube\.com/(channel|c|user)/[\w-]+", re.IGNORECASE),
    re.compile(r"youtube\.com/@[\w-]+", re.IGNORECASE),
    re.compile(r"youtube\.com/watch\?v=", re.IGNORECASE),
    re.compile(r"youtu\.be/", re.IGNORECASE),
]

REDDIT_PATTERN = re.compile(r"reddit\.com/r/(\w+)", re.IGNORECASE)

RSS_EXTENSIONS = [".xml", ".rss", ".atom", "/feed", "/rss"]


def detect_source_type(url: str) -> str:
    """Detect source type from URL pattern."""
    for pattern in YOUTUBE_PATTERNS:
        if pattern.search(url):
            return "youtube"
    if REDDIT_PATTERN.search(url):
        return "reddit"
    for ext in RSS_EXTENSIONS:
        if ext in url.lower():
            return "rss"
    return "generic"


def extract_reddit_subreddit(url: str) -> str:
    """Extract subreddit name from a Reddit URL."""
    match = REDDIT_PATTERN.search(url)
    return match.group(1) if match else None


def test_detect_youtube_channel_url():
    """YouTube channel URL should be detected as youtube type."""
    assert detect_source_type("https://www.youtube.com/c/mkbhd") == "youtube"


def test_detect_youtube_channel_at_url():
    """YouTube @handle URL should be detected as youtube type."""
    assert detect_source_type("https://www.youtube.com/@Fireship") == "youtube"


def test_detect_youtube_channel_full():
    """YouTube /channel/ URL should be detected as youtube type."""
    assert detect_source_type("https://www.youtube.com/channel/UCsBjURrPoezykLs9EqgamOA") == "youtube"


def test_detect_youtube_user_url():
    """YouTube /user/ URL should be detected as youtube type."""
    assert detect_source_type("https://www.youtube.com/user/marquesbrownlee") == "youtube"


def test_detect_youtube_video_url():
    """YouTube watch URL should be detected as youtube type."""
    assert detect_source_type("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"


def test_detect_youtube_short_url():
    """Short youtu.be URL should be detected as youtube type."""
    assert detect_source_type("https://youtu.be/dQw4w9WgXcQ") == "youtube"


def test_detect_reddit_url():
    """Reddit subreddit URL should be detected as reddit type."""
    assert detect_source_type("https://www.reddit.com/r/python") == "reddit"


def test_detect_reddit_without_www():
    """Reddit URL without www should still be detected."""
    assert detect_source_type("https://reddit.com/r/technology") == "reddit"


def test_detect_reddit_subreddit_extraction():
    """Subreddit name should be extracted from the URL."""
    assert extract_reddit_subreddit("https://www.reddit.com/r/python") == "python"
    assert extract_reddit_subreddit("https://reddit.com/r/MachineLearning") == "MachineLearning"


def test_detect_rss_feed_url():
    """URL with /feed path should be detected as rss type."""
    assert detect_source_type("https://techcrunch.com/feed/") == "rss"


def test_detect_rss_xml_extension():
    """URL with .xml extension should be detected as rss type."""
    assert detect_source_type("https://example.com/news.xml") == "rss"


def test_detect_rss_atom_extension():
    """URL with .atom extension should be detected as rss type."""
    assert detect_source_type("https://example.com/feed.atom") == "rss"


def test_detect_generic_url():
    """URL with no recognizable pattern should be detected as generic."""
    assert detect_source_type("https://example.com/article/123") == "generic"


def test_detect_invalid_url():
    """Non-matching URL should fall back to generic."""
    assert detect_source_type("https://some-random-site.com") == "generic"
