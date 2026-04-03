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

from typing import TYPE_CHECKING, Any

from lexigram.contracts.ai.callbacks import CallbackHandlerProtocol
from lexigram.contracts.ai.llm import ChatMessage, Completion
from lexigram.contracts.observability.tracing import SpanProtocol as Span
from lexigram.contracts.observability.tracing import TracerProtocol as Tracer
from lexigram.di.decorators import inject

if TYPE_CHECKING:
    from contextlib import AbstractContextManager as ContextManager


# TracerProtocol is an alias for Tracer in contracts
TracerProtocol = Tracer


@inject
class AITracer(CallbackHandlerProtocol):
    """Distributed tracer for intelligence operations.

    Provides span management and context propagation for:
    - LLM completions and streaming
    - Vector store operations
    - RAG pipeline execution
    - Embedding generation

    Also implements CallbackHandlerProtocol for event-driven tracing.

    Example:
        >>> tracer = AITracer()
        >>> async with tracer.trace_llm_call("openai", "gpt-4") as span:
        ...     response = await client.complete(messages)
        ...     span.set_attribute("tokens.total", response.usage.total_tokens)
        ...     span.set_attribute("cost", response.cost)
    """

    def __init__(self, tracer: Tracer) -> None:
        """Initialize intelligence tracer.

        Args:
            tracer: Tracer instance to use for tracing.
        """
        self.tracer = tracer

    def trace_llm_call(
        self,
        provider: str,
        model: str,
        **attributes: Any,
    ) -> ContextManager[Span]:
        """Create a span for LLM API call.

        Args:
            provider: LLM provider name (e.g., "openai", "anthropic")
            model: Model name (e.g., "gpt-4", "claude-3-opus")
            **attributes: Additional span attributes

        Returns:
            Span context manager

        Example:
            >>> tracer = AITracer()
            >>> with tracer.trace_llm_call("openai", "gpt-4") as span:
            ...     response = await client.complete(messages)
            ...     span.set_attribute("tokens.total", response.usage.total_tokens)
        """
        span_attributes = {
            "llm.provider": provider,
            "llm.model": model,
            "operation.type": "llm.completion",
            **attributes,
        }
        return self.tracer.start_span(
            name=f"llm.{provider}.{model}",
            attributes=span_attributes,
        )

    def trace_operation(
        self,
        name: str,
        **attrs: Any,
    ) -> ContextManager[Span]:
        """Generic operation tracing helper.

        This mirrors the `Tracer.trace_operation` API and is used by
        worker code that needs a generic operation span (e.g., document
        parsing/chunking).
        """
        return self.tracer.start_span(name=name, attributes=attrs or {})

    def trace_vector_operation(
        self,
        operation: str,
        provider: str,
        collection: str | None = None,
        **attributes: Any,
    ) -> ContextManager[Span]:
        """Create a span for vector store operation.

        Args:
            operation: Operation type (e.g., "add", "search", "delete")
            provider: Vector store provider (e.g., "pgvector", "chroma")
            collection: Optional collection/table name
            **attributes: Additional span attributes

        Returns:
            Span context manager

        Example:
            >>> with tracer.trace_vector_operation("search", "pgvector", "documents") as span:
            ...     results = await store.search(query, limit=10)
            ...     span.set_attribute("results.count", len(results))
        """
        span_attributes = {
            "vector.operation": operation,
            "vector.provider": provider,
            "operation.type": "vector.operation",
            **attributes,
        }
        if collection:
            span_attributes["vector.collection"] = collection

        return self.tracer.start_span(
            name=f"vector.{operation}.{provider}",
            attributes=span_attributes,
        )

    def trace_embedding_operation(
        self,
        model: str,
        batch_size: int | None = None,
        **attributes: Any,
    ) -> ContextManager[Span]:
        """Create a span for embedding generation.

        Args:
            model: Embedding model name
            batch_size: Optional number of texts being embedded
            **attributes: Additional span attributes

        Returns:
            Span context manager

        Example:
            >>> with tracer.trace_embedding_operation("text-embedding-ada-002", 5) as span:
            ...     embeddings = await embedder.embed(texts)
            ...     span.set_attribute("embeddings.dimensions", len(embeddings[0]))
        """
        span_attributes = {
            "embedding.model": model,
            "operation.type": "embedding.generation",
            **attributes,
        }
        if batch_size is not None:
            span_attributes["embedding.batch_size"] = batch_size

        return self.tracer.start_span(
            name=f"embedding.{model}",
            attributes=span_attributes,
        )

    def trace_rag_stage(
        self,
        stage: str,
        pipeline: str = "default",
        **attributes: Any,
    ) -> ContextManager[Span]:
        """Create a span for RAG pipeline stage.

        Args:
            stage: Stage name (e.g., "retrieval", "ranking", "synthesis")
            pipeline: Pipeline name
            **attributes: Additional span attributes

        Returns:
            Span context manager

        Example:
            >>> with tracer.trace_rag_stage("retrieval", "default") as span:
            ...     documents = await retriever.retrieve(query)
            ...     span.set_attribute("documents.count", len(documents))
        """
        span_attributes = {
            "rag.stage": stage,
            "rag.pipeline": pipeline,
            "operation.type": "rag.stage",
            **attributes,
        }

        return self.tracer.start_span(
            name=f"rag.{stage}",
            attributes=span_attributes,
        )

    def trace_rag_query(
        self,
        query: str,
        pipeline: str = "default",
        **attributes: Any,
    ) -> ContextManager[Span]:
        """Create a span for complete RAG query.

        Args:
            query: Query text
            pipeline: Pipeline name
            **attributes: Additional span attributes

        Returns:
            Span context manager

        Example:
            >>> with tracer.trace_rag_query("What is Python?") as span:
            ...     result = await rag_pipeline.query(query)
            ...     span.set_attribute("answer.length", len(result.answer))
        """
        span_attributes = {
            "rag.query": query[:100],  # Truncate long queries
            "rag.pipeline": pipeline,
            "operation.type": "rag.query",
            **attributes,
        }

        return self.tracer.start_span(
            name="rag.query",
            attributes=span_attributes,
        )

    def get_current_span(self) -> Span | None:
        """Get the currently active span.

        Returns:
            Current span or None
        """
        return self.tracer.get_current_span()

    async def on_llm_start(
        self,
        messages: list[ChatMessage],
        model: str,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM call starts."""
        span_attributes = {
            "llm.model": model,
            "operation.type": "llm.start",
            **kwargs,
        }
        self.tracer.start_span(name=f"llm.{model}", attributes=span_attributes)

    async def on_llm_new_token(
        self,
        token: str,
        **kwargs: Any,
    ) -> None:
        """Called for each new token in a streaming LLM response."""
        span = self.tracer.get_current_span()
        if span:
            span.add_event("llm.token", {"token": token})

    async def on_llm_end(
        self,
        response: Completion,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM call completes successfully."""
        span = self.tracer.get_current_span()
        if span:
            span.add_event("llm.end", {"model": response.model})
            span.end()

    async def on_llm_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM call fails."""
        span = self.tracer.get_current_span()
        if span:
            span.add_event("llm.error", {"error": str(error)})
            span.set_status("error")
            span.end()

    async def on_chain_start(
        self,
        name: str,
        inputs: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when a chain/pipeline starts executing."""
        self.tracer.start_span(
            name=f"chain.{name}", attributes={"chain.name": name, **kwargs}
        )

    async def on_chain_end(
        self,
        name: str,
        outputs: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when a chain/pipeline completes."""
        span = self.tracer.get_current_span()
        if span:
            span.add_event("chain.end", {"chain.name": name})
            span.end()

    async def on_tool_start(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when a tool starts executing."""
        self.tracer.start_span(
            name=f"tool.{tool_name}",
            attributes={"tool.name": tool_name, "tool.args": arguments, **kwargs},
        )

    async def on_tool_end(
        self,
        tool_name: str,
        result: Any,
        **kwargs: Any,
    ) -> None:
        """Called when a tool finishes executing."""
        span = self.tracer.get_current_span()
        if span:
            span.add_event("tool.end", {"tool.name": tool_name})
            span.end()

    async def on_agent_action(
        self,
        action: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when an agent takes an action."""
        span = self.tracer.get_current_span()
        if span:
            span.add_event("agent.action", action)

    async def on_agent_finish(
        self,
        response: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when an agent finishes executing."""
        span = self.tracer.get_current_span()
        if span:
            span.add_event("agent.finish", response)
            span.end()

    async def on_retriever_start(
        self,
        query: str,
        **kwargs: Any,
    ) -> None:
        """Called when a retriever starts a search."""
        self.tracer.start_span(
            name="retriever.search",
            attributes={"retriever.query": query, **kwargs},
        )

    async def on_retriever_end(
        self,
        documents: list[Any],
        **kwargs: Any,
    ) -> None:
        """Called when a retriever completes a search."""
        span = self.tracer.get_current_span()
        if span:
            span.add_event("retriever.end", {"documents.count": len(documents)})
            span.end()
