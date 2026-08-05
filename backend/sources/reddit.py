"""Reddit subreddit source adapter, backed by the subreddit's public Atom feed.

Reddit used to serve `https://www.reddit.com/r/<sub>/hot.json` to anyone. It no
longer does: every unauthenticated client gets 403 Blocked, and old.reddit.com
redirects the same request to a login page. `api.reddit.com` answers once from a
cold IP and then blocks too. The Atom feed at `/r/<sub>/hot/.rss` is the only
path that still works without an account, so that is what this reads.

The trade: Atom carries no vote or comment counts. Those keys are therefore
omitted rather than set to zero, because the UI hides a missing score and would
otherwise display a confident "0 pts" on every post.

The feed is rate limited per IP and the budget is small. Two requests in quick
succession get a 429, so the default refresh interval for Reddit sources is ten
minutes. Expect harsher throttling from a VPN or a hosting provider than from a
home connection.
"""

import re
from html import unescape

import aiohttp
import feedparser

from backend.config import REQUEST_TIMEOUT, logger
from backend.sources.base import BaseSource, ContentItem, SourceFetchError

# Extract the subreddit name from a URL such as https://reddit.com/r/technology
SUBREDDIT_PATTERN = re.compile(r"reddit\.com/r/([A-Za-z0-9_]+)")

# Reddit wraps every link post in a table that ends with "[link]" and
# "[comments]" anchors. The first is the article the post points at.
LINK_ANCHOR_PATTERN = re.compile(
    r'<a href="([^"]+)"[^>]*>\s*\[link\]\s*</a>', re.IGNORECASE
)

# The same boilerplate tail, once the markup has been stripped to text.
BOILERPLATE_PATTERN = re.compile(
    r"\s*submitted by\s*/u/\S+\s*(\[link\])?\s*(\[comments\])?\s*$", re.IGNORECASE
)

TAG_PATTERN = re.compile(r"<[^>]+>")


class RedditSource(BaseSource):
    """Fetches hot posts from a subreddit via its public Atom feed."""

    def __init__(self, url: str, **kwargs):
        super().__init__(url, **kwargs)
        self.subreddit = self._extract_subreddit(url)
        self.feed_url = f"https://www.reddit.com/r/{self.subreddit}/hot/.rss?limit=50"

    async def fetch(self) -> list[ContentItem]:
        """Fetch hot posts from the subreddit."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.feed_url,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                    headers={"User-Agent": "AwesomeAggregator/0.1 (content dashboard)"},
                ) as response:
                    response.raise_for_status()
                    body = await response.text()
        except aiohttp.ClientError as e:
            raise SourceFetchError(
                f"Failed to fetch Reddit feed: {e}",
                source_url=self.feed_url, cause=e
            )

        feed = feedparser.parse(body)
        if feed.bozo and not feed.entries:
            raise SourceFetchError(
                f"Failed to parse Reddit feed: {feed.bozo_exception}",
                source_url=self.feed_url
            )

        items = []
        for entry in feed.entries:
            content_html = self._entry_content(entry)
            external_url = self._extract_external_url(content_html)

            items.append(ContentItem(
                title=entry.get("title", "Untitled"),
                url=entry.get("link", ""),
                description=self._clean_description(content_html),
                image_url=self._extract_image(entry),
                author=self._clean_author(entry.get("author")),
                published_at=entry.get("published") or entry.get("updated"),
                metadata={
                    "subreddit": self.subreddit,
                    "post_id": entry.get("id"),
                    # No score or num_comments: the Atom feed does not carry them
                    # and a fabricated zero would render as "0 pts" in the panel.
                    "external_url": external_url,
                },
            ))

        logger.debug(f"Reddit: Fetched {len(items)} posts from r/{self.subreddit}")
        return items

    def get_source_type(self) -> str:
        return "reddit"

    def get_display_name(self) -> str:
        return self.config.get("name", f"r/{self.subreddit}")

    @staticmethod
    def _extract_subreddit(url: str) -> str:
        """Extract the subreddit name from a URL, or accept a bare name."""
        match = SUBREDDIT_PATTERN.search(url)
        if match:
            return match.group(1)
        cleaned = url.strip("/").split("/")[-1]
        return cleaned if cleaned else "all"

    @staticmethod
    def _entry_content(entry) -> str:
        """Return the entry's HTML body, whichever field carries it."""
        content = entry.get("content")
        if content and isinstance(content, list) and content[0].get("value"):
            return content[0]["value"]
        return entry.get("summary", "") or ""

    @staticmethod
    def _extract_external_url(content_html: str) -> str | None:
        """The article a link post points at, from its "[link]" anchor.

        Self posts have no such anchor and correctly yield None.
        """
        match = LINK_ANCHOR_PATTERN.search(content_html or "")
        return unescape(match.group(1)) if match else None

    @staticmethod
    def _extract_image(entry) -> str | None:
        """Preview image, which Reddit publishes as a media:thumbnail."""
        media = entry.get("media_thumbnail")
        if media and isinstance(media, list) and media[0].get("url"):
            return media[0]["url"]
        return None

    @staticmethod
    def _clean_author(author: str | None) -> str | None:
        """Reddit reports authors as "/u/name". Keep just the name."""
        if not author:
            return None
        return author[3:] if author.startswith("/u/") else author

    @classmethod
    def _clean_description(cls, content_html: str) -> str:
        """Plain text body, with Reddit's submission boilerplate removed.

        For a link post the whole body is that boilerplate, so this correctly
        returns an empty string rather than "submitted by /u/someone [link]".
        """
        text = TAG_PATTERN.sub(" ", content_html or "")
        text = unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        text = BOILERPLATE_PATTERN.sub("", text).strip()
        return text[:500]
