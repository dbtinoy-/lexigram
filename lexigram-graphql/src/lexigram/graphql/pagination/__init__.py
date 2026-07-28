"""GraphQL pagination helpers.

This package exposes utilities for Relay-style cursor pagination and simple
offset-based pagination.  Implementation details live in submodules so the
root stays concise.
"""

from __future__ import annotations

from lexigram.graphql.pagination.helpers import (
    calculate_offset,
    decode_cursor,
    decode_cursor_to_id,
    encode_cursor,
    encode_cursor_from_id,
    paginate_connection,
    paginate_offset,
)
from lexigram.graphql.pagination.types import (
    CursorConnection,
    CursorPaginationInput,
    Edge,
    OffsetPaginationInput,
    PageInfo,
    PaginationResult,
)

__all__ = [
    "CursorConnection",
    "CursorPaginationInput",
    "Edge",
    "OffsetPaginationInput",
    "PageInfo",
    "PaginationResult",
    "calculate_offset",
    "decode_cursor",
    "decode_cursor_to_id",
    "encode_cursor",
    "encode_cursor_from_id",
    "paginate_connection",
    "paginate_offset",
]
