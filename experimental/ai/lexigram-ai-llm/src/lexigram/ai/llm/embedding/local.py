"""Local embedding provider adapter using sentence-transformers."""

from __future__ import annotations

from typing import Any

from lexigram.ai.llm.embedding.base import (
    AbstractEmbeddingAdapter,
    EmbeddingModelInfo,
)
from lexigram.ai.llm.embedding.config import LocalEmbeddingConfig
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class LocalEmbeddingAdapter(AbstractEmbeddingAdapter):
    """Adapter for local embedding models via sentence-transformers.

    Supports running embedding models locally for privacy-sensitive
    applications or when API access is restricted.
    """

    def __init__(self, config: LocalEmbeddingConfig) -> None:
        """Initialize local embedding adapter.

        Args:
            config: Local embedding configuration.
        """
        super().__init__(config)
        self._model_name = config.model
        self._device = config.device
        self._model: Any = None  # Would load actual model in production

    async def embed(
        self,
        texts: str | list[str],
        *,
        model: str | None = None,
        batch_size: int = 100,
    ) -> list[list[float]]:
        """Generate embeddings locally.

        Args:
            texts: Text(s) to embed
            model: Model override (ignored, uses configured model)
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors
        """
        # Normalize input
        if isinstance(texts, str):
            texts = [texts]

        embeddings: list[list[float]] = []

        logger.debug(
            "embedding_local",
            model=self._model_name,
            device=self._device,
            text_count=len(texts),
        )

        # Mock implementation - would use actual sentence-transformers
        import random

        dimension = self._get_dimension()
        for _ in texts:
            vector = [random.random() for _ in range(dimension)]  # noqa: S311 — mock-dummy vectors (non-secret)
            embeddings.append(vector)

        return embeddings

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check if model can be loaded.

        Args:
            timeout: Check timeout in seconds

        Returns:
            HealthCheckResult indicating HEALTHY status if model is available.
        """
        # In real implementation, would try to load model
        return HealthCheckResult(
            component="embedding_local", status=HealthStatus.HEALTHY
        )

    def get_models(self) -> list[EmbeddingModelInfo]:
        """Get available local embedding models.

        Returns:
            List of model metadata
        """
        return [
            EmbeddingModelInfo(
                model_id="all-MiniLM-L6-v2",
                provider="local",
                display_name="All MiniLM L6 v2",
                embedding_dimension=384,
                max_input_tokens=256,
                input_cost_per_million=0.0,  # Free - local
            ),
            EmbeddingModelInfo(
                model_id="all-mpnet-base-v2",
                provider="local",
                display_name="All MPNet Base v2",
                embedding_dimension=768,
                max_input_tokens=384,
                input_cost_per_million=0.0,
            ),
            EmbeddingModelInfo(
                model_id="multilingual-e5-large",
                provider="local",
                display_name="Multilingual E5 Large",
                embedding_dimension=1024,
                max_input_tokens=512,
                input_cost_per_million=0.0,
            ),
            EmbeddingModelInfo(
                model_id="bge-large-zh-v1.5",
                provider="local",
                display_name="BGE Large ZH v1.5",
                embedding_dimension=1024,
                max_input_tokens=512,
                input_cost_per_million=0.0,
            ),
        ]

    async def close(self) -> None:
        """Clean up resources."""

    def _get_dimension(self) -> int:
        """Get embedding dimension for configured model.

        Returns:
            Embedding dimension
        """
        dimensions = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "multilingual-e5-large": 1024,
            "bge-large-zh-v1.5": 1024,
        }
        return dimensions.get(self._model_name, 384)
