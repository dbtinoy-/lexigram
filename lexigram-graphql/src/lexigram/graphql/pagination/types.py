"""Data structures used for GraphQL pagination.

This module defines the dataclasses representing edges, page info,
connections and input/request objects.  They were previously defined in the
package root but have been moved here for a cleaner API surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class Edge(Generic[T]):
    """An edge in a connection."""

    node: T
    cursor: str


@dataclass
class PageInfo:
    """Pagination information."""

    has_next_page: bool
    has_previous_page: bool
    start_cursor: str | None = None
    end_cursor: str | None = None


@dataclass
class CursorConnection(Generic[T]):
    """A connection for cursor-based pagination."""

    edges: list[Edge[T]]
    page_info: PageInfo


@dataclass
class CursorPaginationInput:
    """Input for cursor-based pagination.

    Attributes:
        first: Number of items to return (forward pagination).
        after: Cursor to start after (forward pagination).
        last: Number of items to return (backward pagination).
        before: Cursor to start before (backward pagination).
    """

    first: int | None = None
    after: str | None = None
    last: int | None = None
    before: str | None = None

    def validate(self) -> None:
        """Validate pagination input.

        Raises:
            ValueError: If the input is invalid.
        """
        if self.first is not None and self.first < 0:
            raise ValueError("first must be non-negative")
        if self.last is not None and self.last < 0:
            raise ValueError("last must be non-negative")
        if self.first is not None and self.last is not None:
            raise ValueError("Cannot specify both first and last")
        if self.after is not None and self.before is not None:
            raise ValueError("Cannot specify both after and before")


@dataclass
class OffsetPaginationInput:
    """Input for offset-based pagination.

    Attributes:
        offset: Number of items to skip.
        limit: Maximum number of items to return.
    """

    offset: int = 0
    limit: int = 10

    def validate(self) -> None:
        """Validate pagination input.

        Raises:
            ValueError: If the input is invalid.
        """
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        if self.limit < 0:
            raise ValueError("limit must be non-negative")


@dataclass
class PaginationResult(Generic[T]):
    """Result of pagination operation.

    Attributes:
        items: The paginated items.
        total_count: Total number of items available.
        has_next: Whether there are more items after this page.
        has_previous: Whether there are items before this page.
    """

    items: list[T]
    total_count: int
    has_next: bool = False
    has_previous: bool = False
