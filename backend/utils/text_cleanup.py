"""Text cleanup utilities for content items."""

import re


def clean_headline(title: str) -> str:
    """Clean up a headline by removing clickbait prefixes, trailing site names,
    normalizing ALL CAPS, and collapsing excessive punctuation."""
    if not title:
        return title

    # Remove clickbait prefixes
    prefixes = ["BREAKING:", "WATCH:", "JUST IN:", "EXCLUSIVE:", "DEVELOPING:", "UPDATED:", "ALERT:"]
    cleaned = title
    for prefix in prefixes:
        if cleaned.upper().startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()

    # Remove trailing | Site Name or - Site Name
    cleaned = re.sub(r'\s*[|\-\u2013\u2014]\s*[A-Z][A-Za-z\s.]+$', '', cleaned)

    # Convert ALL CAPS to title case (if >40% of words are all caps)
    words = cleaned.split()
    if words:
        caps_count = sum(1 for w in words if w.isupper() and len(w) > 1)
        if caps_count / len(words) > 0.4:
            cleaned = cleaned.title()

    # Collapse excessive punctuation
    cleaned = re.sub(r'!{2,}', '!', cleaned)
    cleaned = re.sub(r'\?{2,}', '?', cleaned)
    cleaned = re.sub(r'\.{4,}', '...', cleaned)

    return cleaned.strip()
