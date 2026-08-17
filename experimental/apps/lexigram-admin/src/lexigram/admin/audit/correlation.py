"""Correlation ID propagation via contextvars."""

from __future__ import annotations

from contextvars import ContextVar
import uuid

correlation_id_ctx: ContextVar[str | None] = ContextVar(
    "admin_correlation_id", default=None
)


def get_correlation_id() -> str | None:
    """Return the current correlation ID (or None if not set)."""
    return correlation_id_ctx.get()


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_ctx.set(cid)


def new_correlation_id() -> str:
    """Generate a new unique correlation ID (UUID hex)."""
    return uuid.uuid4().hex


__all__ = [
    "correlation_id_ctx",
    "get_correlation_id",
    "new_correlation_id",
    "set_correlation_id",
]
