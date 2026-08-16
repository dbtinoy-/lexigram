"""Audit store backends."""

from __future__ import annotations

from lexigram.audit.store.memory import InMemoryAuditStore

__all__ = [
    "InMemoryAuditStore",
    # SqlAuditStore is available when a DB backend is configured
    "SqlAuditStore",
]


def __getattr__(name: str) -> object:
    """Lazy-load SqlAuditStore to avoid hard dependency on DB provider."""
    if name == "SqlAuditStore":
        from lexigram.audit.store.sql import SqlAuditStore

        return SqlAuditStore
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
