"""Page base classes and types for lexigram-admin."""

from __future__ import annotations

from lexigram.admin.pages.base import Page
from lexigram.admin.pages.types import NavigationEntry, PageResponse

__all__ = [
    "NavigationEntry",
    "Page",
    "PageResponse",
]
