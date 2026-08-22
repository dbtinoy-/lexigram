"""DI wiring for the memory-chat demo (internal)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.ai.memory import (
    EpisodicMemoryProtocol,
    SemanticMemoryProtocol,
    WorkingMemoryProtocol,
)
from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

from memory_chat.chat_service import ConciergeService


class ConciergeProvider(Provider):
    """Resolves the three memory contracts and assembles the service."""

    name = "concierge"

    def __init__(self) -> None:
        super().__init__()
        self._service: ConciergeService | None = None

    def _get_service(self) -> ConciergeService:
        """Valid only after boot()."""
        if self._service is None:
            raise RuntimeError("ConciergeProvider has not been booted yet")
        return self._service

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind the lazy factory; stores resolve only in boot()."""
        container.singleton(ConciergeService, factory=self._get_service)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Assemble the facade from MemoryModule's exported protocols."""
        working = await container.resolve(WorkingMemoryProtocol)
        episodic = await container.resolve(EpisodicMemoryProtocol)
        semantic = await container.resolve(SemanticMemoryProtocol)
        self._service = ConciergeService(
            working=working,
            episodic=episodic,
            semantic=semantic,
        )


__all__ = ["ConciergeProvider"]
