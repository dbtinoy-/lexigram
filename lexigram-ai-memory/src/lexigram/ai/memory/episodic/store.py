"""Episodic memory store — records and recalls past interaction turns."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.ai.memory import (
        MemoryEntry,
        MemoryQuery,
        MemorySearchResult,
        MemoryStoreProtocol,
    )

logger = get_logger(__name__)


class EpisodicMemoryStore:
    """Episodic memory layer backed by a pluggable MemoryStoreProtocol."""

    def __init__(self, backend: MemoryStoreProtocol) -> None:
        self._backend = backend

    async def record(self, entry: MemoryEntry) -> None:
        await self._backend.store(entry)
        logger.debug("episodic_recorded", entry_id=entry.id, role=entry.role)

    async def recall(self, query: MemoryQuery) -> list[MemorySearchResult]:
        return await self._backend.retrieve(query)

    async def forget(self, entry_id: str, owner_id: str) -> None:
        """Forget a specific episode within an owner scope.

        Args:
            entry_id: ID of the entry to forget.
            owner_id: Owner scope preventing cross-owner deletion.
        """
        await self._backend.delete(entry_id, owner_id)
        logger.debug("episodic_forgotten", entry_id=entry_id, owner_id=owner_id)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        return HealthCheckResult(
            component="memory.episodic",
            status=HealthStatus.HEALTHY,
            details={"timeout": timeout},
        )


__all__ = ["EpisodicMemoryStore"]
