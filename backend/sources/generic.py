"""Generic web page source adapter - makes any website a content source.

Uses trafilatura for article extraction and can be configured with CSS selectors
for structured content extraction from any web page. This is the "universal adapter"
that allows ANY web-based content to be pulled into the dashboard.

For authenticated services (email, LinkedIn, Instagram, Facebook), this adapter
supports:
1. Cookie-based auth (paste cookies from browser)
2. Custom headers (auth tokens, session IDs)
3. CSS selector targeting (extract specific page sections)
4. JSON API endpoints (for services with public/private APIs)
"""

import re
from datetime import datetime
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

from backend.config import REQUEST_TIMEOUT, logger
from backend.sources.base import BaseSource, ContentItem, SourceFetchError

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False


class GenericSource(BaseSource):
    """Universal web content source - turns any web page into a feed.

    Config options (passed via kwargs):
        css_selector: CSS selector to find content items (e.g., "article", ".post", ".email-row")
        title_selector: CSS selector for item titles within each item
        link_selector: CSS selector for item links within each item
        description_selector: CSS selector for item descriptions
        image_selector: CSS selector for item images
        date_selector: CSS selector for item dates
        json_path: JSONPath-like dotted path for JSON API responses (e.g., "data.posts")
        headers: Custom HTTP headers (dict)
        cookies: Custom cookies (dict)
        mode: "auto" | "article" | "structured" | "json"
            - auto: Try trafilatura first, fall back to structured
            - article: Extract as a single article (news, blog posts)
            - structured: Use CSS selectors to extract multiple items
            - json: Parse JSON response
    """

    def __init__(self, url: str, **kwargs):
        super().__init__(url, **kwargs)
        self.mode = kwargs.get("mode", "auto")
        self.css_selector = kwargs.get("css_selector")
        self.title_selector = kwargs.get("title_selector", "h2, h3, .title")
        self.link_selector = kwargs.get("link_selector", "a")
        self.description_selector = kwargs.get("description_selector", "p, .description, .summary")
        self.image_selector = kwargs.get("image_selector", "img")
        self.date_selector = kwargs.get("date_selector", "time, .date, .timestamp")
        self.json_path = kwargs.get("json_path")
        self.custom_headers = kwargs.get("headers", {})
        self.custom_cookies = kwargs.get("cookies", {})

    async def fetch(self) -> list[ContentItem]:
        """Fetch content from the web page."""
        html = await self._fetch_page()

        if self.mode == "json":
            return self._parse_json(html)
        elif self.mode == "structured" or self.css_selector:
            return self._parse_structured(html)
        elif self.mode == "article":
            return self._parse_article(html)
        else:
            # Auto mode: try structured if selector given, else article extraction
            if self.css_selector:
                return self._parse_structured(html)
            items = self._parse_article(html)
            if not items:
                # Fall back to link extraction
                return self._parse_links(html)
            return items

    async def _fetch_page(self) -> str:
        """Fetch the raw HTML/JSON from the URL."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            **self.custom_headers,
        }

        try:
            async with aiohttp.ClientSession(cookies=self.custom_cookies) as session:
                async with session.get(
                    self.url,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                    headers=headers,
                ) as response:
                    response.raise_for_status()
                    return await response.text()
        except aiohttp.ClientError as e:
            raise SourceFetchError(
                f"Failed to fetch page: {e}",
                source_url=self.url, cause=e
            )

    def _extract_meta(self, html: str) -> dict:
        """Extract OpenGraph and meta tag info from HTML head."""
        soup = BeautifulSoup(html, "html.parser")
        meta = {}
        for tag in soup.find_all("meta"):
            prop = tag.get("property", tag.get("name", ""))
            content = tag.get("content", "")
            if prop and content:
                meta[prop] = content
        return meta

    def _parse_article(self, html: str) -> list[ContentItem]:
        """Extract content as a single article using trafilatura."""
        # Always extract meta tags as fallback
        meta = self._extract_meta(html)
        meta_image = (meta.get("og:image") or meta.get("twitter:image")
                      or meta.get("twitter:image:src"))
        meta_title = meta.get("og:title") or meta.get("twitter:title")
        meta_desc = meta.get("og:description") or meta.get("description")
        meta_site = meta.get("og:site_name")

        if not TRAFILATURA_AVAILABLE:
            logger.warning("trafilatura not installed, falling back to BS4")
            if meta_title:
                return [ContentItem(
                    title=meta_title,
                    url=self.url,
                    description=meta_desc or "",
                    image_url=meta_image,
                    metadata={"sitename": meta_site},
                )]
            return self._parse_links(html)

        result = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            include_images=True,
            output_format="json",
        )

        if not result:
            # Trafilatura found nothing (JS-heavy SPA) — use meta tags
            if meta_title or meta_desc:
                return [ContentItem(
                    title=meta_title or "Untitled",
                    url=self.url,
                    description=meta_desc or "",
                    image_url=meta_image,
                    metadata={"sitename": meta_site},
                )]
            return []

        import json
        try:
            data = json.loads(result) if isinstance(result, str) else result
        except (json.JSONDecodeError, TypeError):
            return [ContentItem(
                title=meta_title or self.url.split("/")[-1] or "Page Content",
                url=self.url,
                description=str(result)[:500],
                image_url=meta_image,
            )]

        return [ContentItem(
            title=data.get("title") or meta_title or "Untitled",
            url=self.url,
            description=(data.get("text", "") or meta_desc or "")[:500],
            image_url=data.get("image") or meta_image,
            author=data.get("author"),
            published_at=data.get("date"),
            metadata={
                "sitename": data.get("sitename") or meta_site,
                "categories": data.get("categories", ""),
            }
        )]

    def _parse_structured(self, html: str) -> list[ContentItem]:
        """Extract multiple items using CSS selectors."""
        soup = BeautifulSoup(html, "html.parser")
        container_elements = soup.select(self.css_selector) if self.css_selector else []

        if not container_elements:
            logger.warning(f"No elements matched selector '{self.css_selector}' on {self.url}")
            return []

        items = []
        for el in container_elements[:50]:  # Cap at 50 items
            title_el = el.select_one(self.title_selector)
            link_el = el.select_one(self.link_selector)
            desc_el = el.select_one(self.description_selector)
            img_el = el.select_one(self.image_selector)
            date_el = el.select_one(self.date_selector)

            title = title_el.get_text(strip=True) if title_el else el.get_text(strip=True)[:100]
            if not title:
                continue

            link = ""
            if link_el and link_el.get("href"):
                link = link_el["href"]
                if link.startswith("/"):
                    # Relative URL - make absolute
                    from urllib.parse import urljoin
                    link = urljoin(self.url, link)

            items.append(ContentItem(
                title=title,
                url=link or self.url,
                description=desc_el.get_text(strip=True)[:500] if desc_el else None,
                image_url=img_el.get("src") if img_el else None,
                author=None,
                published_at=date_el.get_text(strip=True) if date_el else None,
            ))

        logger.debug(f"Generic: Extracted {len(items)} items via CSS selectors from {self.url}")
        return items

    def _parse_json(self, text: str) -> list[ContentItem]:
        """Parse a JSON API response."""
        import json
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise SourceFetchError(f"Invalid JSON: {e}", source_url=self.url)

        # Navigate to the specified path
        if self.json_path:
            for key in self.json_path.split("."):
                if isinstance(data, dict):
                    data = data.get(key, [])
                elif isinstance(data, list) and key.isdigit():
                    data = data[int(key)]

        if not isinstance(data, list):
            data = [data]

        items = []
        for entry in data[:50]:
            if not isinstance(entry, dict):
                continue
            items.append(ContentItem(
                title=entry.get("title", entry.get("name", entry.get("text", "Untitled")))[:200],
                url=entry.get("url", entry.get("link", entry.get("href", self.url))),
                description=entry.get("description", entry.get("body", entry.get("content", "")))[:500],
                image_url=entry.get("image", entry.get("thumbnail", entry.get("image_url"))),
                author=entry.get("author", entry.get("user", entry.get("creator"))),
                published_at=entry.get("date", entry.get("published", entry.get("created_at"))),
                metadata=entry,
            ))

        return items

    def _parse_links(self, html: str) -> list[ContentItem]:
        """Fallback: extract all meaningful links from the page."""
        soup = BeautifulSoup(html, "html.parser")
        items = []
        seen_urls = set()

        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)

            if not text or len(text) < 5:
                continue
            if href.startswith(("#", "javascript:", "mailto:")):
                continue
            if href in seen_urls:
                continue

            if href.startswith("/"):
                from urllib.parse import urljoin
                href = urljoin(self.url, href)

            seen_urls.add(href)
            items.append(ContentItem(
                title=text[:200],
                url=href,
            ))

        return items[:50]

    def get_source_type(self) -> str:
        return "generic"

    def get_display_name(self) -> str:
        return self.config.get("name", self.url)
