"""Cohere provider for enterprise-grade NLP with advanced embeddings and RAG.

Cohere specializes in enterprise NLP with best-in-class embeddings, reranking,
and Retrieval-Augmented Generation (RAG) optimized models.

Supported Models:
- command-r-plus: Most capable for RAG and complex tasks
- command-r: Balanced RAG-optimized model
- command: General purpose completion
- command-light: Fast, lightweight completion

Embeddings:
- embed-english-v3.0: 1024-dim English embeddings
- embed-multilingual-v3.0: 1024-dim multilingual embeddings
- embed-english-light-v3.0: 384-dim lightweight embeddings

Features:
- Best-in-class embeddings for semantic search
- Reranking for improved search results
- RAG-optimized models with grounded generation
- Multilingual support (100+ languages)
- Enterprise SLAs and support

Example:
    >>> from lexigram.ai.llm import CohereClient
    >>>
    >>> async with CohereClient(api_key="...") as client:
    ...     # Chat completion
    ...     response = await client.complete(
    ...         model="command-r-plus",
    ...         messages=[{"role": "user", "content": "Explain RAG"}]
    ...     )
    ...
    ...     # Embeddings
    ...     embeddings = await client.embed(
    ...         texts=["Document 1", "Document 2"]
    ...     )
    ...
    ...     # Reranking
    ...     ranked = await client.rerank(
    ...         query="What is AI?",
    ...         documents=["Doc about AI", "Unrelated doc"]
    ...     )

API Documentation: https://docs.cohere.com

"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import aiohttp

from lexigram.ai.llm.clients._cohere_mappers import (
    COHERE_MODELS,
    build_cohere_payload,
)
from lexigram.ai.llm.clients.base import AbstractLLMClient
from lexigram.ai.llm.config import ClientConfig
from lexigram.ai.llm.exceptions import (
    LLMAuthenticationError,
    LLMError,
    LLMModelNotFoundError,
    LLMQuotaExceededError,
    LLMRateLimitError,
)
from lexigram.ai.llm.http.client import ResilientHTTPClient
from lexigram.ai.llm.types import (
    AIError,
    ChatMessage,
    Completion,
    FunctionCall,
    StreamChunk,
    TokenUsage,
    ToolCall,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.web.http_models import HttpStatusError
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result
from lexigram.serialization import loads
from lexigram.validation import SecretStr

logger = get_logger(__name__)

__all__ = ["COHERE_MODELS", "CohereClient"]


class CohereClient(AbstractLLMClient):
    """Client for Cohere's enterprise NLP API.

    Conforms to: :class:`~lexigram.contracts.ai.LLMClientProtocol` protocol via structural typing.

    Supports Chat, Embeddings, and Reranking with:
    - RAG-optimized models (Command R/R+)
    - High-performance embeddings
    - Native reranking support
    """

    def __init__(self, config: ClientConfig) -> None:
        """Initialize Cohere client.

        Args:
            config: LLM configuration
        """
        super().__init__(config=config)
        self._client: ResilientHTTPClient | None = None

    @property
    def api_key(self) -> SecretStr:
        """Get API key from config."""
        return self.config.api_key or SecretStr("")

    @property
    def base_url(self) -> str:
        """Get base URL from config."""
        return self.config.api_base or "https://api.cohere.ai/v1"

    def _get_client(self) -> ResilientHTTPClient:
        """Get or create HTTP client.

        Returns:
            HTTP client instance.
        """
        if self._client is None:
            self._client = ResilientHTTPClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key.get_secret_value()}",
                    "Content-Type": "application/json",
                },
                timeout=self.config.timeout,
                name="cohere-client",
            )
        return self._client

    def _build_payload(
        self,
        messages: list[ChatMessage] | list[dict[str, Any]],
        stream: bool,
        kwargs: dict[str, Any],
    ) -> tuple[ResilientHTTPClient, dict[str, Any], str]:
        """Build the Cohere API request payload from messages."""
        return build_cohere_payload(
            client=self._get_client(),
            messages=messages,
            stream=stream,
            kwargs=kwargs,
            default_model=self.config.model,
            logger=logger,
        )

    async def _do_complete(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> Result[Completion, LLMError]:
        """Generate non-streaming chat completion."""
        try:
            client, payload, model = self._build_payload(
                messages, stream=False, kwargs=kwargs
            )

            # Non-streaming request
            response = await client.post("/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            # Parse response
            content = data.get("text", "")
            tool_calls = None

            # Handle tool calls (normalize to our ToolCall schema)
            if "tool_calls" in data:
                tool_calls = []
                for t in data["tool_calls"]:
                    # Cohere may provide name/args or id/name/arguments
                    name = t.get("name") or ""
                    args = t.get("args") or t.get("arguments") or {}
                    tid = t.get("id") or name or ""
                    tool_calls.append(
                        ToolCall(
                            id=tid,
                            type="function",
                            function=FunctionCall(name=name, arguments=args),
                        ),
                    )

            # Handle citations (for RAG)
            citations = data.get("citations", [])

            usage = {}
            if "meta" in data and "tokens" in data["meta"]:
                tokens = data["meta"]["tokens"]
                usage = {
                    "prompt_tokens": tokens.get("input_tokens", 0),
                    "completion_tokens": tokens.get("output_tokens", 0),
                    "total_tokens": tokens.get("input_tokens", 0)
                    + tokens.get("output_tokens", 0),
                }

            return Ok(
                Completion(
                    content=content,
                    model=model,
                    finish_reason=data.get("finish_reason", "stop"),
                    usage=TokenUsage(
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                    ),
                    tool_calls=tool_calls,
                    metadata={"citations": citations} if citations else {},
                )
            )

        except (OSError, ConnectionError, TimeoutError, RuntimeError, ValueError) as e:
            return self._handle_error_as_result(e)

    async def _do_stream_chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> Result[AsyncIterator[StreamChunk], LLMError]:
        """Start a streaming completion."""
        try:
            client, payload, _ = self._build_payload(
                messages, stream=True, kwargs=kwargs
            )
            return Ok(self._stream_completion(client, payload))
        except (OSError, ConnectionError, TimeoutError, RuntimeError, ValueError) as e:
            return self._handle_error_as_result(e)

    async def _do_chat(
        self,
        messages: list[ChatMessage],
        tools: list[Any] | None = None,
        **kwargs: Any,
    ) -> Result[Completion, LLMError]:
        """Generate completion with optional tool/function calling.

        Converts Lexigram :class:`ToolCall` definitions into Cohere's
        ``tools`` format (``name``, ``description``,
        ``parameter_definitions``) and delegates to ``_do_complete``.

        Args:
            messages: Chat messages.
            tools: Optional tool definitions.
            **kwargs: Additional parameters forwarded to the provider.

        Returns:
            ``Ok(Completion)`` on success or ``Err(LLMError)`` on failure.
        """
        if tools:
            cohere_tools: list[dict[str, Any]] = []
            for tool in tools:
                # Accept both ToolCall objects and raw dicts
                if isinstance(tool, dict):
                    cohere_tools.append(tool)
                    continue
                fn = getattr(tool, "function", tool)
                name: str = getattr(fn, "name", "") or ""
                description: str = getattr(fn, "description", "") or ""
                # Build parameter_definitions from JSON schema if present
                schema: dict[str, Any] = getattr(fn, "parameters", {}) or {}
                properties: dict[str, Any] = schema.get("properties", {})
                required_fields: list[str] = schema.get("required", [])
                param_defs: dict[str, Any] = {}
                for param_name, param_meta in properties.items():
                    param_defs[param_name] = {
                        "description": param_meta.get("description", ""),
                        "type": param_meta.get("type", "str"),
                        "required": param_name in required_fields,
                    }
                cohere_tools.append(
                    {
                        "name": name,
                        "description": description,
                        "parameter_definitions": param_defs,
                    }
                )
            kwargs["tools"] = cohere_tools
        return await self._do_complete(messages, **kwargs)

    async def _stream_completion(
        self,
        client: ResilientHTTPClient,
        payload: dict[str, Any],
    ) -> AsyncIterator[StreamChunk]:
        """Stream chat completion.

        Args:
            client: HTTP client.
            payload: Request payload.

        Yields:
            StreamChunk objects.

        """
        # Support clients that return a coroutine instead of an async context manager
        stream_ctx = client.stream("POST", "/chat", json=payload)

        try:
            if asyncio.iscoroutine(stream_ctx):
                stream_ctx = await stream_ctx
        except aiohttp.ClientResponseError as e:
            # We want to catch specific HTTP errors during setup and convert them
            raise AIError(f"Cohere error: {e}") from e
        except (OSError, ValueError, RuntimeError) as e:
            raise AIError(f"Cohere error: {e}") from e

        try:
            async with stream_ctx as response:
                response.raise_for_status()

                iterator = response.aiter_lines()
                if asyncio.iscoroutine(iterator):
                    iterator = await iterator

                async for line in iterator:
                    if not line:
                        continue

                    try:
                        # Handle bytes or str lines
                        if isinstance(line, (bytes, bytearray)):
                            line_text = line.decode("utf-8")
                        else:
                            line_text = str(line)

                        data = loads(line_text)

                        # Cohere sends different event types
                        event_type = data.get("event_type")

                        if event_type == "text-generation":
                            content = data.get("text", "")
                            if content:
                                yield StreamChunk(
                                    delta=content,
                                    model=payload["model"],
                                    finish_reason=None,
                                )

                        elif event_type == "stream-end":
                            # Final chunk with finish reason
                            yield StreamChunk(
                                delta="",
                                model=payload["model"],
                                finish_reason=data.get("finish_reason", "stop"),
                            )

                    except (ValueError, TypeError) as e:
                        logger.debug("Error parsing stream chunk: %s", e)
                        continue
        except (aiohttp.ClientError, OSError, ValueError, RuntimeError) as e:
            raise AIError(f"Cohere streaming error: {e}") from e

    async def embed(
        self,
        texts: list[str] | str,
        model: str = "embed-english-v3.0",
        input_type: str = "search_document",
        **kwargs: Any,
    ) -> list[list[float]]:
        """Generate embeddings.

        Args:
            texts: Text or list of texts to embed.
            model: Model ID (default: "embed-english-v3.0").
            input_type: Type of input ("search_document", "search_query", "classification", "clustering").
            **kwargs: Additional parameters.

        Returns:
            List of embedding vectors.

        Example:
            >>> # Embed documents
            >>> doc_embeddings = await client.embed(
            ...     texts=["Doc 1", "Doc 2"],
            ...     input_type="search_document"
            ... )
            >>>
            >>> # Embed query
            >>> query_embedding = await client.embed(
            ...     texts="What is AI?",
            ...     input_type="search_query"
            ... )

        """
        try:
            client = self._get_client()

            # Ensure texts is list
            if isinstance(texts, str):
                texts = [texts]

            payload = {
                "texts": texts,
                "model": model,
                "input_type": input_type,
                **kwargs,
            }

            response = await client.post("/embed", json=payload)
            response.raise_for_status()
            data = response.json()

            return data["embeddings"]
        except (
            HttpStatusError,
            aiohttp.ClientError,
            OSError,
            KeyError,
            ValueError,
        ) as e:
            raise AIError(f"Cohere error: {e}") from e

    async def rerank(
        self,
        query: str,
        documents: list[str] | list[dict[str, str]],
        model: str = "rerank-english-v3.0",
        top_n: int | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Rerank documents for a query.

        Args:
            query: Search query.
            documents: List of documents (strings or dicts with 'text' key).
            model: Reranking model (default: "rerank-english-v3.0").
            top_n: Return top N results (default: all).
            **kwargs: Additional parameters.

        Returns:
            List of ranked documents with scores.

        Example:
            >>> results = await client.rerank(
            ...     query="What is machine learning?",
            ...     documents=[
            ...         "ML is a subset of AI...",
            ...         "Unrelated document...",
            ...         "Deep learning uses neural networks..."
            ...     ],
            ...     top_n=2
            ... )
            >>> for result in results:
            ...     print(f"Score: {result['relevance_score']:.3f} - {result['document']['text']}")

        """
        try:
            client = self._get_client()

            payload = {
                "query": query,
                "documents": documents,
                "model": model,
                **kwargs,
            }

            if top_n:
                payload["top_n"] = top_n

            response = await client.post("/rerank", json=payload)
            response.raise_for_status()
            data = response.json()

            return data.get("results", [])
        except (
            HttpStatusError,
            aiohttp.ClientError,
            OSError,
            KeyError,
            ValueError,
        ) as e:
            raise AIError(f"Cohere error: {e}") from e

    def _handle_error_as_result(self, error: Exception) -> Result[Any, LLMError]:
        """Map a caught exception to ``Err`` (recoverable) or re-raise (infra)."""
        if isinstance(error, aiohttp.ClientResponseError):
            if error.status == 401:
                raise LLMAuthenticationError(
                    f"Cohere authentication failed: {error}"
                ) from error
            if error.status == 429:
                return Err(LLMRateLimitError(f"Cohere rate limit exceeded: {error}"))
            if error.status == 402:
                return Err(LLMQuotaExceededError(f"Cohere quota exceeded: {error}"))
            if error.status == 404:
                return Err(LLMModelNotFoundError(f"Cohere model not found: {error}"))
        raise AIError(f"Cohere infrastructure error: {error}") from error

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Perform a lightweight health check against the provider."""
        try:
            client = self._get_client()
            # Simplest probe: list models
            response = await client.get("/models")
            response.raise_for_status()
            return HealthCheckResult(component="cohere", status=HealthStatus.HEALTHY)
        except (OSError, ConnectionError, TimeoutError, RuntimeError) as exc:
            return HealthCheckResult(
                component="cohere",
                status=HealthStatus.UNHEALTHY,
                error=str(exc),
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.close()
            self._client = None
        await super().close()
