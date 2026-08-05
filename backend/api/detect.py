"""API routes for URL auto-detection."""

import re
from urllib.parse import urljoin

from fastapi import APIRouter, HTTPException
import aiohttp
import feedparser
from bs4 import BeautifulSoup

from backend.config import REQUEST_TIMEOUT, logger
from backend.models import DetectRequest

router = APIRouter(prefix="/api/detect", tags=["detect"])

# The separating slash matters. Without it "youtube.com/user/name" matched
# nothing, because "user" is not followed by a word character, while
# "youtube.com/channel/UC..." matched only by accident through the bare "c"
# alternative consuming "hannel". A /user/ channel was therefore detected as a
# plain RSS feed, by way of the feed link on its page, rather than as YouTube.
YOUTUBE_PATTERNS = [
    r'youtube\.com/(?:channel/|c/|user/|@)[\w-]+',
    r'youtube\.com/feeds/videos\.xml\?channel_id=[\w-]+',
    r'youtube\.com/watch\?v=[\w-]+',
    r'youtu\.be/[\w-]+',
]

REDDIT_PATTERN = r'reddit\.com/r/([\w]+)'


@router.post("/url")
async def detect_source_url(data: DetectRequest):
    """Detect source type from URL and return preview items."""
    url = data.url.strip()

    # YouTube detection
    for pattern in YOUTUBE_PATTERNS:
        if re.search(pattern, url):
            return await _detect_youtube(url)

    # Reddit detection
    reddit_match = re.search(REDDIT_PATTERN, url)
    if reddit_match:
        return await _detect_reddit(url, reddit_match.group(1))

    # The URL might already be a feed. This is the ordinary case when someone
    # copies a feed address out of another reader, and it used to fall all the
    # way through to "generic" unless the address happened to end in something
    # like /feed. https://hnrss.org/frontpage is a real feed and was detected
    # as a web page.
    if await _is_feed(url):
        return await _detect_rss(url, url)

    # Otherwise look for a feed advertised by, or sitting next to, an HTML page
    rss_url = await _discover_rss(url)
    if rss_url:
        return await _detect_rss(rss_url, url)

    # Fallback to generic
    return await _detect_generic(url)


async def _is_feed(url) -> bool:
    """True when the URL itself serves a parseable feed with entries."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                headers={"User-Agent": "AwesomeAggregator/0.1"},
            ) as resp:
                if resp.status != 200:
                    return False
                body = await resp.text()
    except Exception:
        return False

    parsed = feedparser.parse(body)
    # feedparser is happy to "parse" an HTML page into an empty feed, so the
    # entries are what actually decide this.
    return bool(parsed.entries)


async def _detect_youtube(url):
    from backend.sources.youtube import YouTubeSource
    try:
        source = YouTubeSource(url)
        items = await source.fetch()
        preview = [
            {"title": i.title, "url": i.url, "image_url": i.image_url, "published_at": i.published_at}
            for i in items[:3]
        ]
        return {"source_type": "youtube", "name": source.get_display_name(), "url": url, "preview_items": preview}
    except Exception as e:
        return {"source_type": "youtube", "name": "YouTube Channel", "url": url, "preview_items": [], "error": str(e)}


async def _detect_reddit(url, subreddit):
    from backend.sources.reddit import RedditSource
    reddit_url = f"https://www.reddit.com/r/{subreddit}"
    try:
        source = RedditSource(reddit_url)
        items = await source.fetch()
        preview = [
            {"title": i.title, "url": i.url, "published_at": i.published_at, "metadata": i.metadata}
            for i in items[:3]
        ]
        return {"source_type": "reddit", "name": f"r/{subreddit}", "url": reddit_url, "preview_items": preview}
    except Exception as e:
        return {"source_type": "reddit", "name": f"r/{subreddit}", "url": reddit_url, "preview_items": [], "error": str(e)}


async def _discover_rss(url):
    """Try to discover RSS feed URL from an HTML page."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10),
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")

        # Check for RSS/Atom link tags
        for link in soup.find_all("link", rel="alternate"):
            link_type = link.get("type", "")
            if "rss" in link_type or "atom" in link_type or "xml" in link_type:
                href = link.get("href", "")
                if href:
                    if href.startswith("/"):
                        href = urljoin(url, href)
                    return href

        # Try common feed paths
        common_paths = ["/feed", "/rss", "/feed.xml", "/rss.xml", "/atom.xml", "/index.xml"]
        async with aiohttp.ClientSession() as session:
            for path in common_paths:
                feed_url = urljoin(url, path)
                try:
                    async with session.head(
                        feed_url,
                        timeout=aiohttp.ClientTimeout(total=5),
                        headers=headers,
                        allow_redirects=True,
                    ) as resp:
                        if resp.status == 200:
                            ct = resp.headers.get("content-type", "")
                            if "xml" in ct or "rss" in ct or "atom" in ct:
                                return feed_url
                except Exception:
                    continue
    except Exception:
        pass
    return None


async def _detect_rss(rss_url, original_url):
    from backend.sources.rss import RSSSource
    try:
        source = RSSSource(rss_url)
        items = await source.fetch()
        preview = [
            {"title": i.title, "url": i.url, "image_url": i.image_url, "published_at": i.published_at}
            for i in items[:3]
        ]
        name = source.get_display_name()
        return {"source_type": "rss", "name": name, "url": rss_url, "preview_items": preview}
    except Exception as e:
        return {"source_type": "rss", "name": "RSS Feed", "url": rss_url, "preview_items": [], "error": str(e)}


async def _detect_generic(url):
    from backend.sources.generic import GenericSource
    try:
        source = GenericSource(url)
        items = await source.fetch()
        preview = [
            {"title": i.title, "url": i.url, "image_url": i.image_url}
            for i in items[:3]
        ]
        return {"source_type": "generic", "name": url.split("/")[2] if "/" in url else url, "url": url, "preview_items": preview}
    except Exception as e:
        return {"source_type": "generic", "name": "Website", "url": url, "preview_items": [], "error": str(e)}
