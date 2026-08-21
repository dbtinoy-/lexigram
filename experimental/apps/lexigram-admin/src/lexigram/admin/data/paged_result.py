"""Paginated query result container for admin data queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass
class PagedResult(Generic[T]):
    """Paginated query result.

    Contains the items for the current page along with pagination metadata.
    Supports both page-based and cursor-based pagination.

    Example:
        >>> result = PagedResult(
        ...     items=[user1, user2],
        ...     total=100,
        ...     page=1,
        ...     per_page=20,
        ... )
        >>> result.has_next  # True
        >>> result.total_pages  # 5
    """

    items: list[T]
    total: int
    page: int
    per_page: int
    cursor: str | None = None
    next_cursor: str | None = None

    @property
    def has_next(self) -> bool:
        """Check if there are more pages after current."""
        if self.next_cursor is not None:
            return True
        return self.page * self.per_page < self.total

    @property
    def has_prev(self) -> bool:
        """Check if there are pages before current."""
        return self.page > 1

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.per_page <= 0:
            return 0
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def is_empty(self) -> bool:
        """Check if result has no items."""
        return len(self.items) == 0

    @property
    def count(self) -> int:
        """Number of items in current page."""
        return len(self.items)

    @property
    def start_index(self) -> int:
        """1-indexed start position of first item."""
        if self.is_empty:
            return 0
        return (self.page - 1) * self.per_page + 1

    @property
    def end_index(self) -> int:
        """1-indexed position of last item."""
        if self.is_empty:
            return 0
        return self.start_index + self.count - 1

    def map(self, fn: Any) -> PagedResult[Any]:
        """Transform items using a function.

        Args:
            fn: Function to apply to each item

        Returns:
            New PagedResult with transformed items
        """
        return PagedResult(
            items=list(map(fn, self.items)),
            total=self.total,
            page=self.page,
            per_page=self.per_page,
            cursor=self.cursor,
            next_cursor=self.next_cursor,
        )

    @classmethod
    def empty(cls, per_page: int = 20) -> PagedResult[T]:
        """Create an empty PagedResult.

        Args:
            per_page: Items per page for pagination metadata

        Returns:
            Empty PagedResult
        """
        return cls(
            items=[],
            total=0,
            page=1,
            per_page=per_page,
        )


__all__ = [
    "CombinedSpec",
    "EqualSpec",
    "FilterCondition",
    "FilterOperator",
    "FilterSpec",
    "GreaterThanOrEqualSpec",
    "InSpec",
    "LessThanOrEqualSpec",
    "PagedResult",
    "QuerySpec",
]
