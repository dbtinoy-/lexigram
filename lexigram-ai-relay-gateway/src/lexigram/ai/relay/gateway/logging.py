"""Fire-and-forget request-log emitter for the relay gateway.

The emitter never touches the request path: append failures are logged
as warnings and the entry is dropped.  Task references are retained in
a set until completion so the event loop never loses a pending append
(see ``asyncio.create_task`` reference-retention rules).
"""

from __future__ import annotations

import asyncio

from lexigram.contracts.ai.relay import (
    RelayRequestLogEntry,
    RelayRequestLogStoreProtocol,
)
from lexigram.logging import get_logger

__all__ = ["RelayRequestLogger"]

logger = get_logger(__name__)


class RelayRequestLogger:
    """Best-effort durable sink for request-log entries.

    ``log`` returns immediately; the append runs as a background task.
    The store contract forbids raising to callers, but a third-party
    store that raises anyway must never fail the request path — the
    append is guarded and reported as a warning only.
    """

    def __init__(self, store: RelayRequestLogStoreProtocol) -> None:
        """Bind the store.

        Args:
            store: The durable request-log sink; resolved from the
                container by the web layer.
        """
        self._store = store
        self._background_tasks: set[asyncio.Task[None]] = set()

    def log(self, entry: RelayRequestLogEntry) -> None:
        """Schedule one entry for the store, never blocking the caller.

        Args:
            entry: The redaction-safe entry to persist.
        """
        task = asyncio.create_task(self._safe_append(entry))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _safe_append(self, entry: RelayRequestLogEntry) -> None:
        """Append without letting store failures reach the request path."""
        try:
            await self._store.append(entry)
        except Exception:  # noqa: BLE001 — any store failure must stay off the request path
            logger.warning(
                "relay_request_log_store_failed", request_id=entry.request_id
            )
