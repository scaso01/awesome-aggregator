"""API routes for daily digest."""

from datetime import datetime, timedelta

from fastapi import APIRouter

from backend.database import get_all_content

router = APIRouter(prefix="/api/digest", tags=["digest"])


@router.get("/today")
async def get_daily_digest():
    """Get top 10 items from the last 24h, scored by engagement + recency."""
    items = await get_all_content(limit=200, offset=0)

    cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    recent = [
        item for item in items
        if (item.get("published_at") or item.get("fetched_at", "")) >= cutoff
    ]

    if not recent:
        return []

    # Score items
    scored = []
    source_counts = {}

    for item in recent:
        score = 0.0
        metadata = item.get("metadata", {})

        # Reddit engagement signals
        if metadata.get("score"):
            score += min(metadata["score"] / 100, 10)
        if metadata.get("num_comments"):
            score += min(metadata["num_comments"] / 50, 5)

        # Recency bonus
        pub = item.get("published_at") or item.get("fetched_at", "")
        if pub:
            try:
                pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                hours_ago = (datetime.utcnow() - pub_dt.replace(tzinfo=None)).total_seconds() / 3600
                score += max(0, 10 - hours_ago)
            except (ValueError, TypeError):
                score += 5

        # Diversity penalty for same source
        src_id = item.get("source_id")
        source_counts[src_id] = source_counts.get(src_id, 0) + 1
        if source_counts[src_id] > 1:
            score *= 0.5 ** (source_counts[src_id] - 1)

        scored.append({"score": score, "item": item})

    scored.sort(key=lambda x: x["score"], reverse=True)

    result = []
    for rank, entry in enumerate(scored[:10], 1):
        result.append({
            "rank": rank,
            "content_item": entry["item"],
            "score": round(entry["score"], 2),
        })

    return result
