"""Utility routines for GraphQL pagination.

This module hosts the cursor encoding/decoding logic and pagination helper
functions.  Previously these were in the package root alongside the data
classes; they have now been moved here to keep ``__init__`` lean.
"""

from __future__ import annotations

import base64
import binascii
from typing import TYPE_CHECKING, TypeVar

from lexigram.graphql.pagination.types import (
    CursorConnection,
    CursorPaginationInput,
    Edge,
    OffsetPaginationInput,
    PageInfo,
    PaginationResult,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

# Cursor helpers -------------------------------------------------------------

T = TypeVar("T")


def encode_cursor(offset: int) -> str:
    """Encode an offset as a base64 cursor.

    Args:
        offset: The offset to encode.

    Returns:
        Base64-encoded cursor string.
    """
    cursor = f"cursor:{offset}"
    return base64.b64encode(cursor.encode()).decode()


def decode_cursor(cursor: str) -> int:
    """Decode a base64 cursor to an offset.

    Args:
        cursor: The cursor string to decode.

    Returns:
        The decoded offset.

    Raises:
        ValueError: If the cursor is invalid.
    """
    try:
        decoded = base64.b64decode(cursor.encode()).decode()
        if decoded.startswith("cursor:"):
            return int(decoded[7:])
    except (ValueError, binascii.Error):
        pass
    raise ValueError(f"Invalid cursor: {cursor}")


def encode_cursor_from_id(item_id: str) -> str:
    """Encode an item ID as an opaque cursor.

    Args:
        item_id: The item ID to encode.

    Returns:
        Base64-encoded cursor string.
    """
    cursor = f"id:{item_id}"
    return base64.b64encode(cursor.encode()).decode()


def decode_cursor_to_id(cursor: str) -> str:
    """Decode a cursor to an item ID.

    Args:
        cursor: The cursor string to decode.

    Returns:
        The decoded item ID.

    Raises:
        ValueError: If the cursor is invalid.
    """
    try:
        decoded = base64.b64decode(cursor.encode()).decode()
        if decoded.startswith("id:"):
            return decoded[3:]
    except (ValueError, binascii.Error):
        pass
    raise ValueError(f"Invalid cursor: {cursor}")


# Pagination implementations ------------------------------------------------


async def paginate_connection(
    items: Sequence[T],
    pagination: CursorPaginationInput | dict,
    total_count: int | None = None,
) -> CursorConnection[T]:
    """Create a Relay Connection from a list of items.

    Args:
        items: Sequence of items to paginate.
        pagination: Cursor pagination input.
        total_count: Total count of items (if known).

    Returns:
        A Connection with edges and page info.
    """
    if isinstance(pagination, dict):
        pagination = CursorPaginationInput(**pagination)

    pagination.validate()

    # Calculate offsets
    start_offset = 0
    end_offset = len(items)

    if pagination.after:
        try:
            start_offset = decode_cursor(pagination.after) + 1
        except ValueError:
            start_offset = 0

    if pagination.before:
        try:
            end_offset = decode_cursor(pagination.before)
        except ValueError:
            end_offset = len(items)

    # Apply first/last limits
    if pagination.first is not None:
        end_offset = min(start_offset + pagination.first, end_offset)
    elif pagination.last is not None:
        start_offset = max(end_offset - pagination.last, start_offset)

    # Get the slice
    page_items = items[start_offset:end_offset]

    # Calculate total if not provided
    if total_count is None:
        total_count = len(items)

    # Create edges
    edges = []
    for i, item in enumerate(page_items):
        offset = start_offset + i
        edge = Edge(
            node=item,
            cursor=encode_cursor(offset),
        )
        edges.append(edge)

    # Calculate has_next/has_previous
    has_next = end_offset < len(items)
    has_previous = start_offset > 0

    page_info = PageInfo(
        has_next_page=has_next,
        has_previous_page=has_previous,
        start_cursor=edges[0].cursor if edges else None,
        end_cursor=edges[-1].cursor if edges else None,
    )

    return CursorConnection(
        edges=edges,
        page_info=page_info,
    )


async def paginate_offset(
    items: Sequence[T],
    pagination: OffsetPaginationInput | dict,
    total_count: int | None = None,
) -> PaginationResult[T]:
    """Paginate using offset-based pagination.

    Args:
        items: Sequence of items to paginate.
        pagination: Offset pagination input.
        total_count: Total count of items (if known).

    Returns:
        PaginationResult with items and metadata.
    """
    if isinstance(pagination, dict):
        pagination = OffsetPaginationInput(**pagination)

    pagination.validate()

    # Calculate total if not provided
    if total_count is None:
        total_count = len(items)

    # Apply offset and limit
    offset = pagination.offset
    limit = min(pagination.offset + pagination.limit, total_count)

    page_items = items[offset:limit]

    # Calculate has_next/has_previous
    has_next = limit < total_count
    has_previous = offset > 0

    return PaginationResult(
        items=list(page_items),
        total_count=total_count,
        has_next=has_next,
        has_previous=has_previous,
    )


def calculate_offset(
    first: int | None,
    after: str | None,
    last: int | None,
    before: str | None,
    default_first: int = 10,
) -> tuple[int, int]:
    """Calculate offset and limit from cursor pagination inputs.

    Args:
        first: Number of items forward.
        after: Cursor to start after.
        last: Number of items backward.
        before: Cursor to start before.
        default_first: Default number of items if not specified.

    Returns:
        Tuple of (offset, limit).
    """
    offset = 0
    limit = default_first

    # Determine direction
    if after:
        try:
            offset = decode_cursor(after) + 1
        except ValueError:
            offset = 0

    if before:
        try:
            offset = decode_cursor(before) - default_first
            offset = max(offset, 0)
        except ValueError:
            pass

    if first is not None:
        limit = first
    elif last is not None:
        limit = last

    return offset, limit
