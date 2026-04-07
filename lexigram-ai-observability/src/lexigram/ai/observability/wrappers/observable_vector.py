"""Observability wrapper for VectorStoreProtocol implementations.

Wraps any :class:`~lexigram.contracts.ai.VectorStoreProtocol` with tracing and metrics
so that every ``add()``, ``search()``, and ``delete()`` call is automatically
instrumented without touching individual backend implementations.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.ai.observability.metrics import AIMetrics
    from lexigram.ai.observability.tracing import AITracer
    from lexigram.contracts.ai.vector import SearchResultProtocol
    from lexigram.contracts.core import HealthCheckResult
    from lexigram.contracts.data.vector.exceptions import VectorError
    from lexigram.result import Result

logger = get_logger(__name__)

__all__ = ["ObservableVectorStore"]


class ObservableVectorStore:
    """Proxy that adds tracing and metrics to any VectorStoreProtocol.

    Wraps the delegate store so callers interact with the same
    :class:`~lexigram.contracts.ai.VectorStoreProtocol` protocol while every
    ``add()``, ``search()``, and ``delete()`` call is:

    - **Traced** via :class:`~lexigram.ai.observability.tracing.AITracer`
    - **Metered** via :class:`~lexigram.ai.observability.metrics.AIMetrics`

    Either dependency may be ``None`` (e.g. when the monitoring module is not
    installed), in which case the wrapper transparently delegates to the
    underlying store.

    Example:
        >>> store = ObservableVectorStore(raw_store, backend="pgvector",
        ...                              collection="documents", tracer=tracer,
        ...                              metrics=metrics)
        >>> results = await store.search(query="find similar docs", k=5)
    """

    def __init__(
        self,
        delegate: Any,
        *,
        backend: str,
        collection: str | None = None,
        tracer: AITracer | None = None,
        metrics: AIMetrics | None = None,
    ) -> None:
        self._delegate = delegate
        self._backend = backend
        self._collection = collection
        self._tracer = tracer
        self._metrics = metrics

    async def add(self, documents: list[Any]) -> Result[list[str], VectorError]:
        """Add documents with tracing and metrics."""
        labels = {"backend": self._backend, "operation": "add"}
        start = time.perf_counter()
        if self._metrics:
            self._metrics.vector_operations_total.increment(labels=labels)
        try:
            if self._tracer:
                with self._tracer.trace_vector_operation(
                    "add", self._backend, self._collection
                ):
                    result = await self._delegate.add(documents)
            else:
                result = await self._delegate.add(documents)
            if self._metrics and result.is_ok():
                self._metrics.vector_documents_total.increment(
                    amount=len(result.unwrap()), labels=labels
                )
            return result
        finally:
            elapsed = time.perf_counter() - start
            if self._metrics:
                self._metrics.vector_duration_seconds.observe(
                    value=elapsed, labels=labels
                )

    async def search(
        self,
        query_vector: list[float] | None = None,
        query: Any = None,
        k: int | None = None,
        top_k: int | None = None,
        filter: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Result[list[SearchResultProtocol], VectorError]:
        """Search with tracing and metrics."""
        labels = {"backend": self._backend, "operation": "search"}
        start = time.perf_counter()
        if self._metrics:
            self._metrics.vector_operations_total.increment(labels=labels)
        try:
            if self._tracer:
                with self._tracer.trace_vector_operation(
                    "search", self._backend, self._collection
                ):
                    result = await self._delegate.search(
                        query_vector=query_vector,
                        query=query,
                        k=k,
                        top_k=top_k,
                        filter=filter,
                        **kwargs,
                    )
            else:
                result = await self._delegate.search(
                    query_vector=query_vector,
                    query=query,
                    k=k,
                    top_k=top_k,
                    filter=filter,
                    **kwargs,
                )
            if self._metrics and result.is_ok():
                self._metrics.vector_documents_total.increment(
                    amount=len(result.unwrap()),
                    labels={"backend": self._backend, "operation": "search_results"},
                )
            return result
        finally:
            elapsed = time.perf_counter() - start
            if self._metrics:
                self._metrics.vector_duration_seconds.observe(
                    value=elapsed, labels=labels
                )

    async def delete(self, ids: list[str]) -> Result[int, VectorError]:
        """Delete documents with tracing and metrics."""
        labels = {"backend": self._backend, "operation": "delete"}
        start = time.perf_counter()
        if self._metrics:
            self._metrics.vector_operations_total.increment(labels=labels)
        try:
            if self._tracer:
                with self._tracer.trace_vector_operation(
                    "delete", self._backend, self._collection
                ):
                    result = await self._delegate.delete(ids)
            else:
                result = await self._delegate.delete(ids)
            return result
        finally:
            elapsed = time.perf_counter() - start
            if self._metrics:
                self._metrics.vector_duration_seconds.observe(
                    value=elapsed, labels=labels
                )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Delegate health check transparently."""
        return await self._delegate.health_check(timeout=timeout)
