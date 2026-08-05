"""Abstract base class for content source adapters."""

from abc import ABC, abstractmethod
from typing import Any


class ContentItem:
    """A single content item fetched from a source."""

    def __init__(self, title: str, url: str, description: str = None,
                 image_url: str = None, author: str = None,
                 published_at: str = None, metadata: dict[str, Any] = None):
        self.title = title
        self.url = url
        self.description = description
        self.image_url = image_url
        self.author = author
        self.published_at = published_at
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "image_url": self.image_url,
            "author": self.author,
            "published_at": self.published_at,
            "metadata": self.metadata,
        }


class BaseSource(ABC):
    """Abstract base class that all source adapters must implement."""

    def __init__(self, url: str, **kwargs):
        self.url = url
        self.config = kwargs

    @abstractmethod
    async def fetch(self) -> list[ContentItem]:
        """Fetch content items from the source.

        Returns a list of ContentItem objects.
        Raises SourceFetchError on failure.
        """
        ...

    @abstractmethod
    def get_source_type(self) -> str:
        """Return the source type identifier (e.g., 'rss', 'youtube')."""
        ...

    def get_display_name(self) -> str:
        """Return a human-readable name for this source."""
        return self.url


class SourceFetchError(Exception):
    """Raised when a source fetch fails."""

    def __init__(self, message: str, source_url: str = None, cause: Exception = None):
        self.source_url = source_url
        self.cause = cause
        super().__init__(message)
