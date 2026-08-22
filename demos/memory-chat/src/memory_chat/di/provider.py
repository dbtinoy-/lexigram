"""DI wiring for the memory-chat demo (internal)."""

from __future__ import annotations

from memory_chat.repository.memory_repository import MemoryRepository
from memory_chat.services.chat_service import ConciergeService

from lexigram.contracts.ai.memory import (
    EpisodicMemoryProtocol,
    SemanticMemoryProtocol,
    WorkingMemoryProtocol,
)
from lexigram.contracts.core.health import HealthCheckResult
from lexigram.di.provider import Provider


class ConciergeProvider(Provider):
    """Resolves the three memory contracts and assembles the service."""

    name = "concierge"

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report component readiness with live counters."""
        return HealthCheckResult(
            component=self.name,
            details={"owners_seen": len(self._service._turns) if self._service else 0},
        )

    def __init__(self) -> None:
        super().__init__()
        self._service: ConciergeService | None = None

    def _get_service(self) -> ConciergeService:
        """Valid only after boot()."""
        if self._service is None:
            raise RuntimeError("ConciergeProvider has not been booted yet")
        return self._service

    async def register(self, container) -> None:
        """Bind the lazy factory; stores resolve only in boot()."""

        assert isinstance(container, object)
        container.singleton(ConciergeService, factory=self._get_service)

    async def boot(self, container) -> None:
        """Assemble the repository façade over MemoryModule's protocols."""
        working = await container.resolve(WorkingMemoryProtocol)
        episodic = await container.resolve(EpisodicMemoryProtocol)
        semantic = await container.resolve(SemanticMemoryProtocol)
        self._service = ConciergeService(
            MemoryRepository(working=working, episodic=episodic, semantic=semantic),
        )


__all__ = ["ConciergeProvider"]
