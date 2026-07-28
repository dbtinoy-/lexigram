"""
Distributed tracing for Lexigram Intelligence operations.

This module provides distributed tracing capabilities for:
- LLM API calls with token and cost tracking
- Vector store operations (add, search, delete)
- RAG pipeline stages (retrieval, ranking, synthesis)
- Embedding operations

All traces use lexigram-monitor's Tracer for OpenTelemetry compatibility.
"""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.ai.observability.tracing.core import AITracer


# The local TracerProtocol and SpanProtocol definitions are removed as per instruction.
# The type alias Span = SpanProtocol is also removed.

# TracerProtocol is an alias for Tracer in contracts


def trace_llm(
    provider: str,
    model: str,
    tracer: AITracer,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to automatically trace LLM calls.

    Args:
        provider: LLM provider name
        model: Model name
        tracer: AITracer instance to use for tracing

    Returns:
        Decorator function

    Example:
        >>> tracer = AITracer(some_tracer)
        >>> @trace_llm(provider="openai", model="gpt-4", tracer=tracer)
        ... async def complete(messages):
        ...     response = await client.complete(messages)
        ...     return response
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal tracer
            if tracer is None:
                return await func(*args, **kwargs)

            with tracer.trace_llm_call(provider, model) as span:
                try:
                    result = await func(*args, **kwargs)

                    # Extract and record metrics from result
                    if hasattr(result, "usage"):
                        usage = result.usage
                        if hasattr(usage, "total_tokens"):
                            span.set_attribute("llm.tokens.total", usage.total_tokens)
                        if hasattr(usage, "prompt_tokens"):
                            span.set_attribute("llm.tokens.prompt", usage.prompt_tokens)
                        if hasattr(usage, "completion_tokens"):
                            span.set_attribute(
                                "llm.tokens.completion",
                                usage.completion_tokens,
                            )

                    if hasattr(result, "cost") and result.cost is not None:
                        span.set_attribute("llm.cost", result.cost)

                    if hasattr(result, "content"):
                        span.set_attribute("llm.response.length", len(result.content))

                    span.set_attribute("status", "success")

                except (
                    Exception
                ) as e:  # tracing decorator must capture all exception types
                    span.set_attribute("status", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.add_event("exception", {"exception": str(e)})
                    raise
                else:
                    return result

        return wrapper

    return decorator


def trace_vector(
    operation: str,
    provider: str,
    tracer: AITracer,
    collection: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to automatically trace vector operations.

    Args:
        operation: Operation type (e.g., "add", "search", "delete")
        provider: Vector store provider
        tracer: AITracer instance to use for tracing
        collection: Optional collection name

    Returns:
        Decorator function

    Example:
        >>> tracer = AITracer(some_tracer)
        >>> @trace_vector(operation="search", provider="pgvector", tracer=tracer, collection="docs")
        ... async def search(query, limit=10):
        ...     results = await store.search(query, limit)
        ...     return results
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal tracer
            if tracer is None:
                return await func(*args, **kwargs)

            with tracer.trace_vector_operation(operation, provider, collection) as span:
                try:
                    result = await func(*args, **kwargs)

                    # Record result metrics
                    if hasattr(result, "__len__"):
                        span.set_attribute("results.count", len(result))

                    if operation == "search" and isinstance(result, list):
                        if result and hasattr(result[0], "score"):
                            span.set_attribute("results.top_score", result[0].score)

                    span.set_attribute("status", "success")

                except (
                    Exception
                ) as e:  # tracing decorator must capture all exception types
                    span.set_attribute("status", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.add_event("exception", {"exception": str(e)})
                    raise
                else:
                    return result

        return wrapper

    return decorator


def trace_rag(
    stage: str,
    tracer: AITracer,
    pipeline: str = "default",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to automatically trace RAG pipeline stages.

    Args:
        stage: Stage name (e.g., "retrieval", "ranking", "synthesis")
        tracer: AITracer instance to use for tracing
        pipeline: Pipeline name

    Returns:
        Decorator function

    Example:
        >>> tracer = AITracer(some_tracer)
        >>> @trace_rag(stage="retrieval", tracer=tracer, pipeline="default")
        ... async def retrieve(query):
        ...     documents = await retriever.retrieve(query)
        ...     return documents
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal tracer
            if tracer is None:
                return await func(*args, **kwargs)

            with tracer.trace_rag_stage(stage, pipeline) as span:
                try:
                    result = await func(*args, **kwargs)

                    # Record stage-specific metrics
                    if stage == "retrieval" and hasattr(result, "__len__"):
                        span.set_attribute("documents.retrieved", len(result))

                    if stage == "synthesis" and hasattr(result, "answer"):
                        span.set_attribute("answer.length", len(result.answer))

                    span.set_attribute("status", "success")

                except (
                    Exception
                ) as e:  # tracing decorator must capture all exception types
                    span.set_attribute("status", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.add_event("exception", {"exception": str(e)})
                    raise
                else:
                    return result

        return wrapper

    return decorator
