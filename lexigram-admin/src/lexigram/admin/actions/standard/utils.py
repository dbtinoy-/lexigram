"""Shared helpers for the standard admin actions."""

from __future__ import annotations

from typing import Any

from lexigram.admin.actions.types import ActionContext


def _extract_id(record: Any) -> Any | None:
    """Extract the ``id`` field from a record dict or object.

    Args:
        record: A record dict or object.

    Returns:
        The record id, or ``None`` when absent.
    """
    if isinstance(record, dict):
        return record.get("id")
    return getattr(record, "id", None)


def _resolve_data_source(ctx: ActionContext, injected: Any | None = None) -> Any | None:
    """Resolve the data source for an action execution.

    Args:
        ctx: Action execution context.
        injected: Constructor-injected data source, if any.

    Returns:
        The resolved data source, or ``None``.
    """
    if injected is not None:
        return injected
    if ctx.data_source is not None:
        return ctx.data_source
    return ctx.metadata.get("data_source")
