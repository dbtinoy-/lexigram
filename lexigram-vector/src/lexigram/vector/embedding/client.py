"""OpenAI-compatible embedding client backed by aiohttp."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Self

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger
from lexigram.vector.embedding.config import EmbeddingClientConfig

if TYPE_CHECKING:
    import aiohttp

logger = get_logger(__name__)


class OpenAICompatibleEmbeddingClient:
    """Async embedding client for any OpenAI-compatible ``/v1/embeddings`` endpoint.

    Implements ``EmbeddingClientProtocol`` from ``lexigram-contracts`` so it can
    be registered in the DI container and consumed by ``DocumentVectorStoreAdapter``
    or any other service that needs text embeddings.

    Supports any backend exposing the OpenAI embeddings API:
    - text-embeddings-inference (self-hosted, local docker-compose)
    - LM Studio
    - OpenAI
    - Cohere (OpenAI-compat mode)

    Texts are split into ``config.batch_size`` chunks and embedded in parallel.
    The underlying ``aiohttp.ClientSession`` is created lazily on the first call
    and reused across all requests until ``close()`` is called.

    Example::

        config = EmbeddingClientConfig(
            api_base="http://fastembed/v1",
            model="nomic-ai/nomic-embed-text-v1.5",
            dimension=768,
        )
        client = OpenAICompatibleEmbeddingClient(config)
        vectors = await client.embed(["dog limping", "cat vomiting"])
        await client.close()
    """

    def __init__(self, config: EmbeddingClientConfig) -> None:
        """Initialise the embedding client.

        Args:
            config: Client configuration (URL, model, dimension, timeout, batch size).
        """
        self._config = config
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # EmbeddingClientProtocol
    # ------------------------------------------------------------------

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Splits input into batches of ``config.batch_size``, sends each batch to
        the ``/embeddings`` endpoint, then concatenates results preserving order.

        Args:
            texts: Texts to embed. Empty list returns immediately.

        Returns:
            One embedding vector per input text, in the same order.

        Raises:
            RuntimeError: If the HTTP request fails or the response is malformed.
        """
        if not texts:
            return []

        session = await self._get_session()
        results: list[list[float]] = []
        batch_size = self._config.batch_size

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_vectors = await self._embed_batch(session, batch)
            results.extend(batch_vectors)

        return results

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Verify the embedding endpoint is reachable.

        Embeds a short test string with a reduced timeout.

        Args:
            timeout: Connection timeout in seconds.

        Returns:
            Healthy if the endpoint responds correctly, Unhealthy otherwise.
        """
        try:
            session = await self._get_session()
            await self._embed_batch(session, ["ping"], timeout_override=timeout)
            return HealthCheckResult(
                component="embedding_client",
                status=HealthStatus.HEALTHY,
                details={
                    "embedding_api": self._config.api_base,
                    "model": self._config.model,
                },
            )
        except Exception as exc:  # noqa: BLE001
            return HealthCheckResult(
                component="embedding_client",
                status=HealthStatus.UNHEALTHY,
                error=str(exc),
                details={"embedding_api": self._config.api_base},
            )

    async def close(self) -> None:
        """Close the underlying aiohttp session and release connections."""
        async with self._lock:
            if self._session is not None and not self._session.closed:
                await self._session.close()
                self._session = None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        """Return the shared session, creating it if needed (thread-safe)."""
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    self._session = self._create_session()
        return self._session

    def _create_session(self) -> aiohttp.ClientSession:
        """Build an aiohttp ClientSession with appropriate headers and timeout."""
        import aiohttp

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        timeout = aiohttp.ClientTimeout(total=self._config.timeout)
        return aiohttp.ClientSession(headers=headers, timeout=timeout)

    async def _embed_batch(
        self,
        session: aiohttp.ClientSession,
        texts: list[str],
        timeout_override: float | None = None,
    ) -> list[list[float]]:
        """Send one batch to the embedding endpoint and return vectors.

        Args:
            session: Shared aiohttp session.
            texts: Texts for this batch.
            timeout_override: Optional per-request timeout (used by health_check).

        Returns:
            List of embedding vectors matching ``texts`` order.

        Raises:
            RuntimeError: On HTTP error or unexpected response shape.
        """
        import aiohttp

        url = f"{self._config.api_base.rstrip('/')}/embeddings"

        # Build payload based on format
        if self._config.format == "fastembed":
            # FastEmbed: {"texts": [...], "model": "..."}
            payload = {"texts": texts, "model": self._config.model}
        elif self._config.format == "cohere":
            # Cohere: {"texts": [...], "model": "..."}
            payload = {"texts": texts, "model": self._config.model}
        else:
            # OpenAI default: {"input": [...], "model": "..."}
            payload = {"model": self._config.model, "input": texts}

        kwargs: dict[str, Any] = {}
        if timeout_override is not None:
            kwargs["timeout"] = aiohttp.ClientTimeout(total=timeout_override)

        async with session.post(url, json=payload, **kwargs) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"Embedding API error {resp.status}: {body[:200]}")
            data = await resp.json()

        # Parse response based on format
        if self._config.format in {"fastembed", "cohere"}:
            # FastEmbed/Cohere (nested): {"results": [{"embedding": [...]}, ...]}
            # FastEmbed (flat): {"embeddings": [[...], ...]}  (infinity server)
            raw = data.get("results", data.get("embeddings", []))
            if not raw:
                raise RuntimeError(
                    f"Embedding API returned empty results for {len(texts)} input(s)"
                )
            if isinstance(raw[0], list):
                vectors = raw
            else:
                vectors = [item["embedding"] for item in raw]
        else:
            # OpenAI: {"data": [{"index": 0, "embedding": [...]}, ...]}
            raw = data.get("data", [])
            if not raw:
                raise RuntimeError(
                    f"Embedding API returned empty data for {len(texts)} input(s)"
                )
            # Sort by index to guarantee order (some backends may reorder)
            raw.sort(key=lambda x: x.get("index", 0))
            vectors = [item["embedding"] for item in raw]

        logger.debug(
            "embedding_batch_complete",
            texts=len(texts),
            dim=len(vectors[0]) if vectors else 0,
            model=self._config.model,
        )
        return vectors

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()


__all__ = ["OpenAICompatibleEmbeddingClient"]
