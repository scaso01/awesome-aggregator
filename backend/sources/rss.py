"""RSS/Atom feed source adapter."""

import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape

import aiohttp
import feedparser

from backend.config import REQUEST_TIMEOUT, logger
from backend.sources.base import BaseSource, ContentItem, SourceFetchError


class RSSSource(BaseSource):
    """Fetches content from RSS/Atom feeds."""

    async def fetch(self) -> list[ContentItem]:
        """Fetch and parse an RSS/Atom feed."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.url,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                    headers={"User-Agent": "AwesomeAggregator/0.1"}
                ) as response:
                    response.raise_for_status()
                    content = await response.text()
        except aiohttp.ClientError as e:
            raise SourceFetchError(
                f"Failed to fetch RSS feed: {e}",
                source_url=self.url, cause=e
            )

        feed = feedparser.parse(content)
        if feed.bozo and not feed.entries:
            raise SourceFetchError(
                f"Failed to parse RSS feed: {feed.bozo_exception}",
                source_url=self.url
            )

        # feedparser does not flag a response that simply is not a feed. An
        # empty body parses to bozo=False with no entries, and so does an HTML
        # page, so both were recorded as a perfectly healthy fetch that just
        # happened to return nothing. Three ESPN panels sat on "Loading..."
        # forever because ESPN answers this client with an empty 202.
        #
        # `version` is the reliable signal: a real feed carries "rss20",
        # "atom10" and so on, an unrecognised document carries "" and an empty
        # body carries None. A genuine feed that currently has no items keeps
        # its version and is left alone, because that is not an error.
        if not feed.get("version"):
            raise SourceFetchError(
                "The response is not a feed. Check the URL points at a feed "
                "rather than a web page, and that the site is not blocking "
                "this client.",
                source_url=self.url
            )

        items = []
        for entry in feed.entries:
            published = self._parse_date(entry)
            image = self._extract_image(entry)

            items.append(ContentItem(
                title=entry.get("title", "Untitled"),
                url=entry.get("link", ""),
                description=self._clean_description(entry.get("summary", "")),
                image_url=image,
                author=entry.get("author"),
                published_at=published,
                metadata={
                    "feed_title": feed.feed.get("title", ""),
                    "tags": [t.get("term", "") for t in entry.get("tags", [])],
                }
            ))

        logger.debug(f"RSS: Fetched {len(items)} items from {self.url}")
        return items

    def get_source_type(self) -> str:
        return "rss"

    def get_display_name(self) -> str:
        return self.config.get("name", self.url)

    @staticmethod
    def _parse_date(entry) -> str | None:
        """Parse the published date from a feed entry."""
        for field in ("published", "updated", "created"):
            raw = entry.get(field)
            if raw:
                try:
                    dt = parsedate_to_datetime(raw)
                    return dt.isoformat()
                except (ValueError, TypeError):
                    pass
            # Try the parsed version
            parsed = entry.get(f"{field}_parsed")
            if parsed:
                try:
                    from time import mktime
                    dt = datetime.fromtimestamp(mktime(parsed))
                    return dt.isoformat()
                except (ValueError, TypeError, OverflowError):
                    pass
        return None

    @staticmethod
    def _extract_image(entry) -> str | None:
        """Try to extract an image URL from a feed entry."""
        # Check media:thumbnail
        media = entry.get("media_thumbnail")
        if media and isinstance(media, list) and media[0].get("url"):
            return media[0]["url"]

        # Check media:content
        media_content = entry.get("media_content")
        if media_content and isinstance(media_content, list):
            for mc in media_content:
                if mc.get("medium") == "image" and mc.get("url"):
                    return mc["url"]

        # Check enclosures
        enclosures = entry.get("enclosures", [])
        for enc in enclosures:
            if enc.get("type", "").startswith("image/") and enc.get("href"):
                return enc["href"]

        return None

    @staticmethod
    def _clean_description(raw: str) -> str:
        """Strip HTML tags and decode entities for plain text display.

        Decoding matters as much as stripping. Feeds routinely write
        punctuation and spacing as character references, and without this step
        they reached the panel verbatim: a TechCrunch summary rendered as
        "written.&#160;It&#8217;s&#160;a trend" on screen. The Reddit adapter
        has always unescaped, so this was one adapter out of step rather than a
        deliberate choice.

        The order is deliberate. Unescaping before the whitespace collapse
        turns &#160; into a non-breaking space, which the collapse then folds
        into an ordinary one, which is what the feed meant by it.
        """
        text = re.sub(r"<[^>]+>", "", raw)
        text = unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:500] if text else ""
