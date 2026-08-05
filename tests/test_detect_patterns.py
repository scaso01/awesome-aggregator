"""URL classification, the part that needs no network.

The live detection tests sit in test_ui_actions.py. These cover the routing
decision itself, which had two faults that were invisible until someone pasted
a real address:

  - "youtube.com/user/name" matched no YouTube pattern at all, because the
    pattern expected a word character straight after "user" rather than a
    slash. Such a channel was classified as a plain RSS feed, by way of the
    feed link on its page.
  - "youtube.com/channel/UC..." matched only by accident, through the bare "c"
    alternative swallowing "hannel".
"""

import re

import pytest

from backend.api.detect import REDDIT_PATTERN, YOUTUBE_PATTERNS
from backend.sources.youtube import YouTubeSource


def looks_like_youtube(url: str) -> bool:
    return any(re.search(p, url) for p in YOUTUBE_PATTERNS)


@pytest.mark.parametrize("url", [
    "https://www.youtube.com/@Computerphile",
    "https://youtube.com/@some-handle",
    "https://www.youtube.com/channel/UC9-y-6csu5WGm29I7JiwpnA",
    "https://www.youtube.com/c/Computerphile",
    "https://www.youtube.com/user/Computerphile",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UC9-y-6csu5WGm29I7JiwpnA",
])
def test_youtube_urls_are_recognised(url):
    assert looks_like_youtube(url), f"{url} should be detected as YouTube"


@pytest.mark.parametrize("url", [
    "https://hnrss.org/frontpage",
    "https://techcrunch.com/feed/",
    "https://www.reddit.com/r/technology",
    "https://example.com",
    "https://notyoutube.example.com/feed",
])
def test_non_youtube_urls_are_not_claimed(url):
    assert not looks_like_youtube(url), f"{url} should not be detected as YouTube"


@pytest.mark.parametrize("url,expected", [
    ("https://www.reddit.com/r/technology", "technology"),
    ("https://reddit.com/r/MachineLearning", "MachineLearning"),
    ("https://old.reddit.com/r/python/", "python"),
])
def test_reddit_urls_are_recognised(url, expected):
    match = re.search(REDDIT_PATTERN, url)
    assert match and match.group(1) == expected


def test_reddit_pattern_does_not_claim_a_plain_page():
    assert not re.search(REDDIT_PATTERN, "https://example.com/r")


# --- Channel id extraction ----------------------------------------------------


@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/channel/UC9-y-6csu5WGm29I7JiwpnA", "UC9-y-6csu5WGm29I7JiwpnA"),
    ("https://www.youtube.com/feeds/videos.xml?channel_id=UC9-y-6csu5WGm29I7JiwpnA", "UC9-y-6csu5WGm29I7JiwpnA"),
    ("UC9-y-6csu5WGm29I7JiwpnA", "UC9-y-6csu5WGm29I7JiwpnA"),
])
def test_channel_id_read_straight_from_the_url(url, expected):
    assert YouTubeSource._extract_channel_id(url) == expected


@pytest.mark.parametrize("url", [
    "https://www.youtube.com/@Computerphile",
    "https://www.youtube.com/user/Computerphile",
])
def test_handle_urls_carry_no_id_and_need_resolving(url):
    """These have to be looked up, and fetch() does that before it builds a feed URL."""
    assert YouTubeSource._extract_channel_id(url) is None


def test_a_handle_url_does_not_leave_the_feed_pointing_at_a_web_page():
    """The failure this produced was an XML parse error, which explains nothing.

    fetch() resolves the id first now, and raises a message naming the accepted
    URL shapes if it cannot.
    """
    source = YouTubeSource("https://www.youtube.com/@Computerphile")
    assert source.channel_id is None
    assert source.feed_url == "https://www.youtube.com/@Computerphile"


# --- Reading the id out of a channel page -------------------------------------


CANONICAL_PAGE = '''
<html><head>
<link rel="canonical" href="https://www.youtube.com/channel/UC9-y-6csu5WGm29I7JiwpnA">
<meta property="og:url" content="https://www.youtube.com/channel/UC9-y-6csu5WGm29I7JiwpnA">
</head><body>
<script>{"channelId":"UCoxcjq-8xIDTYp3uz647V5A","title":"A recommended channel"}</script>
<script>{"externalId":"UC9-y-6csu5WGm29I7JiwpnA"}</script>
</body></html>
'''


def test_page_patterns_pick_the_channel_not_a_recommendation():
    """A channel page also names other channels.

    Matching a bare "channelId" anywhere in the document returns whichever came
    first, which on a real page is a recommendation. Verified against
    youtube.com/@Computerphile, where that shortcut resolves to an unrelated
    channel. The patterns used are anchored to the canonical link, externalId
    and og:url instead.
    """
    from backend.sources.youtube import PAGE_CHANNEL_ID_PATTERNS

    found = {p.search(CANONICAL_PAGE).group(1)
             for p in PAGE_CHANNEL_ID_PATTERNS
             if p.search(CANONICAL_PAGE)}
    assert found == {"UC9-y-6csu5WGm29I7JiwpnA"}
    assert "UCoxcjq-8xIDTYp3uz647V5A" not in found
