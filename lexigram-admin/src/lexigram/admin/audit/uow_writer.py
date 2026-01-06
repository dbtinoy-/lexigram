"""UowAuditWriter — transactional audit writer participating in unit of work."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from lexigram.contracts.admin.audit_entry import AuditEntry
from lexigram.contracts.admin.audit_logger import AdminAuditLoggerProtocol


class UoWProtocol(Protocol):
    """Minimal unit-of-work interface for audit deferral."""

    def on_commit(self, callback: Callable[[], Any]) -> None: ...
    def on_rollback(self, callback: Callable[[], Any]) -> None: ...


class UowAuditWriter:
    """Audit writer that defers writes to the active unit of work.

    If no active UoW is available (e.g. outside a request context),
    writes are dispatched directly to the underlying logger.
    """

    def __init__(
        self,
        logger: AdminAuditLoggerProtocol,
        uow_provider: Callable[[], UoWProtocol | None],
    ) -> None:
        self._logger = logger
        self._uow_provider = uow_provider

    async def write(self, entry: AuditEntry) -> None:
        """Write *entry*, deferring to active UoW when available."""
        uow = self._uow_provider()
        if uow is None:
            await self._logger.write(entry)
            return
        uow.on_commit(lambda: self._logger.write(entry))


__all__ = ["UoWProtocol", "UowAuditWriter"]
