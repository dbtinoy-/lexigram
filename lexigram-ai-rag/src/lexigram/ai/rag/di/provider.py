"""DI Provider for the RAG (Retrieval Augmented Generation) subsystem."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING, Any

from lexigram.ai.rag.config import RAGConfig
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.exceptions.container import UnresolvableDependencyError
from lexigram.contracts.exceptions.provider import ModuleVisibilityError
from lexigram.di.provider import Provider, ProviderPriority
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )

logger = get_logger(__name__)


def _llmlingua_available() -> bool:
    """Check if llmlingua package is installed."""
    try:
        return importlib.util.find_spec("llmlingua") is not None
    except (ValueError, AttributeError):
        return False


def _flashrank_available() -> bool:
    """Check if flashrank package is installed."""
    try:
        return importlib.util.find_spec("flashrank") is not None
    except (ValueError, AttributeError):
        return False


class RAGProvider(Provider):
    """Registers RAG pipeline services and strategy registries with the DI container."""

    name = "rag"
    priority = ProviderPriority.DOMAIN
    config_key: str | None = "ai.rag"
    config_model: type | None = RAGConfig

    def __init__(self, config: RAGConfig | None = None) -> None:
        super().__init__()
        self._config = config or RAGConfig()

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(RAGConfig, instance=self._config)

        from lexigram.ai.rag.context_compression.strategy_registry import (
            CompressionStrategyRegistry,
        )

        compression_registry = CompressionStrategyRegistry.with_defaults()

        # Register LLMLingua-2 handler if available
        if _llmlingua_available():
            from lexigram.ai.rag.context_compression.strategies.llmlingua2 import (
                LLMLingua2CompressorStrategy,
                LLMLingua2StrategyHandler,
            )

            compression_registry.register(
                LLMLingua2StrategyHandler(LLMLingua2CompressorStrategy())
            )
            logger.debug("llmlingua2_compressor_registered")
        else:
            logger.debug("llmlingua2_compressor_skipped_not_installed")

        container.singleton(CompressionStrategyRegistry, instance=compression_registry)

        from lexigram.ai.rag.hyde.strategy_registry import HyDEStrategyRegistry

        hyde_registry = HyDEStrategyRegistry.with_defaults()
        container.singleton(HyDEStrategyRegistry, instance=hyde_registry)

        from lexigram.ai.rag.reasoning.strategy_registry import (
            ReasoningStrategyRegistry,
        )

        reasoning_registry = ReasoningStrategyRegistry.with_defaults()
        container.singleton(ReasoningStrategyRegistry, instance=reasoning_registry)

        from lexigram.ai.rag.pipeline.stages.synthesis_registry import (
            SynthesisStrategyRegistry,
        )

        synthesis_registry = SynthesisStrategyRegistry.with_defaults()
        container.singleton(SynthesisStrategyRegistry, instance=synthesis_registry)

        from lexigram.ai.rag.chunking.strategy_registry import (
            ChunkingStrategyRegistry,
        )

        chunking_registry = ChunkingStrategyRegistry.with_defaults()
        container.singleton(ChunkingStrategyRegistry, instance=chunking_registry)

        from lexigram.ai.rag.reranking.strategy_registry import (
            RerankingStrategyRegistry,
        )

        reranking_registry = RerankingStrategyRegistry.with_defaults()

        # Register FlashRank handler if available
        if _flashrank_available():
            from lexigram.ai.rag.reranking.strategies.flashrank import (
                FlashRankStrategyHandler,
            )

            reranking_registry.register(FlashRankStrategyHandler())
            logger.debug("flashrank_reranker_registered")
        else:
            logger.debug("flashrank_reranker_skipped_not_installed")

        container.singleton(RerankingStrategyRegistry, instance=reranking_registry)

        await self._discover_strategies(container)

        await self._register_knowledge_graph(container)

        logger.info("rag_provider_registered")

    async def _register_knowledge_graph(
        self,
        container: ContainerRegistrarProtocol,
    ) -> None:
        """Register the default in-memory knowledge graph singleton."""
        from lexigram.ai.rag.knowledge_graph.core import KnowledgeGraph

        container.singleton(KnowledgeGraph, instance=KnowledgeGraph())
        logger.info("rag_knowledge_graph_in_memory")

    async def _discover_strategies(self, container: ContainerRegistrarProtocol) -> None:
        """Auto-discover RAG strategy providers via entry-points."""
        import importlib.metadata as _meta

        from lexigram.di.provider import Provider as _Provider

        for group in (
            "lexigram.chunking.strategies",
            "lexigram.retrieval.strategies",
        ):
            eps = _meta.entry_points(group=group)
            for ep in eps:
                try:
                    candidate = ep.load()
                except (ImportError, AttributeError, TypeError, ValueError) as exc:
                    logger.warning(
                        "rag_strategy_ep_load_failed",
                        name=ep.name,
                        group=group,
                        error=str(exc),
                    )
                    continue
                if isinstance(candidate, type) and issubclass(candidate, _Provider):
                    await candidate().register(container)
                    logger.info("rag_strategy_ep_loaded", name=ep.name, group=group)
                else:
                    logger.debug("rag_strategy_ep_skipped", name=ep.name, group=group)

    async def _maybe_wrap_with_tenancy(
        self,
        container: BootContainerProtocol,
    ) -> None:
        """Register ``TenantScopedRAGPipeline`` when tenancy is enabled."""
        if not self._config.tenancy.enabled:
            return

        from lexigram.ai.rag.tenancy import TenantScopedRAGPipeline
        from lexigram.ai.rag.tenancy.resolver import (
            TemplatedTenantCollectionResolver,
        )
        from lexigram.contracts.ai.rag import RAGPipelineProtocol
        from lexigram.primitives.context import Context

        ctx = await container.resolve(Context)
        resolver: Any = TemplatedTenantCollectionResolver()
        base_config = self._config

        async def _default_factory(config: RAGConfig) -> RAGPipelineProtocol:
            from lexigram.ai.rag.config import PipelineConfig
            from lexigram.ai.rag.pipeline import RAGPipeline
            from lexigram.ai.rag.pipeline._stage_factory import (
                build_pipeline_stages,
            )

            pipeline_cfg = PipelineConfig()
            stages = build_pipeline_stages(pipeline_cfg)
            return RAGPipeline(config=pipeline_cfg, stages=stages)

        container.singleton(
            RAGPipelineProtocol,
            instance=TenantScopedRAGPipeline(
                base_config=base_config,
                resolver=resolver,
                ctx=ctx,
                pipeline_factory=_default_factory,
            ),
        )
        logger.info("rag_tenancy_enabled")

    async def boot(self, container: BootContainerProtocol) -> None:
        """Boot RAG provider — wire optional integrations."""
        self._booted_container = container

        # Optional: tenancy
        await self._maybe_wrap_with_tenancy(container)

        # Optional: working memory (from lexigram-ai-memory)
        working_memory = None
        try:
            from lexigram.contracts.ai.memory import WorkingMemoryProtocol

            working_memory = await container.resolve(WorkingMemoryProtocol)
            logger.debug("rag_working_memory_available")
        except (
            LookupError,
            RuntimeError,
            AttributeError,
            ImportError,
            TypeError,
            ModuleVisibilityError,
            UnresolvableDependencyError,
        ):
            logger.debug("rag_working_memory_not_available")

        if working_memory is not None:
            self._working_memory = working_memory

        # Optional: graph store
        graph_store_available = False
        try:
            from lexigram.contracts.data.graph.protocols import GraphStoreProtocol

            graph_store = await container.resolve_optional(GraphStoreProtocol)
            graph_store_available = graph_store is not None
        except (
            LookupError,
            RuntimeError,
            AttributeError,
            ImportError,
            TypeError,
            ModuleVisibilityError,
            UnresolvableDependencyError,
        ):
            pass

        logger.info(
            "rag_provider_booted",
            working_memory=working_memory is not None,
            graph_store=graph_store_available,
        )

    async def shutdown(self) -> None:
        pass

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check RAG provider health — verifies embedding service and vector store.

        Returns:
            :class:`~lexigram.contracts.core.HealthCheckResult` with status
            ``healthy`` when all configured dependencies are reachable, or
            ``degraded``/``unhealthy`` otherwise.
        """
        details: dict = {
            "embedding_service": "unconfigured",
            "vector_store": "unconfigured",
        }
        overall = HealthStatus.HEALTHY

        container: BootContainerProtocol | None = getattr(
            self, "_booted_container", None
        )
        if container is None:
            return HealthCheckResult(
                component="rag",
                status=HealthStatus.HEALTHY,
                details={"note": "RAG provider not yet booted"},
            )

        # Check embedding client if available
        try:
            from lexigram.contracts.ai import EmbeddingClientProtocol

            embedding_client = await container.resolve_optional(EmbeddingClientProtocol)
            if embedding_client is not None and hasattr(
                embedding_client, "health_check"
            ):
                emb_result = await embedding_client.health_check(timeout=timeout)
                if hasattr(emb_result, "status"):
                    details["embedding_service"] = emb_result.status
                    if emb_result.status != HealthStatus.HEALTHY:
                        overall = HealthStatus.DEGRADED
                else:
                    details["embedding_service"] = "ok"
            else:
                details["embedding_service"] = "not_configured"
        except (LookupError, RuntimeError, AttributeError) as exc:
            details["embedding_service"] = f"error: {exc}"
            overall = HealthStatus.DEGRADED

        # Check vector store if available
        try:
            from lexigram.contracts.ai import DocumentVectorStoreProtocol

            vector_store = await container.resolve_optional(DocumentVectorStoreProtocol)
            if vector_store is not None and hasattr(vector_store, "health_check"):
                vs_result = await vector_store.health_check(timeout=timeout)
                if hasattr(vs_result, "status"):
                    details["vector_store"] = vs_result.status
                    if vs_result.status != HealthStatus.HEALTHY:
                        overall = HealthStatus.DEGRADED
                else:
                    details["vector_store"] = "ok"
            else:
                details["vector_store"] = "not_configured"
        except (LookupError, RuntimeError, AttributeError) as exc:
            details["vector_store"] = f"error: {exc}"
            overall = HealthStatus.DEGRADED

        return HealthCheckResult(
            component="rag",
            status=overall,
            details=details,
        )


__all__ = ["RAGProvider"]
