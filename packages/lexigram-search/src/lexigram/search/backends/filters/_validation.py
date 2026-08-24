"""Canonical-filter validation shared by all dialect renderers."""

from __future__ import annotations

import re
from typing import Any

_FIELD_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")

_OPERATOR_KEYS = frozenset(
    {"in", "nin", "ne", "gt", "gte", "lt", "lte", "contains", "exists"}
)
_BOOLEAN_KEYS = frozenset({"$and", "$or", "$not"})
_COMPARISON_SYMBOLS = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}


class FilterRenderError(ValueError):
    """Raised when a filter dict cannot be rendered for a backend."""


def _validate_filters(filters: dict[str, Any]) -> None:
    """Validate a filter dict against the canonical dialect.

    Args:
        filters: The filter dict to validate.

    Raises:
        FilterRenderError: If the structure violates the dialect (bad field
            names, unknown operators, malformed boolean groups).
    """
    for key, value in filters.items():
        if key in _BOOLEAN_KEYS:
            if key == "$not":
                if not isinstance(value, dict):
                    raise FilterRenderError("$not must contain a single filter dict")
                _validate_filters(value)
                continue
            if not isinstance(value, list) or not all(
                isinstance(item, dict) for item in value
            ):
                raise FilterRenderError(f"{key} must be a list of filter dicts")
            for item in value:
                _validate_filters(item)
            continue
        if not _FIELD_NAME_RE.fullmatch(key):
            raise FilterRenderError(
                f"invalid field name {key!r}; only A-Za-z0-9._- are allowed"
            )
        if isinstance(value, dict):
            unknown = set(value) - _OPERATOR_KEYS
            if unknown:
                raise FilterRenderError(
                    f"unsupported operator(s) {sorted(unknown)} on field {key!r}"
                )


# ---------------------------------------------------------------------------
# Elasticsearch / OpenSearch
# ---------------------------------------------------------------------------
