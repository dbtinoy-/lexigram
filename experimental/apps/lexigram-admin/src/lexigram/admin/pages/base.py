"""Page ABC: base class for admin pages.

.. experimental::
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lexigram.admin.pages.types import NavigationEntry, PageResponse


class MethodNotAllowedError(RuntimeError):
    """Raised when a page does not support the POST method."""


class Page(ABC):
    """Base class for admin pages.

    A Page is the unit of routing. Each page declares its title,
    path, and optional navigation entry. Subclasses implement
    ``view()`` and optionally ``post()``.
    """

    title: str
    path: str = ""

    @abstractmethod
    async def view(self, request: Any) -> PageResponse:
        """Render the page on GET request."""
        ...

    async def post(self, request: Any) -> PageResponse:
        """Handle POST request. Default raises MethodNotAllowedError."""
        raise MethodNotAllowedError("POST not supported on this page")

    def navigation(self) -> NavigationEntry | None:
        """Return a navigation entry or None to skip the sidebar."""
        return None


__all__ = [
    "Page",
]
