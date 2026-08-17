"""OpenAI embedding provider adapter."""

from __future__ import annotations

from lexigram.ai.llm.embedding.base import (
    AbstractEmbeddingAdapter,
    EmbeddingModelInfo,
)
from lexigram.ai.llm.embedding.config import OpenAIEmbeddingConfig
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class OpenAIEmbeddingAdapter(AbstractEmbeddingAdapter):
    """Adapter for OpenAI embedding models."""

    def __init__(self, config: OpenAIEmbeddingConfig) -> None:
        """Initialize OpenAI embedding adapter.

        Args:
            config: OpenAI embedding configuration.
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
        """Generate embeddings using OpenAI API.

        Args:
            texts: Text(s) to embed
            model: Model to use (default: text-embedding-3-small)
            batch_size: Batch size (max 100 for OpenAI)

        Returns:
            List of embedding vectors
        """
        model = model or "text-embedding-3-small"

        # Normalize input
        if isinstance(texts, str):
            texts = [texts]

        embeddings: list[list[float]] = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            # In a real implementation, would call OpenAI API here
            # For now, return mock embeddings
            logger.debug(
                "embedding_batch",
                provider="openai",
                model=model,
                batch_size=len(batch),
            )

            # Mock implementation: return random vectors of correct dimension
            import random

            for _ in batch:
                vector = [random.random() for _ in range(1536)]  # noqa: S311 — mock-dummy vectors (non-secret)
                embeddings.append(vector)

        return embeddings

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check OpenAI API availability.

        Args:
            timeout: Check timeout in seconds

        Returns:
            HealthCheckResult indicating HEALTHY if API key is configured.
        """
        if self._api_key:
            return HealthCheckResult(
                component="embedding_openai", status=HealthStatus.HEALTHY
            )
        return HealthCheckResult(
            component="embedding_openai",
            status=HealthStatus.UNHEALTHY,
            message="API key not configured",
        )

    def get_models(self) -> list[EmbeddingModelInfo]:
        """Get available OpenAI embedding models.

        Returns:
            List of model metadata
        """
        return [
            EmbeddingModelInfo(
                model_id="text-embedding-3-large",
                provider="openai",
                display_name="OpenAI Embedding 3 Large",
                embedding_dimension=3072,
                max_input_tokens=8191,
                input_cost_per_million=13.0,
            ),
            EmbeddingModelInfo(
                model_id="text-embedding-3-small",
                provider="openai",
                display_name="OpenAI Embedding 3 Small",
                embedding_dimension=1536,
                max_input_tokens=8191,
                input_cost_per_million=2.0,
            ),
        ]
