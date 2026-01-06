"""Page types: dataclasses for page responses and navigation entries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PageResponse:
    """Response from a page view handler."""

    content: Any  # Element/htpy content
    title: str
    breadcrumbs: list[tuple[str, str]] | None = None

    @property
    def has_breadcrumbs(self) -> bool:
        """Whether this response includes breadcrumbs."""
        return self.breadcrumbs is not None and len(self.breadcrumbs) > 0


@dataclass
class NavigationEntry:
    """Navigation entry for the admin sidebar/menu."""

    label: str
    url: str
    icon: str | None = None
    permissions: list[str] | None = None
    active: bool = False


__all__ = [
    "NavigationEntry",
    "PageResponse",
]
