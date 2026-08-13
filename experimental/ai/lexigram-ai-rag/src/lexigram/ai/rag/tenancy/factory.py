"""TenantScopedRAGPipeline — per-tenant pipeline factory with instance caching."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any

from lexigram.contracts.ai.exceptions import RAGError
from lexigram.contracts.ai.rag import RAGContext, RAGResponse
from lexigram.primitives.context import TENANT_ID
from lexigram.result import Result

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from lexigram.ai.rag.config import RAGConfig
    from lexigram.contracts.ai.rag import RAGPipelineProtocol
    from lexigram.contracts.data.vector.tenancy import TenantCollectionResolver
    from lexigram.primitives.context import Context

    PipelineFactory = Callable[["RAGConfig"], Awaitable[RAGPipelineProtocol]]


class TenantScopedRAGPipeline:
    """Resolves per-tenant RAG pipelines at request time.

    Caches pipeline instances per tenant with LRU eviction. When no tenant
    context is available, delegates to a default pipeline built from the
    base config.

    The factory callable receives a tenant-scoped ``RAGConfig`` (with
    ``collection_name`` already resolved) and should return a fully
    constructed ``RAGPipelineProtocol``.

    Example usage::

        factory = TenantScopedRAGPipeline(
            base_config=RAGConfig(collection_name="canon"),
            resolver=TemplatedTenantCollectionResolver(),
            ctx=context,
            pipeline_factory=build_rag_pipeline,
        )
        result = await factory.execute(RAGContext(query="..."))
    """

    def __init__(
        self,
        base_config: RAGConfig,
        resolver: TenantCollectionResolver,
        ctx: Context,
        pipeline_factory: Any,  # Callable[[RAGConfig], Awaitable[RAGPipelineProtocol]]
        cache_size: int = 100,
    ) -> None:
        self._base_config = base_config
        self._resolver = resolver
        self._ctx = ctx
        self._factory = pipeline_factory
        self._cache: OrderedDict[str, RAGPipelineProtocol] = OrderedDict()
        self._cache_size = cache_size

    async def execute(
        self,
        context: RAGContext,
    ) -> Result[RAGResponse, RAGError]:
        """Execute the RAG pipeline with tenant-aware collection resolution.

        When a tenant ID is present in the current ``Context``, the
        ``collection_name`` from ``base_config`` is resolved via the
        ``TenantCollectionResolver`` before delegating to the tenant's
        cached pipeline instance.

        Args:
            context: The RAG execution context.

        Returns:
            The pipeline result or an error.
        """
        tenant_id = self._ctx.get(TENANT_ID)
        pipeline = await self._get_or_create(tenant_id)
        return await pipeline.execute(context)

    async def query(self, question: str, **kwargs: Any) -> RAGResponse:
        """Convenience: execute a query string and return the response.

        Builds a ``RAGContext`` from *question* and extra keyword
        arguments, then delegates to :meth:`execute`. Raises on error.

        Args:
            question: The user query.
            **kwargs: Additional ``RAGContext`` fields.

        Returns:
            The RAG response.

        Raises:
            RAGError: If the pipeline execution fails.
        """
        context = RAGContext(query=question, **kwargs)
        result = await self.execute(context)
        if result.is_err():
            raise result.unwrap_err()
        return result.unwrap()

    async def _get_or_create(self, tenant_id: str | None) -> RAGPipelineProtocol:
        key = tenant_id or "__default__"
        if key not in self._cache:
            config = self._base_config
            if tenant_id:
                resolved = self._resolver.resolve(
                    self._base_config.collection_name, tenant_id
                )
                config = config.with_collection(resolved)
            pipeline = await self._factory(config)
            self._cache[key] = pipeline
            if len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
        return self._cache[key]


__all__ = ["TenantScopedRAGPipeline"]
