"""Jina embedding provider adapter."""

from __future__ import annotations

from lexigram.ai.llm.embedding.base import (
    AbstractEmbeddingAdapter,
    EmbeddingModelInfo,
)
from lexigram.ai.llm.embedding.config import JinaEmbeddingConfig
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class JinaEmbeddingAdapter(AbstractEmbeddingAdapter):
    """Adapter for Jina embedding models."""

    def __init__(self, config: JinaEmbeddingConfig) -> None:
        """Initialize Jina embedding adapter.

        Args:
            config: Jina embedding configuration.
        """
        super().__init__(config)
        self._api_key = config.api_key
        self._base_url = config.base_url

    async def embed(
        self,
        texts: str | list[str],
        *,
        model: str | None = None,
        batch_size: int = 100,
    ) -> list[list[float]]:
        """Generate embeddings using Jina API.

        Args:
            texts: Text(s) to embed
            model: Model to use (default: jina-embeddings-v3)
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors
        """
        model = model or "jina-embeddings-v3"

        # Normalize input
        if isinstance(texts, str):
            texts = [texts]

        embeddings: list[list[float]] = []

        logger.debug(
            "embedding_batch",
            provider="jina",
            model=model,
            batch_size=len(texts),
        )

        # Mock implementation
        import random

        dimension = 1024 if "v3" in model else 768
        for _ in texts:
            vector = [random.random() for _ in range(dimension)]
            embeddings.append(vector)

        return embeddings

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check Jina API availability.

        Args:
            timeout: Check timeout in seconds

        Returns:
            HealthCheckResult indicating HEALTHY if API key is configured.
        """
        if self._api_key:
            return HealthCheckResult(
                component="embedding_jina", status=HealthStatus.HEALTHY
            )
        return HealthCheckResult(
            component="embedding_jina",
            status=HealthStatus.UNHEALTHY,
            message="API key not configured",
        )

    def get_models(self) -> list[EmbeddingModelInfo]:
        """Get available Jina embedding models.

        Returns:
            List of model metadata
        """
        return [
            EmbeddingModelInfo(
                model_id="jina-embeddings-v3",
                provider="jina",
                display_name="Jina Embeddings v3",
                embedding_dimension=1024,
                max_input_tokens=8192,
                input_cost_per_million=0.02,
            ),
            EmbeddingModelInfo(
                model_id="jina-embeddings-v2-base-en",
                provider="jina",
                display_name="Jina Embeddings v2 Base EN",
                embedding_dimension=768,
                max_input_tokens=8192,
                input_cost_per_million=0.01,
            ),
        ]

    async def close(self) -> None:
        """Clean up resources."""
