"""API routes for reader mode article extraction."""

import json

from fastapi import APIRouter, HTTPException, Query
import aiohttp
from bs4 import BeautifulSoup

from backend.config import REQUEST_TIMEOUT, logger

router = APIRouter(prefix="/api/reader", tags=["reader"])

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False


@router.get("/extract")
async def extract_article(url: str = Query(..., min_length=5)):
    """Extract full article content from a URL for reader mode."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                html = await resp.text()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {str(e)}")

    # Extract metadata from HTML
    soup = BeautifulSoup(html, "html.parser")
    meta = {}
    for tag in soup.find_all("meta"):
        prop = tag.get("property", tag.get("name", ""))
        content = tag.get("content", "")
        if prop and content:
            meta[prop] = content

    hero_image = meta.get("og:image") or meta.get("twitter:image")
    site_name = meta.get("og:site_name", "")

    if not TRAFILATURA_AVAILABLE:
        raise HTTPException(status_code=503, detail="trafilatura not installed")

    result = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        include_images=True,
        include_links=True,
        output_format="txt",
    )

    if not result:
        raise HTTPException(status_code=422, detail="Could not extract article content")

    # Also try to get structured data for metadata
    structured = trafilatura.extract(html, output_format="json")
    structured_data = {}
    if structured:
        try:
            structured_data = json.loads(structured) if isinstance(structured, str) else structured
        except (json.JSONDecodeError, TypeError):
            pass

    title = structured_data.get("title") or meta.get("og:title") or meta.get("title", "Untitled")
    author = structured_data.get("author") or meta.get("author")
    date = structured_data.get("date")

    # Convert plain text to basic HTML paragraphs
    paragraphs = result.split("\n\n")
    content_html = "".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())

    word_count = len(result.split())
    read_minutes = max(1, word_count // 250)

    return {
        "title": title,
        "author": author,
        "date": date,
        "site_name": site_name,
        "hero_image": hero_image,
        "content_html": content_html,
        "word_count": word_count,
        "estimated_read_minutes": read_minutes,
    }
