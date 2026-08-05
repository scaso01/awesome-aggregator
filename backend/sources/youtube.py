"""YouTube channel source adapter using RSS feeds (no API key needed)."""

import re
from datetime import datetime

import aiohttp
import feedparser

from backend.config import REQUEST_TIMEOUT, logger
from backend.sources.base import BaseSource, ContentItem, SourceFetchError

# YouTube RSS feed URL template
YT_RSS_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

# Regex to extract channel ID from various YouTube URL formats
CHANNEL_ID_PATTERNS = [
    re.compile(r"channel_id=([A-Za-z0-9_-]+)"),
    re.compile(r"youtube\.com/channel/([A-Za-z0-9_-]+)"),
    re.compile(r"youtube\.com/feeds/videos\.xml\?channel_id=([A-Za-z0-9_-]+)"),
]

# A channel page carries its own id in several places. These two agree with each
# other and with the RSS link on the page.
#
# Deliberately NOT matching a bare "channelId":"UC..." anywhere in the document:
# a channel page also mentions the ids of recommended channels, and that pattern
# picks up the wrong one. Measured against youtube.com/@Computerphile, where it
# returns a completely different channel.
PAGE_CHANNEL_ID_PATTERNS = [
    re.compile(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[A-Za-z0-9_-]{22})"'),
    re.compile(r'"externalId":"(UC[A-Za-z0-9_-]{22})"'),
    re.compile(r'<meta property="og:url" content="https://www\.youtube\.com/channel/(UC[A-Za-z0-9_-]{22})"'),
]


class YouTubeSource(BaseSource):
    """Fetches latest videos from a YouTube channel via RSS (free, no API key)."""

    def __init__(self, url: str, **kwargs):
        super().__init__(url, **kwargs)
        self.channel_id = self._extract_channel_id(url)
        self.feed_url = YT_RSS_TEMPLATE.format(channel_id=self.channel_id) if self.channel_id else url

    async def fetch(self) -> list[ContentItem]:
        """Fetch latest videos from the YouTube channel RSS feed."""
        # A handle URL carries no channel id, and YouTube's RSS endpoint only
        # takes ids. Without this the feed URL stayed pointed at the channel's
        # HTML page, which fails as "not well-formed (invalid token)" and tells
        # the user nothing. Handles are how channels are shared now, so this is
        # the common case rather than an edge one.
        if not self.channel_id:
            self.channel_id = await self._resolve_channel_id(self.url)
            if not self.channel_id:
                raise SourceFetchError(
                    "Could not find a channel id for this YouTube URL. Use the "
                    "channel address, for example youtube.com/@handle or "
                    "youtube.com/channel/UC...",
                    source_url=self.url,
                )
            self.feed_url = YT_RSS_TEMPLATE.format(channel_id=self.channel_id)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.feed_url,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                    headers={"User-Agent": "AwesomeAggregator/0.1"}
                ) as response:
                    response.raise_for_status()
                    content = await response.text()
        except aiohttp.ClientError as e:
            raise SourceFetchError(
                f"Failed to fetch YouTube feed: {e}",
                source_url=self.feed_url, cause=e
            )

        feed = feedparser.parse(content)
        if feed.bozo and not feed.entries:
            raise SourceFetchError(
                f"Failed to parse YouTube feed: {feed.bozo_exception}",
                source_url=self.feed_url
            )

        channel_name = feed.feed.get("title", "Unknown Channel")
        items = []

        for entry in feed.entries:
            video_id = entry.get("yt_videoid", "")
            published = entry.get("published")

            # YouTube RSS provides high-quality thumbnails
            thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else None

            items.append(ContentItem(
                title=entry.get("title", "Untitled Video"),
                url=entry.get("link", f"https://www.youtube.com/watch?v={video_id}"),
                description=entry.get("summary", ""),
                image_url=thumbnail,
                author=entry.get("author", channel_name),
                published_at=published,
                metadata={
                    "video_id": video_id,
                    "channel_name": channel_name,
                    "channel_id": self.channel_id,
                    "source_type": "youtube",
                    "views": entry.get("media_statistics", {}).get("views"),
                }
            ))

        logger.debug(f"YouTube: Fetched {len(items)} videos from {channel_name}")
        return items

    def get_source_type(self) -> str:
        return "youtube"

    def get_display_name(self) -> str:
        return self.config.get("name", f"YouTube: {self.channel_id}")

    @staticmethod
    def _extract_channel_id(url: str) -> str | None:
        """Extract a channel ID that is already present in the URL."""
        for pattern in CHANNEL_ID_PATTERNS:
            match = pattern.search(url)
            if match:
                return match.group(1)
        # If the URL looks like a raw channel ID
        if re.match(r"^UC[A-Za-z0-9_-]{22}$", url):
            return url
        return None

    @staticmethod
    async def _resolve_channel_id(url: str) -> str | None:
        """Fetch a channel page and read its channel ID out of the markup.

        Covers youtube.com/@handle and youtube.com/user/name, neither of which
        carries the id. Costs one request, and only on the first fetch.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                    headers={"User-Agent": "Mozilla/5.0"},
                ) as response:
                    if response.status != 200:
                        return None
                    html = await response.text()
        except aiohttp.ClientError:
            return None

        for pattern in PAGE_CHANNEL_ID_PATTERNS:
            match = pattern.search(html)
            if match:
                return match.group(1)
        return None
