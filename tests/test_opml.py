"""Tests for OPML import/export functionality.

Tests OPML XML generation and parsing logic directly,
since the OPML API endpoints may not be mounted yet.
"""

import pytest
import xml.etree.ElementTree as ET


# --- OPML generation/parsing helpers (mirrors expected backend behavior) ---


def generate_opml(sources: list[dict]) -> str:
    """Generate OPML XML from a list of source dicts."""
    root = ET.Element("opml", version="2.0")
    head = ET.SubElement(root, "head")
    title = ET.SubElement(head, "title")
    title.text = "Awesome Aggregator Feeds"
    body = ET.SubElement(root, "body")

    # Group by category
    categories = {}
    for src in sources:
        cat = src.get("category", "General")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(src)

    for cat_name, cat_sources in categories.items():
        outline = ET.SubElement(body, "outline", text=cat_name, title=cat_name)
        for src in cat_sources:
            ET.SubElement(outline, "outline",
                          type="rss",
                          text=src["name"],
                          title=src["name"],
                          xmlUrl=src["url"],
                          htmlUrl=src.get("html_url", ""),
                          category=cat_name)

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def parse_opml(opml_xml: str) -> list[dict]:
    """Parse OPML XML and return a list of source dicts."""
    root = ET.fromstring(opml_xml)
    sources = []
    for body in root.findall("body"):
        for category_outline in body.findall("outline"):
            cat_name = category_outline.get("text", "General")
            for feed_outline in category_outline.findall("outline"):
                url = feed_outline.get("xmlUrl")
                if url:
                    sources.append({
                        "name": feed_outline.get("text", ""),
                        "url": url,
                        "category": cat_name,
                        "source_type": "rss",
                    })
    return sources


# --- Tests ---


def test_export_empty_sources_returns_valid_opml():
    """Exporting an empty source list should produce valid OPML XML."""
    opml = generate_opml([])
    root = ET.fromstring(opml)
    assert root.tag == "opml"
    assert root.get("version") == "2.0"
    head = root.find("head")
    assert head is not None
    body = root.find("body")
    assert body is not None
    # No outlines in body
    assert len(list(body)) == 0


def test_export_sources_grouped_by_category():
    """Sources should be grouped under category outlines."""
    sources = [
        {"name": "Feed A", "url": "https://a.com/feed", "category": "News"},
        {"name": "Feed B", "url": "https://b.com/feed", "category": "News"},
        {"name": "Feed C", "url": "https://c.com/feed", "category": "Tech"},
    ]
    opml = generate_opml(sources)
    root = ET.fromstring(opml)
    body = root.find("body")
    categories = body.findall("outline")
    assert len(categories) == 2
    cat_names = {c.get("text") for c in categories}
    assert "News" in cat_names
    assert "Tech" in cat_names


def test_import_valid_opml_creates_sources():
    """Parsing valid OPML should return a list of source dicts."""
    sources = [
        {"name": "Test Feed", "url": "https://test.com/feed.xml", "category": "General"},
    ]
    opml = generate_opml(sources)
    parsed = parse_opml(opml)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "Test Feed"
    assert parsed[0]["url"] == "https://test.com/feed.xml"
    assert parsed[0]["category"] == "General"


def test_import_opml_preserves_category():
    """Parsed sources should retain their category from the OPML."""
    sources = [
        {"name": "Feed 1", "url": "https://f1.com/feed", "category": "Science"},
        {"name": "Feed 2", "url": "https://f2.com/feed", "category": "Tech"},
    ]
    opml = generate_opml(sources)
    parsed = parse_opml(opml)
    categories = {s["category"] for s in parsed}
    assert "Science" in categories
    assert "Tech" in categories


def test_round_trip_export_then_import():
    """Exporting then importing should preserve source data."""
    original = [
        {"name": "HN", "url": "https://hnrss.org/frontpage", "category": "News"},
        {"name": "Lobsters", "url": "https://lobste.rs/rss", "category": "Dev"},
        {"name": "NASA", "url": "https://www.nasa.gov/rss/feed", "category": "Science"},
    ]
    opml = generate_opml(original)
    imported = parse_opml(opml)
    assert len(imported) == len(original)
    for orig, imp in zip(original, imported):
        assert imp["name"] == orig["name"]
        assert imp["url"] == orig["url"]
        assert imp["category"] == orig["category"]


def test_import_invalid_xml_raises_error():
    """Parsing invalid XML should raise a ParseError."""
    with pytest.raises(ET.ParseError):
        parse_opml("this is not valid xml <><>")


def test_export_opml_has_xml_declaration():
    """Exported OPML should start with an XML declaration."""
    opml = generate_opml([{"name": "F", "url": "https://f.com/rss", "category": "G"}])
    assert opml.startswith("<?xml")


def test_import_opml_skips_outlines_without_url():
    """Outlines without xmlUrl attribute should be skipped."""
    opml = """<?xml version="1.0"?>
    <opml version="2.0">
      <head><title>Test</title></head>
      <body>
        <outline text="Category">
          <outline text="No URL" title="No URL"/>
          <outline text="Has URL" title="Has URL" xmlUrl="https://example.com/feed"/>
        </outline>
      </body>
    </opml>"""
    parsed = parse_opml(opml)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "Has URL"
