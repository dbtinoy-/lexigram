"""
Metrics collection for Lexigram Intelligence operations.

This module provides comprehensive metrics collection for:
- LLM operations (requests, tokens, duration, costs)
- Vector store operations (add, search, delete)
- Cache operations (hits, misses)
- RAG pipeline operations (queries, retrievals, latency)

All metrics use lexigram-monitor's MetricsCollectorProtocol for consistent observability.
"""

from __future__ import annotations

from functools import wraps
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.ai.observability.metrics.core import AIMetrics


from lexigram.contracts.observability.metrics import (
    MetricsCollectorProtocol as MetricsCollectorProtocol,
)


def track_llm_call(
    provider: str,
    model: str,
    metrics: AIMetrics | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to automatically track LLM call metrics.

    Args:
        provider: LLM provider name (e.g., "openai", "anthropic")
        model: Model name (e.g., "gpt-4", "claude-3-opus")
        metrics: AIMetrics instance to use. If None, creates a new one.

    Returns:
        Decorator function

    Example:
        >>> @track_llm_call(provider="openai", model="gpt-4")
        ... async def complete(messages):
        ...     response = await client.complete(messages)
        ...     return response
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal metrics

            if metrics is None:
                return await func(*args, **kwargs)

            labels = {"provider": provider, "model": model}

            # Track active requests
            metrics.llm_active_requests.increment(labels=labels)

            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)

                # Extract metrics from result if available
                if hasattr(result, "usage"):
                    usage = result.usage
                    if hasattr(usage, "total_tokens"):
                        metrics.llm_tokens_total.increment(
                            amount=usage.total_tokens,
                            labels={**labels, "type": "total"},
                        )
                    if hasattr(usage, "prompt_tokens"):
                        metrics.llm_tokens_total.increment(
                            amount=usage.prompt_tokens,
                            labels={**labels, "type": "prompt"},
                        )
                    if hasattr(usage, "completion_tokens"):
                        metrics.llm_tokens_total.increment(
                            amount=usage.completion_tokens,
                            labels={**labels, "type": "completion"},
                        )

                if hasattr(result, "cost") and result.cost is not None:
                    metrics.llm_cost_dollars.increment(
                        amount=int(result.cost * 1_000_000),  # Store as micro-dollars
                        labels=labels,
                    )

            except (
                Exception
            ):  # metrics decorator must observe all exceptions without narrowing
                status = "error"
                raise

            else:
                return result

            finally:
                # Track request completion
                duration = time.time() - start_time
                metrics.llm_duration_seconds.observe(value=duration, labels=labels)
                metrics.llm_requests_total.increment(
                    labels={**labels, "status": status},
                )
                metrics.llm_active_requests.decrement(labels=labels)

        return wrapper

    return decorator


def track_vector_operation(
    operation: str,
    provider: str,
    metrics: AIMetrics | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to automatically track vector store operation metrics.

    Args:
        operation: Operation type (e.g., "add", "search", "delete")
        provider: Vector store provider (e.g., "pgvector", "chroma", "qdrant")
        metrics: AIMetrics instance to use. If None, creates a new one.

    Returns:
        Decorator function

    Example:
        >>> @track_vector_operation(operation="search", provider="pgvector")
        ... async def search(query_embedding, limit=10):
        ...     results = await store.search(query_embedding, limit)
        ...     return results
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal metrics

            if metrics is None:
                return await func(*args, **kwargs)

            labels = {"operation": operation, "provider": provider}

            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # Track document counts for add/search operations
                if operation == "add" and hasattr(result, "__len__"):
                    metrics.vector_documents_total.increment(
                        amount=len(result),
                        labels={**labels, "type": "added"},
                    )
                elif operation == "search" and hasattr(result, "__len__"):
                    metrics.vector_documents_total.increment(
                        amount=len(result),
                        labels={**labels, "type": "retrieved"},
                    )

                return result

            finally:
                duration = time.time() - start_time
                metrics.vector_duration_seconds.observe(value=duration, labels=labels)
                metrics.vector_operations_total.increment(labels=labels)

        return wrapper

    return decorator


def track_embedding_operation(
    model: str,
    metrics: AIMetrics | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to automatically track embedding operation metrics.

    Args:
        model: Embedding model name (e.g., "text-embedding-ada-002")
        metrics: AIMetrics instance to use. If None, creates a new one.

    Returns:
        Decorator function

    Example:
        >>> @track_embedding_operation(model="text-embedding-ada-002")
        ... async def embed_batch(texts):
        ...     embeddings = await embedder.embed(texts)
        ...     return embeddings
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal metrics

            if metrics is None:
                return await func(*args, **kwargs)

            labels = {"model": model}

            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # Track batch size
                if hasattr(result, "__len__"):
                    metrics.embedding_batch_size.observe(
                        value=len(result),
                        labels=labels,
                    )

                return result

            finally:
                duration = time.time() - start_time
                metrics.embedding_duration_seconds.observe(
                    value=duration,
                    labels=labels,
                )
                metrics.embedding_operations_total.increment(labels=labels)

        return wrapper

    return decorator
