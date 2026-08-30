"""Small data-source resolution helpers shared by resource render/mutation paths."""

from __future__ import annotations

from typing import Any


def get_resource_data_source(resource: Any) -> Any | None:
    """Resolve a resource's wired or lazily-provided data source.

    Mounted resources normally store their source on ``_data_source``. Custom
    resources may expose a ``get_data_source()`` method instead, so CRUD,
    relation options, and detail rendering must not silently fall back to a
    non-operational form merely because the private slot is empty.
    """
    if resource is None:
        return None

    source = getattr(resource, "_data_source", None)
    if source is not None:
        return source

    getter = getattr(resource, "get_data_source", None)
    if callable(getter):
        try:
            source = getter()
        except (AttributeError, NotImplementedError, RuntimeError, TypeError, ValueError):
            source = None
        if source is not None:
            return source

    return getattr(resource, "data_source", None)


__all__ = ["get_resource_data_source"]
