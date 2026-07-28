"""Streaming response adapters for unified multi-provider streaming.

Provides a unified interface for streaming responses from different LLM
providers, with automatic chunk aggregation, token tracking, and metrics.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime

from lexigram.ai.llm.types import StreamChunk
from lexigram.contracts.ai.models import ModelRequest, ModelResponse
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class StreamingMetrics:
    """Metrics for a streaming response.

    Attributes:
        total_chunks: Number of chunks received
        total_tokens: Total tokens in response
        total_input_tokens: Input tokens from request
        total_latency_ms: Total time from request to completion
        time_to_first_chunk_ms: Time until first chunk received
        chunks_per_second: Average chunks received per second
    """

    total_chunks: int = 0
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_latency_ms: float = 0.0
    time_to_first_chunk_ms: float | None = None
    chunks_per_second: float = 0.0


class StreamingResponse:
    """Manages streaming response state and aggregation.

    Tracks incoming chunks, aggregates content, and maintains metrics
    about the streaming response.
    """

    def __init__(
        self,
        provider: str,
        model_id: str,
    ) -> None:
        """Initialize streaming response tracker.

        Args:
            provider: Provider name
            model_id: Model ID being used
        """
        self.provider = provider
        self.model_id = model_id
        self.chunks: list[StreamChunk] = []
        self.start_time = datetime.now(UTC)
        self.first_chunk_time: datetime | None = None
        self.finished = False
        self.finish_reason: str | None = None

    def add_chunk(self, chunk: StreamChunk) -> None:
        """Add a chunk to the response.

        Args:
            chunk: Chunk to add
        """
        if self.first_chunk_time is None:
            self.first_chunk_time = datetime.now(UTC)

        self.chunks.append(chunk)
        logger.debug(
            "stream_chunk_received",
            provider=self.provider,
            chunk_index=chunk.index,
            chunk_content_len=len(
                (chunk.content if chunk.content is not None else chunk.delta) or ""
            ),
        )

    def finish(self, reason: str | None = None) -> None:
        """Mark streaming as finished.

        Args:
            reason: Why the stream ended
        """
        self.finished = True
        self.finish_reason = reason
        if self.chunks:
            self.finish_reason = self.chunks[-1].finish_reason or reason

    def get_aggregated_content(self) -> str:
        """Get concatenated answer content of all non-thinking chunks.

        Returns:
            Full response text (thinking chunks excluded)
        """
        return "".join(
            ((chunk.content if chunk.content is not None else chunk.delta) or "")
            for chunk in self.chunks
            if not chunk.is_thinking
        )

    def get_aggregated_thinking(self) -> str:
        """Get concatenated thinking content from all thinking chunks.

        Returns:
            Full thinking text, empty string when thinking was not enabled.
        """
        return "".join(
            chunk.thinking_delta or "" for chunk in self.chunks if chunk.is_thinking
        )

    def get_metrics(self) -> StreamingMetrics:
        """Calculate streaming metrics.

        Returns:
            StreamingMetrics with aggregate values
        """
        now = datetime.now(UTC)
        total_latency = (now - self.start_time).total_seconds() * 1000

        time_to_first = None
        if self.first_chunk_time:
            time_to_first = (
                self.first_chunk_time - self.start_time
            ).total_seconds() * 1000

        total_tokens = sum(chunk.tokens_used for chunk in self.chunks)
        if total_tokens == 0 and self.chunks:
            total_tokens = len(self.chunks)
        chunks_per_sec = len(self.chunks) / max(total_latency / 1000, 0.001)

        return StreamingMetrics(
            total_chunks=len(self.chunks),
            total_tokens=total_tokens,
            total_latency_ms=total_latency,
            time_to_first_chunk_ms=time_to_first,
            chunks_per_second=chunks_per_sec,
        )

    async def to_model_response(
        self,
        input_tokens: int = 0,
    ) -> ModelResponse:
        """Convert streaming response to standard ModelResponse.

        Args:
            input_tokens: Number of input tokens from request

        Returns:
            ModelResponse with aggregated content
        """
        return ModelResponse(
            content=self.get_aggregated_content(),
            tokens_used=(
                sum(chunk.tokens_used for chunk in self.chunks) or len(self.chunks)
            ),
            stop_reason=self.finish_reason,
            extra_metadata={
                "provider": self.provider,
                "model_id": self.model_id,
                "chunks": len(self.chunks),
                "time_to_first_chunk_ms": (
                    self.get_metrics().time_to_first_chunk_ms or 0.0
                ),
                "input_tokens": input_tokens,
            },
        )


class AbstractStreamingAdapter(ABC):
    """Abstract base for streaming response adapters.

    Provides a unified interface for streaming from different
    LLM providers. Concrete implementations wrap provider-specific
    streaming clients.
    """

    def __init__(self, provider: str) -> None:
        """Initialize streaming adapter.

        Args:
            provider: Provider name
        """
        self.provider = provider

    @abstractmethod
    def stream(
        self,
        request: ModelRequest,
        model_id: str,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response from LLM provider.

        Args:
            request: The model request
            model_id: Model to use

        Yields:
            StreamChunk objects as they arrive

        Raises:
            StreamingError: If streaming fails
        """

    async def stream_to_response(
        self,
        request: ModelRequest,
        model_id: str,
    ) -> StreamingResponse:
        """Stream and aggregate response into StreamingResponse.

        Args:
            request: The model request
            model_id: Model to use

        Returns:
            Completed StreamingResponse with all chunks

        Raises:
            StreamingError: If streaming fails
        """
        response = StreamingResponse(self.provider, model_id)

        async for chunk in self.stream(request, model_id):
            response.add_chunk(chunk)

        response.finish()
        logger.info(
            "stream_completed",
            provider=self.provider,
            model_id=model_id,
            total_chunks=len(response.chunks),
        )

        return response


