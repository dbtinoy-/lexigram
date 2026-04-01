"""DI provider for lexigram-ai-memory."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from lexigram.ai.memory.backends.in_memory import InMemoryMemoryBackend
from lexigram.ai.memory.config import MemoryConfig
from lexigram.ai.memory.consolidation.consolidator import MemoryConsolidator
from lexigram.ai.memory.consolidation.scheduler import ConsolidationScheduler
from lexigram.ai.memory.episodic.store import EpisodicMemoryStore
from lexigram.ai.memory.pruning.pruner import DynamicContextPruner
from lexigram.ai.memory.retrieval.ranking import RelevanceRanker
from lexigram.ai.memory.retrieval.retriever import MemoryRetriever
from lexigram.ai.memory.semantic.store import SemanticMemoryStore
from lexigram.ai.memory.working.manager import WorkingMemoryManager
from lexigram.contracts.ai.memory import (
    EpisodicMemoryProtocol,
    MemoryConsolidatorProtocol,
    MemoryStoreProtocol,
    SemanticMemoryProtocol,
    WorkingMemoryProtocol,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.di.provider import Provider, ProviderPriority
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class MemoryProvider(Provider):
    """Registers all memory services in the DI container.

    Wires up the MemoryStoreProtocol, EpisodicMemoryProtocol,
    SemanticMemoryProtocol, WorkingMemoryProtocol, and consolidation
    services. The default backend is ``InMemoryMemoryBackend``; callers
    with persistent needs should register a ``MemoryStoreProtocol``
    override after this provider runs.
    """

    name = "ai-memory"
    priority = ProviderPriority.DOMAIN
    config_key: str | None = "ai_memory"
    config_model: type | None = MemoryConfig

    def __init__(
        self,
        config: MemoryConfig | None = None,
        enable_consolidation: bool = True,
    ) -> None:
        """Initialise the provider.

        Args:
            config: Memory configuration. Defaults to ``MemoryConfig()``.
            enable_consolidation: Start the consolidation scheduler during
                :meth:`boot`. When ``False``, the scheduler is never started
                regardless of ``config.consolidation.enabled``.
        """
        super().__init__()
        self._requested_config = config
        self._mem_config = config or MemoryConfig()
        self._enable_consolidation = enable_consolidation
        self._scheduler: ConsolidationScheduler | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register memory services.

        Args:
            container: DI container registrar.
        """
        self._mem_config = self._requested_config or (
            self.config
            if isinstance(getattr(self, "config", None), MemoryConfig)
            else self._mem_config
        )
        container.singleton(MemoryConfig, self._mem_config)

        if not self._mem_config.enabled:
            logger.info("memory_disabled", reason="MemoryConfig.enabled=False")
            return

        # Follow-up: wire cache/database/vector backends at boot phase
        # (see 2026-08-12-ai-family-gaps-remediation.md Task 5) — requires
        # resolving CacheBackendProtocol/DatabaseProviderProtocol from the
        # container, which ContainerRegistrarProtocol does not permit.
        if self._mem_config.default_backend != "in_memory":
            logger.warning(
                "memory_backend_not_implemented",
                requested_backend=self._mem_config.default_backend,
                fallback="in_memory",
            )

        backend = InMemoryMemoryBackend()
        episodic = EpisodicMemoryStore(backend=backend)
        semantic = SemanticMemoryStore(
            min_confidence=self._mem_config.semantic.min_confidence,
            max_facts_per_entity=self._mem_config.semantic.max_facts_per_entity,
        )
        working = WorkingMemoryManager(
            episodic=episodic,
            semantic=cast("SemanticMemoryProtocol", semantic),
            config=self._mem_config.working,
        )
        consolidator = MemoryConsolidator(config=self._mem_config.consolidation)
        retriever = MemoryRetriever(sources=[backend])

        container.singleton(MemoryStoreProtocol, lambda: backend)
        container.singleton(EpisodicMemoryProtocol, lambda: episodic)
        container.singleton(SemanticMemoryProtocol, lambda: semantic)
        container.singleton(WorkingMemoryProtocol, lambda: working)
        container.singleton(MemoryConsolidatorProtocol, lambda: consolidator)
        container.singleton(MemoryRetriever, lambda: retriever)
        container.singleton(RelevanceRanker, RelevanceRanker)
        # Register pruner — the container will auto-inject TokenCounterProtocol
        container.singleton(DynamicContextPruner, DynamicContextPruner)

        logger.debug("memory_services_registered")

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Start the consolidation scheduler if enabled.

        Args:
            container: Resolved DI container.
        """
        if not self._mem_config.enabled:
            return

        if self._enable_consolidation and self._mem_config.consolidation.enabled:
            store = await container.resolve_optional(MemoryStoreProtocol)
            consolidator = await container.resolve_optional(MemoryConsolidatorProtocol)
            if store is None or consolidator is None:
                logger.warning("memory_consolidation_dependencies_missing")
                return

            self._scheduler = ConsolidationScheduler(
                store=store,
                consolidator=consolidator,
                config=self._mem_config.consolidation,
            )
            await self._scheduler.start()
            logger.info("memory_consolidation_scheduler_started")

    async def shutdown(self) -> None:
        """Stop the consolidation scheduler."""
        if self._scheduler:
            await self._scheduler.stop()
            self._scheduler = None

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Health check — always healthy (in-process domain provider).

        No external backend to ping.

        Args:
            timeout: Ignored for in-process providers.

        Returns:
            Always HEALTHY — no external backend to ping.
        """
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={"status": "operational"},
        )


__all__ = ["MemoryProvider"]
