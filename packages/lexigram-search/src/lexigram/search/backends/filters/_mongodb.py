"""MongoDB filter rendering."""

from __future__ import annotations

import re
from typing import Any

from lexigram.search.backends.filters._validation import (
    FilterRenderError,
    _validate_filters,
)


def _mongo_sub(sub: dict[str, Any]) -> dict[str, Any]:
    """Render one sub-filter dict to a MongoDB query document."""
    doc: dict[str, Any] = {}
    for key, value in sub.items():
        if key == "$not":
            if not isinstance(value, dict):
                raise FilterRenderError("$not must contain a single filter dict")
            doc.update({"$nor": [_mongo_sub(value)]})
            continue
        if key in ("$and", "$or"):
            if not isinstance(value, list):
                raise FilterRenderError(f"{key} must be a list of filter dicts")
            doc.update({key: [_mongo_sub(group) for group in value]})
            continue
        if isinstance(value, dict):
            if "contains" in value:
                doc[key] = {
                    "$regex": re.escape(str(value["contains"])),
                    "$options": "i",
                }
                continue
            if "exists" in value:
                doc[key] = {"$exists": bool(value["exists"])}
                continue
            if "in" in value:
                doc[key] = {"$in": list(value["in"])}
                continue
            if "nin" in value:
                doc[key] = {"$nin": list(value["nin"])}
                continue
            if "ne" in value:
                doc[key] = {"$ne": value["ne"]}
                continue
            doc[key] = {f"${op}": val for op, val in value.items()}
            continue
        if isinstance(value, (list, tuple)):
            doc[key] = {"$in": list(value)}
        elif isinstance(value, str) and "*" in value:
            doc[key] = {"$regex": value.replace("*", ".*"), "$options": "i"}
        else:
            doc[key] = value
    return doc


def render_mongodb(filters: dict[str, Any]) -> dict[str, Any]:
    """Render a filter dict to a MongoDB query document.

    Args:
        filters: Canonical filter dict.

    Returns:
        A MongoDB query document (``{"status": "active"}``,
        ``{"score": {"$gte": 80}}``, ``{"$or": [...]}``, ...).

    Raises:
        FilterRenderError: If the filter dict violates the dialect.
    """
    _validate_filters(filters)
    return _mongo_sub(filters)


# ---------------------------------------------------------------------------
# SQL backends (Postgres / MySQL / SQLite) — WHERE clause with parameters
# ---------------------------------------------------------------------------
