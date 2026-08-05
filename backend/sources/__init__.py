"""Source adapter registry and factory."""

from backend.sources.base import BaseSource
from backend.sources.rss import RSSSource
from backend.sources.youtube import YouTubeSource
from backend.sources.reddit import RedditSource
from backend.sources.generic import GenericSource

# Source type registry
SOURCE_REGISTRY: dict[str, type[BaseSource]] = {
    "rss": RSSSource,
    "youtube": YouTubeSource,
    "reddit": RedditSource,
    "generic": GenericSource,
}


def create_source_adapter(source_type: str, url: str, **kwargs) -> BaseSource:
    """Factory function to create the right source adapter."""
    adapter_class = SOURCE_REGISTRY.get(source_type)
    if adapter_class is None:
        raise ValueError(f"Unknown source type: {source_type}. "
                         f"Available: {list(SOURCE_REGISTRY.keys())}")
    return adapter_class(url=url, **kwargs)


def get_available_types() -> list[str]:
    """Return list of registered source types."""
    return list(SOURCE_REGISTRY.keys())
