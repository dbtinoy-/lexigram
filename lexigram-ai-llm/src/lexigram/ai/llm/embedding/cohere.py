"""Cohere embedding provider adapter."""

from __future__ import annotations

from lexigram.ai.llm.embedding.base import (
    AbstractEmbeddingAdapter,
    EmbeddingModelInfo,
)
from lexigram.ai.llm.embedding.config import CohereEmbeddingConfig
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class CohereEmbeddingAdapter(AbstractEmbeddingAdapter):
    """Adapter for Cohere embedding models."""

    def __init__(self, config: CohereEmbeddingConfig) -> None:
        """Initialize Cohere embedding adapter.

        Args:
            config: Cohere embedding configuration.
        """
        super().__init__(config)
        self._api_key = config.api_key

    async def embed(
        self,
        texts: str | list[str],
        *,
        model: str | None = None,
        batch_size: int = 100,
    ) -> list[list[float]]:
        """Generate embeddings using Cohere API.

        Args:
            texts: Text(s) to embed
            model: Model to use (default: embed-english-v3.0)
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors
        """
        model = model or "embed-english-v3.0"

        # Normalize input
        if isinstance(texts, str):
            texts = [texts]

        embeddings: list[list[float]] = []

        logger.debug(
            "embedding_batch",
            provider="cohere",
            model=model,
            batch_size=len(texts),
        )

        # Mock implementation
        import random

        for _ in texts:
            vector = [random.random() for _ in range(1024)]
            embeddings.append(vector)

        return embeddings

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check Cohere API availability.

        Args:
            timeout: Check timeout in seconds

        Returns:
            HealthCheckResult indicating HEALTHY if API key is configured.
        """
        if self._api_key:
            return HealthCheckResult(
                component="embedding_cohere", status=HealthStatus.HEALTHY
            )
        return HealthCheckResult(
            component="embedding_cohere",
            status=HealthStatus.UNHEALTHY,
            message="API key not configured",
        )

    def get_models(self) -> list[EmbeddingModelInfo]:
        """Get available Cohere embedding models.

        Returns:
            List of model metadata
        """
        return [
            EmbeddingModelInfo(
                model_id="embed-english-v3.0",
                provider="cohere",
                display_name="Cohere English v3.0",
                embedding_dimension=1024,
                max_input_tokens=512,
                input_cost_per_million=0.10,
            ),
            EmbeddingModelInfo(
                model_id="embed-english-light-v3.0",
                provider="cohere",
                display_name="Cohere English Light v3.0",
                embedding_dimension=384,
                max_input_tokens=512,
                input_cost_per_million=0.03,
            ),
        ]

    async def close(self) -> None:
        """Clean up resources."""