class OpenAIStreamingAdapter(AbstractStreamingAdapter):
    """Streaming adapter for OpenAI provider."""

    async def stream(
        self,
        request: ModelRequest,
        model_id: str,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response from OpenAI.

        Args:
            request: The model request
            model_id: Model to use

        Yields:
            StreamChunk objects as they arrive
        """

        # Placeholder: In real implementation, call OpenAI streaming API
        # For now, simulate a few chunks
        async def generate_chunks() -> AsyncIterator[StreamChunk]:
            chunks = [
                StreamChunk(delta="Hello ", index=0),
                StreamChunk(delta="from ", index=1),
                StreamChunk(delta="OpenAI", index=2, finish_reason="stop"),
            ]
            for chunk in chunks:
                await asyncio.sleep(0.01)  # Simulate network latency
                yield chunk

        async for chunk in generate_chunks():
            yield chunk


class AnthropicStreamingAdapter(AbstractStreamingAdapter):
    """Streaming adapter for Anthropic provider."""

    async def stream(
        self,
        request: ModelRequest,
        model_id: str,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response from Anthropic.

        Args:
            request: The model request
            model_id: Model to use

        Yields:
            StreamChunk objects as they arrive
        """

        # Placeholder: In real implementation, call Anthropic streaming API
        async def generate_chunks() -> AsyncIterator[StreamChunk]:
            chunks = [
                StreamChunk(delta="Hello ", index=0),
                StreamChunk(delta="from ", index=1),
                StreamChunk(delta="Anthropic", index=2, finish_reason="end_turn"),
            ]
            for chunk in chunks:
                await asyncio.sleep(0.01)
                yield chunk

        async for chunk in generate_chunks():
            yield chunk


class GoogleStreamingAdapter(AbstractStreamingAdapter):
    """Streaming adapter for Google provider."""

    async def stream(
        self,
        request: ModelRequest,
        model_id: str,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response from Google.

        Args:
            request: The model request
            model_id: Model to use

        Yields:
            StreamChunk objects as they arrive
        """

        # Placeholder: In real implementation, call Google streaming API
        async def generate_chunks() -> AsyncIterator[StreamChunk]:
            chunks = [
                StreamChunk(delta="Hello ", index=0),
                StreamChunk(delta="from ", index=1),
                StreamChunk(delta="Google", index=2, finish_reason="stop"),
            ]
            for chunk in chunks:
                await asyncio.sleep(0.01)
                yield chunk

        async for chunk in generate_chunks():
            yield chunk


class StreamingOrchestrator:
    """Orchestrates streaming across multiple providers.

    Similar to LLMOrchestrator but for streaming responses,
    with automatic provider fallback and metrics tracking.
    """

    def __init__(self) -> None:
        """Initialize streaming orchestrator."""
        self.adapters: dict[str, AbstractStreamingAdapter] = {}
        self.lock = asyncio.Lock()
        logger.info("streaming_orchestrator_created")

    async def register_adapter(
        self,
        provider: str,
        adapter: AbstractStreamingAdapter,
    ) -> None:
        """Register a streaming adapter for a provider.

        Args:
            provider: Provider name
            adapter: AbstractStreamingAdapter implementation
        """
        async with self.lock:
            self.adapters[provider] = adapter
            logger.info(
                "streaming_adapter_registered",
                provider=provider,
                adapter_type=type(adapter).__name__,
            )

    async def stream(
        self,
        request: ModelRequest,
        provider: str,
        model_id: str,
    ) -> StreamingResponse:
        """Stream response from a provider.

        Args:
            request: The model request
            provider: Provider to use
            model_id: Model to use

        Returns:
            Completed StreamingResponse

        Raises:
            ValueError: If provider not registered
            StreamingError: If streaming fails
        """
        if provider not in self.adapters:
            raise ValueError(f"No streaming adapter for provider: {provider}")

        adapter = self.adapters[provider]
        response = await adapter.stream_to_response(request, model_id)

        logger.info(
            "stream_orchestrated",
            provider=provider,
            model_id=model_id,
            metrics=response.get_metrics(),
        )

        return response

    async def stream_with_fallback(
        self,
        request: ModelRequest,
        providers: list[str],
        model_ids: dict[str, str],
    ) -> StreamingResponse:
        """Stream with automatic fallback to alternate providers.

        Tries providers in order until one succeeds.

        Args:
            request: The model request
            providers: List of providers to try in order
            model_ids: Dict mapping provider to model_id

        Returns:
            Completed StreamingResponse from first successful provider

        Raises:
            ValueError: If no providers available or streaming fails
        """
        last_error: Exception | None = None

        for provider in providers:
            if provider not in self.adapters:
                logger.warning(
                    "streaming_provider_not_registered",
                    provider=provider,
                )
                continue

            try:
                model_id = model_ids.get(provider)
                if not model_id:
                    logger.warning(
                        "streaming_provider_no_model",
                        provider=provider,
                    )
                    continue

                response = await self.stream(request, provider, model_id)
                logger.info(
                    "stream_fallback_success",
                    provider=provider,
                    model_id=model_id,
                )

                return response

            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "streaming_provider_failed",
                    provider=provider,
                    error=str(e),
                )
                last_error = e
                continue

        error_msg = f"Streaming failed for all providers: {last_error}"
        logger.error("streaming_all_providers_failed")
        raise ValueError(error_msg) from last_error

    async def stream_with_chunking(
        self,
        request: ModelRequest,
        provider: str,
        model_id: str,
        chunk_callback=None,
    ) -> StreamingResponse:
        """Stream with callback for each chunk (no aggregation).

        Useful for real-time processing of chunks without waiting
        for full response.

        Args:
            request: The model request
            provider: Provider to use
            model_id: Model to use
            chunk_callback: Async callback(chunk) for each chunk

        Returns:
            Completed StreamingResponse
        """
        if provider not in self.adapters:
            raise ValueError(f"No streaming adapter for provider: {provider}")

        adapter = self.adapters[provider]
        response = StreamingResponse(provider, model_id)

        async for chunk in adapter.stream(request, model_id):
            response.add_chunk(chunk)
            if chunk_callback:
                await chunk_callback(chunk)

        response.finish()
        return response
