"""API routes for OPML import/export."""

import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response

from backend.database import get_all_sources, create_sources_batch

router = APIRouter(prefix="/api/opml", tags=["opml"])


@router.get("/export")
async def export_opml():
    """Export all sources as OPML XML file."""
    sources = await get_all_sources()

    opml = ET.Element("opml", version="2.0")
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = "Awesome Aggregator Sources"
    ET.SubElement(head, "dateCreated").text = datetime.utcnow().isoformat()

    body = ET.SubElement(opml, "body")

    # Group by category
    categories = {}
    for src in sources:
        cat = src.get("category", "General")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(src)

    for cat_name, cat_sources in categories.items():
        cat_outline = ET.SubElement(body, "outline", text=cat_name, title=cat_name)
        for src in cat_sources:
            ET.SubElement(
                cat_outline,
                "outline",
                type="rss",
                text=src["name"],
                title=src["name"],
                xmlUrl=src["url"],
                htmlUrl=src.get("url", ""),
                category=cat_name,
            )

    tree = ET.ElementTree(opml)
    buf = BytesIO()
    # encoding="unicode" makes ElementTree write str, which a BytesIO rejects —
    # every export raised TypeError and returned 500. Naming a real encoding
    # makes it write the bytes the buffer (and the Response) expect.
    tree.write(buf, encoding="utf-8", xml_declaration=True)
    content = buf.getvalue()

    return Response(
        content=content,
        media_type="text/xml",
        headers={"Content-Disposition": "attachment; filename=awesome-aggregator.opml"},
    )


@router.post("/import")
async def import_opml(file: UploadFile = File(...)):
    """Import sources from an OPML file."""
    content = await file.read()

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML: {str(e)}")

    sources_to_create = []
    errors = []

    body = root.find("body")
    if body is None:
        raise HTTPException(status_code=400, detail="Invalid OPML: no body element")

    def process_outlines(parent, category="General"):
        for outline in parent.findall("outline"):
            xml_url = outline.get("xmlUrl")
            if xml_url:
                # This is a feed entry
                name = outline.get("text") or outline.get("title") or xml_url
                sources_to_create.append({
                    "name": name,
                    "source_type": "rss",
                    "url": xml_url,
                    "category": category,
                })
            else:
                # This is a category folder
                cat_name = outline.get("text") or outline.get("title") or category
                process_outlines(outline, cat_name)

    process_outlines(body)

    if not sources_to_create:
        return {"imported": 0, "skipped": 0, "errors": ["No feeds found in OPML file"]}

    created = await create_sources_batch(sources_to_create)
    imported = len(created)
    skipped = len(sources_to_create) - imported

    return {"imported": imported, "skipped": skipped, "errors": errors}
