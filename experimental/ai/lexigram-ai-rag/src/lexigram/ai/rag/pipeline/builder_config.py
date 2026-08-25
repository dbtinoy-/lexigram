"""Fluent configuration wiring for :class:`~lexigram.ai.rag.pipeline.builder.PipelineBuilder`.

This module hosts the builder's configuration surface: per-stage
tweaks, error handling, high-level convenience API (Phase 10 DX), and
config loading from dicts/YAML.  Pipeline assembly itself (stage
construction, validation, instantiation) stays in the builder.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

import yaml

from lexigram.ai.rag.config import (
    PipelineConfig,
    PipelineStageType,
)
from lexigram.ai.rag.pipeline.types import ErrorStrategy
from lexigram.contracts.ai.rag import RAGEvaluatorProtocol

if TYPE_CHECKING:
    from lexigram.ai.rag.pipeline.base import PipelineStageProtocol
    from lexigram.contracts.ai.memory import WorkingMemoryProtocol

__all__ = ["PipelineConfigWiring"]


class PipelineConfigWiring:
    """Mixin providing the fluent configuration methods of the pipeline builder.

    Concrete builders are expected to provide ``self.config``
    (:class:`~lexigram.ai.rag.config.PipelineConfig`), ``self._custom_stages``
    and, optionally, ``self._evaluator`` / ``self._working_memory``.
    """

    config: PipelineConfig
    _custom_stages: list[PipelineStageProtocol]
    _evaluator: RAGEvaluatorProtocol | None
    _working_memory: WorkingMemoryProtocol | None

    def with_name(self, name: str) -> Self:
        """Set pipeline name.

        Args:
            name: Pipeline name

        Returns:
            Self for chaining
        """
        self.config.name = name
        return self

    def with_description(self, description: str) -> Self:
        """Set pipeline description.

        Args:
            description: Pipeline description

        Returns:
            Self for chaining
        """
        self.config.description = description
        return self

    def with_ingestion(self, **kwargs: Any) -> Self:
        """Configure ingestion stage.

        Args:
            **kwargs: Ingestion configuration parameters

        Returns:
            Self for chaining
        """
        for key, value in kwargs.items():
            if hasattr(self.config.ingestion, key):
                setattr(self.config.ingestion, key, value)
        return self

    def with_query_processing(self, **kwargs: Any) -> Self:
        """Configure query processing stage.

        Args:
            **kwargs: Query processing configuration parameters

        Returns:
            Self for chaining
        """
        for key, value in kwargs.items():
            if hasattr(self.config.query_processing, key):
                setattr(self.config.query_processing, key, value)
        return self

    def with_retrieval(self, **kwargs: Any) -> Self:
        """Configure retrieval stage.

        Args:
            **kwargs: Retrieval configuration parameters

        Returns:
            Self for chaining
        """
        for key, value in kwargs.items():
            if hasattr(self.config.retrieval, key):
                setattr(self.config.retrieval, key, value)
        return self

    def with_context_optimization(self, **kwargs: Any) -> Self:
        """Configure context optimization stage.

        Args:
            **kwargs: Context optimization configuration parameters

        Returns:
            Self for chaining
        """
        for key, value in kwargs.items():
            if hasattr(self.config.context_optimization, key):
                setattr(self.config.context_optimization, key, value)
        return self

    def with_synthesis(self, **kwargs: Any) -> Self:
        """Configure synthesis stage.

        Args:
            **kwargs: Synthesis configuration parameters

        Returns:
            Self for chaining
        """
        for key, value in kwargs.items():
            if hasattr(self.config.synthesis, key):
                setattr(self.config.synthesis, key, value)
        return self

    def with_quality_assurance(self, **kwargs: Any) -> Self:
        """Configure quality assurance stage.

        Args:
            **kwargs: Quality assurance configuration parameters

        Returns:
            Self for chaining
        """
        for key, value in kwargs.items():
            if hasattr(self.config.quality_assurance, key):
                setattr(self.config.quality_assurance, key, value)
        return self

    def with_post_processing(self, **kwargs: Any) -> Self:
        """Configure post-processing stage.

        Args:
            **kwargs: Post-processing configuration parameters

        Returns:
            Self for chaining
        """
        for key, value in kwargs.items():
            if hasattr(self.config.post_processing, key):
                setattr(self.config.post_processing, key, value)
        return self

    def with_error_strategy(
        self,
        strategy: ErrorStrategy,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> Self:
        """Configure global error handling.

        Args:
            strategy: Default error handling strategy
            max_retries: Maximum number of retries
            retry_delay: Initial delay between retries

        Returns:
            Self for chaining
        """
        self.config.default_error_strategy = strategy
        self.config.max_retries = max_retries
        self.config.retry_delay = retry_delay
        return self

    def with_stages(self, stages: list[PipelineStageType]) -> Self:
        """Set the ordered list of pipeline stages.

        Args:
            stages: List of stages

        Returns:
            Self for chaining
        """
        self.config.stages = stages
        return self

    def with_custom_stage(self, stage: PipelineStageProtocol) -> Self:
        """Add a custom pipeline stage.

        Args:
            stage: Custom pipeline stage

        Returns:
            Self for chaining
        """
        self._custom_stages.append(stage)
        return self

    def from_dict(self, config_dict: dict[str, Any]) -> Self:
        """Load configuration from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Self for chaining
        """
        self.config = PipelineConfig.from_dict(config_dict)
        return self

    async def from_yaml(self, yaml_path: str | Path) -> Self:
        """Load configuration from YAML file.

        Args:
            yaml_path: Path to YAML configuration file

        Returns:
            Self for chaining
        """
        import asyncio

        def _load_yaml() -> Any:
            with open(yaml_path) as f:
                return yaml.safe_load(f.read())

        config_dict = await asyncio.to_thread(_load_yaml)
        return self.from_dict(config_dict)

    # -----------------------------------------------------------------
    # High-level convenience API (Phase 10 DX)
    # -----------------------------------------------------------------

    def retrieve(
        self,
        strategy: str = "hybrid",
        top_k: int = 10,
        **kwargs: Any,
    ) -> Self:
        """Configure retrieval with high-level parameters.

        Args:
            strategy: Retrieval strategy name (``"hybrid"``, ``"dense"``,
                ``"sparse"``).
            top_k: Number of chunks to retrieve.
            **kwargs: Additional retrieval parameters.
        """
        self.config.retrieval.enabled = True
        self.config.retrieval.strategy = strategy
        self.config.retrieval.top_k = top_k
        for key, value in kwargs.items():
            if hasattr(self.config.retrieval, key):
                setattr(self.config.retrieval, key, value)
        return self

    def rerank(
        self,
        strategy: str = "cross-encoder",
        top_k: int = 5,
        **kwargs: Any,
    ) -> Self:
        """Configure context optimization / reranking.

        Args:
            strategy: Reranking strategy name.
            top_k: Number of chunks to keep after reranking.
            **kwargs: Additional reranking parameters.
        """
        self.config.context_optimization.enabled = True
        self.config.context_optimization.strategy = strategy
        self.config.context_optimization.top_k = top_k
        for key, value in kwargs.items():
            if hasattr(self.config.context_optimization, key):
                setattr(self.config.context_optimization, key, value)
        return self

    def synthesize(
        self,
        strategy: str = "abstractive",
        model: str | None = None,
        **kwargs: Any,
    ) -> Self:
        """Configure synthesis with high-level parameters.

        Args:
            strategy: Synthesis strategy (``"abstractive"``, ``"extractive"``).
            model: LLM model identifier for generation.
            **kwargs: Additional synthesis parameters.
        """
        self.config.synthesis.enabled = True
        self.config.synthesis.strategy = strategy  # type: ignore[assignment]
        if model is not None:
            self.config.synthesis.model = model
        for key, value in kwargs.items():
            if hasattr(self.config.synthesis, key):
                setattr(self.config.synthesis, key, value)
        return self

    def with_citations(self, required: bool = True) -> Self:
        """Enable citation tracking in the pipeline.

        Args:
            required: Whether citations are required (pipeline fails without
                them if set to ``True``).
        """
        self.config.require_citations = required
        return self

    def with_evaluation(
        self,
        evaluator: RAGEvaluatorProtocol | None = None,
        every_n: int = 1,
    ) -> Self:
        """Enable automatic evaluation of pipeline outputs.

        Args:
            evaluator: Optional pre-built evaluator instance.
            every_n: Evaluate every *n*-th request (default: every request).
        """
        self._evaluator = evaluator
        self.config.auto_evaluate_every_n = every_n
        return self

    def with_timeout(self, **stage_timeouts: float) -> Self:
        """Set per-stage timeouts (in seconds).

        Keyword arguments map stage names to their timeout values::

            builder.with_timeout(retrieval=10.0, synthesis=30.0)

        Args:
            **stage_timeouts: Mapping of stage name to timeout in seconds.
        """
        if not hasattr(self.config, "stage_timeouts"):
            setattr(self.config, "stage_timeouts", {})  # noqa: B010
        self.config.stage_timeouts.update(stage_timeouts)  # type: ignore[attr-defined]
        return self

    def with_working_memory(
        self,
        memory: WorkingMemoryProtocol,
    ) -> Self:
        """Attach working memory for context enrichment.

        Args:
            memory: Working memory instance.
        """
        self._working_memory = memory
        return self
