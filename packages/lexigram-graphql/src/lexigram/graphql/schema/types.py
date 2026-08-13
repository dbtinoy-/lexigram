"""GraphQL type helpers.

This module provides type aliases and helpers for defining
GraphQL types using Strawberry.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar, cast

import strawberry

T = TypeVar("T")


# Re-export Strawberry type decorators for convenience
ObjectType: Any = strawberry.type
InputType: Any = strawberry.input
InterfaceType: Any = strawberry.interface
EnumType: Any = strawberry.enum
ScalarType: Any = strawberry.scalar


def union_type(*types: Any, name: str | None = None) -> Any:
    """Create a GraphQL union type.

    Args:
        types: Types to include in the union.
        name: Optional name for the union.

    Returns:
        Union type annotation.

    Example:
        ```python
        SearchResult = union_type(User, Post, Comment, name="SearchResult")

        @strawberry.type
        class Query:
            @strawberry.field
            def search(self, query: str) -> list[SearchResult]:
                ...
        ```
    """
    return strawberry.union(name or "Union", types=types)  # type: ignore[call-arg]


# Generic Connection class - NOT a Strawberry type, just a type hint
# Use create_connection_type() to create concrete Connection types
class Connection(Generic[T]):
    """GraphQL Connection type template for cursor-based pagination.

    This is a generic template. Use create_connection_type() to create
    concrete Connection types for your node types.

    Attributes:
        edges: List of edges containing nodes.
        page_info: Pagination information.
        total_count: Total number of items.
    """

    class Edge:
        """Connection edge template."""

        node: Any
        cursor: str

    class PageInfo:
        """Pagination information."""

        has_next_page: bool
        has_previous_page: bool
        start_cursor: str | None
        end_cursor: str | None

    edges: list[Any]
    page_info: Any  # Will be PageInfo type
    total_count: int = 0


# Concrete PageInfo type for use in typed connections
@strawberry.type
class ConnectionPageInfo:
    """Pagination information for connections."""

    has_next_page: bool
    has_previous_page: bool
    start_cursor: str | None = None
    end_cursor: str | None = None


@strawberry.type
class PagedResult(Generic[T]):
    """Simple offset-based pagination result.

    Attributes:
        items: List of items in the current page.
        total: Total number of items.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
        has_next: Whether there are more pages.
        has_previous: Whether there are previous pages.
    """

    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool = False
    has_previous: bool = False

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


@strawberry.input
class PaginationInput:
    """Input for pagination parameters.

    Attributes:
        page: Page number (1-indexed).
        page_size: Number of items per page.
    """

    page: int = 1
    page_size: int = 20


@strawberry.input
class CursorPaginationInput:
    """Input for cursor-based pagination.

    Attributes:
        first: Number of items to fetch from the start.
        after: Cursor to fetch items after.
        last: Number of items to fetch from the end.
        before: Cursor to fetch items before.
    """

    first: int | None = None
    after: str | None = None
    last: int | None = None
    before: str | None = None


@strawberry.input
class SortInput:
    """Input for sorting.

    Attributes:
        field: Field to sort by.
        direction: Sort direction (ASC or DESC).
    """

    field: str
    direction: str = "ASC"


@strawberry.type
class MutationResult(Generic[T]):
    """Standard mutation result type.

    Attributes:
        success: Whether the mutation succeeded.
        data: Result data if successful.
        errors: Error messages if failed.
    """

    success: bool
    data: T | None = None
    errors: list[str] = strawberry.field(default_factory=list)


@strawberry.type
class DeleteResult:
    """Result of a delete mutation.

    Attributes:
        success: Whether deletion succeeded.
        id: ID of deleted item.
        message: Optional message.
    """

    success: bool
    id: str | None = None
    message: str | None = None


def create_connection_type(
    node_type: type[T],
    name: str | None = None,
) -> type[Connection[T]]:
    """Create a Connection type for a specific node type.

    Args:
        node_type: The node type for the connection.
        name: Optional name prefix for the connection type.

    Returns:
        A Connection type class.
    """
    type_name = name or node_type.__name__

    @strawberry.type(name=f"{type_name}Edge")
    class TypedEdge:
        node: Any  # node_type used at runtime; annotate as Any for typing
        cursor: str

    @strawberry.type(name=f"{type_name}Connection")
    class TypedConnection:
        edges: list[TypedEdge]
        page_info: ConnectionPageInfo
        total_count: int = 0

    # type so callers and mypy treat this as Connection[T].
    return cast("type[Connection[T]]", TypedConnection)


__all__ = [
    "Connection",
    "ConnectionPageInfo",
    "CursorPaginationInput",
    "DeleteResult",
    "EnumType",
    "InputType",
    "InterfaceType",
    "MutationResult",
    "ObjectType",
    "PagedResult",
    "PaginationInput",
    "ScalarType",
    "SortInput",
    "create_connection_type",
    "union_type",
]
