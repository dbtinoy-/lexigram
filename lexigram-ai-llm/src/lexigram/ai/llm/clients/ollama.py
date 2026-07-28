"""Ollama LLM client implementation for local models.

Production-ready implementation with Ollama API integration.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator
from datetime import UTC, datetime
from typing import Any

from lexigram.ai.llm.clients._message_utils import serialize_text_for_ollama
from lexigram.ai.llm.clients.base import AbstractLLMClient
from lexigram.ai.llm.config import ClientConfig
from lexigram.ai.llm.exceptions import LLMError
from lexigram.ai.llm.multimodal.fetcher import fetch_image_as_base64
from lexigram.ai.llm.types import (
    AIError,
    ChatMessage,
    Completion,
    StreamChunk,
    TokenUsage,
    ToolCall,
)
from lexigram.contracts.ai.multimodal import ImageUrlPart
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.result import Ok, Result


class OllamaClient(AbstractLLMClient):
    """Ollama LLM client for local models.

    Conforms to: :class:`~lexigram.contracts.ai.LLMClientProtocol` protocol via structural typing.

    Supports running LLMs locally with Ollama:
    - Llama 3, Mistral, Phi, and other open models
    - Streaming responses
    - Zero API costs
    - Full data privacy

    Example:
        >>> from lexigram.ai import ClientConfig
        >>> config = ClientConfig(
        ...     provider="ollama",
        ...     model="llama3:8b",
        ...     api_base="http://localhost:11434"
        ... )
        >>> client = OllamaClient(config)
        >>> completion = await client.complete([
        ...     ChatMessage(role="user", content="Hello!")
        ... ])
    """

    def __init__(self, config: ClientConfig):
        """Initialize Ollama client.

        Args:
            config: LLM configuration

        Raises:
            ImportError: If ollama package is not installed
        """
        super().__init__(config=config)
        self.model_manager = None
        self.current_model = config.model

        try:
            from ollama import AsyncClient
        except ImportError as e:
            raise ImportError(
                "Ollama client requires 'ollama' package. "
                "Install with: pip install lexigram-intelligence[ollama]",
            ) from e

        # Ollama typically runs on localhost:11434
        host = config.api_base or "http://localhost:11434"
        self.client = AsyncClient(host=host)
        self._closed = False

    async def _ensure_model_loaded(self, model_name: str) -> None:
        """Ensure the specified model is loaded (no-op without an injected model_manager)."""
        if model_name != self.current_model and self.model_manager is not None:
            await self.model_manager.switch_provider("ollama")
            await self.model_manager.load_model(model_name)
            self.current_model = model_name

    async def _serialize_messages_for_ollama(
        self, messages: list[ChatMessage]
    ) -> list[dict[str, Any]]:
        """Serialize ChatMessages to Ollama wire format, pre-fetching URL images.

        Builds Ollama-compatible message dicts with ``content`` (text) and optional
        ``images`` (list of raw base64 strings, no data URI prefix). ``ImageUrlPart``
        entries are fetched via ``fetch_image_as_base64`` before serialization.

        Args:
            messages: ChatMessages to serialize.

        Returns:
            List of Ollama message dicts with optional ``images`` key.
        """
        result: list[dict[str, Any]] = []
        for msg in messages:
            content = msg.content
            # Pre-fetch ImageUrlParts before passing to sync serializer
            if isinstance(content, list):
                resolved: list[Any] = []
                for part in content:
                    if isinstance(part, ImageUrlPart):
                        resolved.append(await fetch_image_as_base64(part.url))
                    else:
                        resolved.append(part)
                content = resolved

            text, images = serialize_text_for_ollama(content)
            entry: dict[str, Any] = {
                "role": msg.role.value,
                "content": text,
            }
            if images:
                entry["images"] = images
            result.append(entry)
        return result

    async def _do_complete(
        self,
        messages: list[ChatMessage],
        **kwargs,
    ) -> Result[Completion, LLMError]:
        """Generate completion from messages.

        Args:
            messages: Chat messages
            **kwargs: Additional Ollama parameters

        Returns:
            ``Ok(Completion)`` on success.

        Raises:
            AIError: If request fails (all Ollama errors are infrastructure).
        """
        try:
            model_name = kwargs.pop("model", self.config.model)
            await self._ensure_model_loaded(model_name)

            # Convert messages to Ollama format
            ollama_messages = await self._serialize_messages_for_ollama(messages)

            # Merge config defaults with kwargs
            params = {
                "model": model_name,
                "messages": ollama_messages,
                "options": {
                    "temperature": kwargs.pop("temperature", self.config.temperature),
                    "num_predict": kwargs.pop("max_tokens", self.config.max_tokens),
                },
                **kwargs,
            }

            # Inject thinking suppress for models that support it
            if self.config.thinking is not None and self.config.thinking.suppress:
                params["think"] = False

            # Make API call
            response = await self.client.chat(**params)

            # Convert to our Completion type
            return Ok(
                Completion(
                    content=response["message"]["content"],
                    model=response["model"],
                    finish_reason="stop",
                    usage=TokenUsage(
                        prompt_tokens=response.get("prompt_eval_count", 0),
                        completion_tokens=response.get("eval_count", 0),
                        total_tokens=response.get("prompt_eval_count", 0)
                        + response.get("eval_count", 0),
                    ),
                    metadata={
                        "total_duration": response.get("total_duration"),
                        "load_duration": response.get("load_duration"),
                    },
                    timestamp=datetime.now(UTC),
                )
            )

        except (LLMError, ValueError, RuntimeError, OSError, ConnectionError) as e:
            msg = f"Ollama completion failed: {e}"
            raise AIError(msg) from e

    async def _do_stream_chat(
        self,
        messages: list[ChatMessage],
        **kwargs,
    ) -> Result[AsyncIterator[StreamChunk], LLMError]:
        """Start streaming completion (protocol-aligned method).

        Args:
            messages: Chat messages
            **kwargs: Additional parameters

        Returns:
            ``Ok(AsyncIterator[StreamChunk])`` on success.

        Raises:
            AIError: If setting up the stream fails.
        """
        return Ok(self._stream_impl(messages, **kwargs))

    async def _stream_impl(
        self,
        messages: list[ChatMessage],
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Internal async generator for streaming.

        Args:
            messages: Chat messages
            **kwargs: Additional parameters

        Yields:
            StreamChunk objects

        Raises:
            AIError: If streaming fails
        """
        try:
            model_name = kwargs.pop("model", self.config.model)
            await self._ensure_model_loaded(model_name)

            # Convert messages to Ollama format
            ollama_messages = await self._serialize_messages_for_ollama(messages)

            # Merge config defaults with kwargs
            params = {
                "model": model_name,
                "messages": ollama_messages,
                "stream": True,
                "options": {
                    "temperature": kwargs.pop("temperature", self.config.temperature),
                    "num_predict": kwargs.pop("max_tokens", self.config.max_tokens),
                },
                **kwargs,
            }

            # Inject thinking suppress for models that support it
            if self.config.thinking is not None and self.config.thinking.suppress:
                params["think"] = False

            # Stream API call
            index = 0
            stream = await self.client.chat(**params)
            async for chunk in stream:
                if "message" in chunk and "content" in chunk["message"]:
                    delta = chunk["message"]["content"]
                    if delta:
                        yield StreamChunk(
                            delta=delta,
                            model=chunk.get("model", self.config.model),
                            finish_reason="stop" if chunk.get("done") else None,
                            index=index,
                        )
                        index += 1

        except (LLMError, ValueError, RuntimeError, OSError, ConnectionError) as e:
            msg = f"Ollama streaming failed: {e}"
            raise AIError(msg) from e

    async def _do_chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolCall] | None = None,
        **kwargs,
    ) -> Result[Completion, LLMError]:
        """Generate completion (tools not supported in Ollama yet).

        Args:
            messages: Chat messages
            tools: Optional tools (ignored for now)
            **kwargs: Additional parameters

        Returns:
            ``Ok(Completion)`` on success.  ``Err(LLMError)`` on failure.
        """
        # Ollama doesn't support tool calling yet
        # Delegate to regular complete
        return await self._do_complete(messages, **kwargs)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Perform a lightweight health check against the Ollama daemon.

        Calls ``list()`` to verify the daemon is running and reachable.

        Args:
            timeout: Maximum seconds to wait for the response.

        Returns:
            :class:`~lexigram.contracts.core.health.HealthCheckResult`.
        """
        try:
            models_response = await self.client.list()
            model_names = [m.model for m in models_response.models]
            return HealthCheckResult(
                component="llm.ollama",
                status=HealthStatus.HEALTHY,
                details={
                    "provider": "ollama",
                    "model": self.current_model,
                    "available_models": model_names,
                },
            )
        except (OSError, ConnectionError, TimeoutError, RuntimeError) as exc:
            return HealthCheckResult(
                component="llm.ollama",
                status=HealthStatus.UNHEALTHY,
                error=str(exc),
            )

    async def close(self) -> None:
        """Close Ollama client."""
        if not self._closed:
            self._closed = True
        await super().close()
