"""DI wiring for the memory-chat demo.

A Provider tells the DI container *what* exists and *how* to build it.
Two-phase lifecycle: ``register()`` binds, ``boot()`` initializes.

Simplest patterns for new users:

- ``container.singleton(Thing, instance=Thing())`` — already built, hand it over
- ``container.singleton(Thing, factory=lambda: ...)`` — build lazily on first resolve
- ``container.singleton(Thing, factory=self._build_thing)`` — async factory for complex wiring
"""

from __future__ import annotations

from lexigram.contracts.ai.memory import (
    EpisodicMemoryProtocol,
    SemanticMemoryProtocol,
    WorkingMemoryProtocol,
)
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.health import HealthCheckResult
from lexigram.di.provider import Provider
from memory_chat.repository.memory_repository import MemoryRepository
from memory_chat.services.chat_service import ConciergeService

__all__ = ["ConciergeProvider"]


class ConciergeProvider(Provider):
    """Demo-specific DI registrations — your app replaces this.

    Provider lifecycle: register() → boot() → shutdown().
    register() binds services (no I/O); boot() initializes after freeze.
    """

    name = "concierge"

    def __init__(self) -> None:
        super().__init__()
        self._service: ConciergeService | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind the lazy factory; stores resolve only in boot().

        ``container.singleton(Thing, instance=Thing())`` for already-built objects.
        ``container.singleton(Thing, factory=async_fn)`` for services that need
        other services resolved first (async factories run during resolve).
        """
        container.singleton(ConciergeService, factory=self._get_service)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Assemble the repository facade over MemoryModule's protocols.

        boot() runs AFTER register() completes and the container is frozen.
        This is where you resolve services and do initialization work
        (seeding data, warming caches, connecting to external services).
        """
        working = await container.resolve(WorkingMemoryProtocol)
        episodic = await container.resolve(EpisodicMemoryProtocol)
        semantic = await container.resolve(SemanticMemoryProtocol)
        self._service = ConciergeService(
            MemoryRepository(working=working, episodic=episodic, semantic=semantic),
        )

    def _get_service(self) -> ConciergeService:
        """Valid only after boot()."""
        if self._service is None:
            raise RuntimeError("ConciergeProvider has not been booted yet")
        return self._service

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report component readiness with live counters."""
        return HealthCheckResult(
            component=self.name,
            details={"owners_seen": len(self._service._turns) if self._service else 0},
        )


__all__ = ["ConciergeProvider"]
