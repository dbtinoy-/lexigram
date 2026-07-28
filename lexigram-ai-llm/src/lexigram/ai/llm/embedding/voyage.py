"""Voyage AI embedding provider adapter."""

from __future__ import annotations

from lexigram.ai.llm.embedding.base import (
    AbstractEmbeddingAdapter,
    EmbeddingModelInfo,
)
from lexigram.ai.llm.embedding.config import VoyageEmbeddingConfig
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class VoyageEmbeddingAdapter(AbstractEmbeddingAdapter):
    """Adapter for Voyage embedding models."""

    def __init__(self, config: VoyageEmbeddingConfig) -> None:
        """Initialize Voyage embedding adapter.

        Args:
            config: Voyage embedding configuration.
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
        """Generate embeddings using Voyage API.

        Args:
            texts: Text(s) to embed
            model: Model to use (default: voyage-3)
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors
        """
        model = model or "voyage-3"

        # Normalize input
        if isinstance(texts, str):
            texts = [texts]

        embeddings: list[list[float]] = []

        logger.debug(
            "embedding_batch",
            provider="voyage",
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
        """Check Voyage API availability.

        Args:
            timeout: Check timeout in seconds

        Returns:
            HealthCheckResult indicating HEALTHY if API key is configured.
        """
        if self._api_key:
            return HealthCheckResult(
                component="embedding_voyage", status=HealthStatus.HEALTHY
            )
        return HealthCheckResult(
            component="embedding_voyage",
            status=HealthStatus.UNHEALTHY,
            message="API key not configured",
        )

    async def close(self) -> None:
        """Clean up resources."""

    def get_models(self) -> list[EmbeddingModelInfo]:
        """Get available Voyage embedding models.

        Returns:
            List of model metadata
        """
        return [
            EmbeddingModelInfo(
                model_id="voyage-3",
                provider="voyage",
                display_name="Voyage 3",
                embedding_dimension=1024,
                max_input_tokens=16000,
                input_cost_per_million=0.05,
            ),
            EmbeddingModelInfo(
                model_id="voyage-3-lite",
                provider="voyage",
                display_name="Voyage 3 Lite",
                embedding_dimension=512,
                max_input_tokens=16000,
                input_cost_per_million=0.02,
            ),
        ]
