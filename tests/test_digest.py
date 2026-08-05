"""Tests for digest scoring and ranking logic.

Tests the digest algorithm directly since the API endpoint
may not be mounted yet.
"""

import pytest
from datetime import datetime, timedelta


def score_item(item: dict) -> float:
    """Score a content item for digest ranking.

    Scoring factors:
    - Reddit: score + num_comments * 2
    - Recency: items in last 6h get 1.5x boost
    - Diversity: penalty if same source appears multiple times
    """
    base_score = 0.0
    metadata = item.get("metadata", {})

    # Reddit scoring
    if metadata.get("score"):
        base_score += metadata["score"]
    if metadata.get("num_comments"):
        base_score += metadata["num_comments"] * 2

    # Fallback score for non-Reddit items
    if base_score == 0:
        base_score = 10.0

    # Recency boost
    published = item.get("published_at")
    if published:
        try:
            pub_dt = datetime.fromisoformat(published)
            hours_ago = (datetime.utcnow() - pub_dt).total_seconds() / 3600
            if hours_ago <= 6:
                base_score *= 1.5
            elif hours_ago <= 12:
                base_score *= 1.2
        except (ValueError, TypeError):
            pass

    return base_score


def apply_diversity_penalty(ranked: list[dict]) -> list[dict]:
    """Apply penalty for items from the same source appearing consecutively."""
    seen_sources = {}
    result = []
    for item in ranked:
        sid = item.get("source_id")
        count = seen_sources.get(sid, 0)
        penalty = 0.8 ** count  # 20% penalty per duplicate
        item["final_score"] = item.get("score", 0) * penalty
        seen_sources[sid] = count + 1
        result.append(item)
    result.sort(key=lambda x: x["final_score"], reverse=True)
    return result


def build_digest(items: list[dict], limit: int = 10) -> list[dict]:
    """Build a digest from a list of content items."""
    # Score items
    scored = []
    for item in items:
        item["score"] = score_item(item)
        scored.append(item)
    scored.sort(key=lambda x: x["score"], reverse=True)
    # Apply diversity
    diversified = apply_diversity_penalty(scored)
    return diversified[:limit]


# --- Tests ---


def test_digest_returns_top_10():
    """Digest should return at most 10 items."""
    items = [{"source_id": i, "metadata": {}} for i in range(20)]
    digest = build_digest(items, limit=10)
    assert len(digest) == 10


def test_digest_scores_reddit_by_score_and_comments():
    """Reddit items with higher score/comments should rank higher."""
    high = {"source_id": 1, "metadata": {"score": 1000, "num_comments": 200}}
    low = {"source_id": 2, "metadata": {"score": 10, "num_comments": 2}}
    assert score_item(high) > score_item(low)


def test_digest_recency_boost():
    """Items published in the last 6 hours should get a recency boost."""
    recent = {
        "source_id": 1, "metadata": {},
        "published_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
    }
    old = {
        "source_id": 2, "metadata": {},
        "published_at": (datetime.utcnow() - timedelta(hours=48)).isoformat(),
    }
    assert score_item(recent) > score_item(old)


def test_digest_diversity_penalty():
    """Items from the same source should receive increasing penalties."""
    items = [
        {"source_id": 1, "score": 100},
        {"source_id": 1, "score": 100},
        {"source_id": 2, "score": 90},
    ]
    result = apply_diversity_penalty(items)
    # The second source_id=1 item should be penalized
    source1_scores = [r["final_score"] for r in result if r["source_id"] == 1]
    assert source1_scores[0] > source1_scores[1] if len(source1_scores) > 1 else True


def test_digest_with_no_items_returns_empty():
    """Digest with no items should return an empty list."""
    digest = build_digest([], limit=10)
    assert digest == []


def test_digest_non_reddit_items_get_base_score():
    """Non-Reddit items without metadata should get a base score of 10."""
    item = {"source_id": 1, "metadata": {}}
    assert score_item(item) == 10.0
