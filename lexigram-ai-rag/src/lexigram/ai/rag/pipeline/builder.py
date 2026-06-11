from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from lexigram.ai.rag.config import (
    PipelineConfig,
    PipelineStageType,
)
from lexigram.ai.rag.exceptions import MissingCitationsError
from lexigram.ai.rag.pipeline._stage_factory import build_pipeline_stages
from lexigram.ai.rag.pipeline.base import PipelineStageProtocol
from lexigram.ai.rag.pipeline.executor import PipelineExecutor
from lexigram.ai.rag.pipeline.types import ErrorStrategy
from lexigram.contracts.ai.exceptions import RAGError
from lexigram.contracts.ai.rag import RAGContext, RAGEvaluatorProtocol, RAGResponse
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.ai.rag.pipeline.types import PipelineContext
    from lexigram.contracts.ai.memory import WorkingMemoryProtocol

from lexigram.primitives.builder import AbstractBuilder

logger = get_logger(__name__)


class RAGPipeline:
    """Main RAG pipeline that orchestrates all stages.

    This class provides a simple interface for executing the complete
    RAG pipeline with configurable stages and error handling.
    """

    def __init__(
        self,
        config: PipelineConfig,
        stages: list[PipelineStageProtocol],
        evaluator: RAGEvaluatorProtocol | None = None,
        working_memory: WorkingMemoryProtocol | None = None,
    ):
        """Initialize the RAG pipeline.

        Args:
            config: Pipeline configuration
            stages: List of pipeline stages
            evaluator: Optional evaluator implementing
                :class:`~lexigram.contracts.ai.rag.RAGEvaluatorProtocol` for
                automatic per-request quality evaluation.  Evaluation
                frequency is controlled by :attr:`~lexigram.ai.rag.config.PipelineConfig.auto_evaluate_every_n`.
            working_memory: Optional working memory for context enrichment.
        """
        self.config = config
        self.stages = stages
        self.evaluator = evaluator
        self._working_memory = working_memory
        self._request_count: int = 0
        error_strategy = config.default_error_strategy
        if not isinstance(error_strategy, ErrorStrategy):
            if isinstance(error_strategy, str):
                error_strategy = ErrorStrategy(error_strategy)
            else:
                error_strategy = ErrorStrategy.GRACEFUL

        self.executor = PipelineExecutor(
            stages=stages,
            default_error_strategy=error_strategy,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
        )

    async def run(
        self,
        query: str,
        documents: list[str] | None = None,
        document_paths: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PipelineContext:
        """Execute the RAG pipeline.

        Args:
            query: User query
            documents: Optional list of document content strings
            document_paths: Optional list of document file paths
            metadata: Optional custom metadata

        Returns:
            Pipeline context with results
        """
        from lexigram.ai.rag.pipeline.types import PipelineContext

        # Create initial context
        context = PipelineContext(
            query=query,
            documents=documents or [],
            document_paths=document_paths or [],
            metadata=metadata or {},
        )

        # Enrich query with memory context if working memory is available
        if self._working_memory:
            try:
                memory_entries = await self._working_memory.assemble(
                    query=query,
                    token_budget=1024,
                    owner_id=(metadata or {}).get("user_id")
                    or (metadata or {}).get("session_id")
                    or "anonymous",
                )
                if memory_entries:
                    memory_context = "\n".join(
                        f"[{e.role}]: {e.content}" for e in memory_entries
                    )
                    context.metadata["memory_context"] = memory_context
                    context.metadata["memory_entries_count"] = len(memory_entries)
            except (RuntimeError, TypeError, AttributeError, LookupError) as e:
                logger.warning("rag_memory_enrichment_failed", error=str(e))

        # Execute pipeline
        context = await self.executor.execute(context)

        # Citation enforcement (P7.2) — fail fast before incrementing counters
        if (
            self.config.require_citations
            and context.synthesis_result is not None
            and not context.synthesis_result.citations
        ):
            msg = (
                f"Pipeline '{self.config.name}' requires citations but none were "
                "produced by the synthesis stage."
            )
            raise MissingCitationsError(msg)

        # Auto-evaluation hook (P7.1)
        self._request_count += 1
        if (
            self.evaluator is not None
            and self.config.auto_evaluate_every_n is not None
            and self._request_count % self.config.auto_evaluate_every_n == 0
            and context.synthesis_result is not None
        ):
            docs = context.optimized_chunks or context.retrieved_chunks
            try:
                report = await self.evaluator.evaluate(
                    query=context.query,
                    retrieved_docs=docs,
                    generated_answer=context.synthesis_result.response,
                )
                context.metadata["evaluation_report"] = report
            except (RuntimeError, TypeError, AttributeError, OSError, ValueError):
                logger.warning(
                    "Auto-evaluation failed for request %s",
                    context.request_id,
                    exc_info=True,
                )

        return context

    async def execute(self, context: RAGContext) -> Result[RAGResponse, RAGError]:
        """Execute the RAG pipeline per the contract protocol.

        Args:
            context: Pipeline context with query and optional config/filters.

        Returns:
            Ok(RAGResponse) on success, Err(RAGError) on failure.
        """
        try:
            pipeline_ctx = await self.run(
                query=context.query,
                metadata=context.filters,
            )
            synthesis = pipeline_ctx.synthesis_result
            answer = synthesis.response if synthesis is not None else ""
            citations = synthesis.citations if synthesis is not None else None
            response = RAGResponse(
                answer=answer,
                sources=[],
                citations=citations,
            )
            return Ok(response)
        except RAGError as exc:
            return Err(exc)

    async def run_parallel(
        self,
        query: str,
        stages: list[PipelineStageProtocol] | None = None,
        **kwargs: Any,
    ) -> PipelineContext:
        """Execute pipeline stages in parallel.

        Args:
            query: User query
            stages: Stages to execute in parallel (default: all stages)
            **kwargs: Additional context parameters

        Returns:
            Pipeline context with results
        """
        from lexigram.ai.rag.pipeline.types import PipelineContext

        context = PipelineContext(query=query, **kwargs)
        return await self.executor.execute_parallel(context, stages)


class PipelineBuilder(AbstractBuilder[RAGPipeline]):
    """Builder for constructing RAG pipelines with fluent API.

    The builder provides a convenient way to configure and build
    pipelines programmatically or from configuration files.
    """

    def __init__(self) -> None:
        """Initialize the pipeline builder."""
        super().__init__()
        self.config = PipelineConfig()
        self._custom_stages: list[PipelineStageProtocol] = []

    def with_name(self, name: str) -> PipelineBuilder:
        """Set pipeline name.

        Args:
            name: Pipeline name

        Returns:
            Self for chaining
        """
        self.config.name = name
        return self

    def with_description(self, description: str) -> PipelineBuilder:
        """Set pipeline description.

        Args:
            description: Pipeline description

        Returns:
            Self for chaining
        """
        self.config.description = description
        return self

    def with_ingestion(self, **kwargs: Any) -> PipelineBuilder:
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

    def with_query_processing(self, **kwargs: Any) -> PipelineBuilder:
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

    def with_retrieval(self, **kwargs: Any) -> PipelineBuilder:
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

    def with_context_optimization(self, **kwargs: Any) -> PipelineBuilder:
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

    def with_synthesis(self, **kwargs: Any) -> PipelineBuilder:
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

    def with_quality_assurance(self, **kwargs: Any) -> PipelineBuilder:
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

    def with_post_processing(self, **kwargs: Any) -> PipelineBuilder:
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
    ) -> PipelineBuilder:
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

    def with_stages(self, stages: list[PipelineStageType]) -> PipelineBuilder:
        """Set the ordered list of pipeline stages.

        Args:
            stages: List of stages

        Returns:
            Self for chaining
        """
        self.config.stages = stages
        return self

    def with_custom_stage(self, stage: PipelineStageProtocol) -> PipelineBuilder:
        """Add a custom pipeline stage.

        Args:
            stage: Custom pipeline stage

        Returns:
            Self for chaining
        """
        self._custom_stages.append(stage)
        return self

    def from_dict(self, config_dict: dict[str, Any]) -> PipelineBuilder:
        """Load configuration from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Self for chaining
        """
        self.config = PipelineConfig.from_dict(config_dict)
        return self

    async def from_yaml(self, yaml_path: str | Path) -> PipelineBuilder:
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
    ) -> PipelineBuilder:
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
    ) -> PipelineBuilder:
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
    ) -> PipelineBuilder:
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

    def with_citations(self, required: bool = True) -> PipelineBuilder:
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
    ) -> PipelineBuilder:
        """Enable automatic evaluation of pipeline outputs.

        Args:
            evaluator: Optional pre-built evaluator instance.
            every_n: Evaluate every *n*-th request (default: every request).
        """
        self._evaluator = evaluator
        self.config.auto_evaluate_every_n = every_n
        return self

    def with_timeout(self, **stage_timeouts: float) -> PipelineBuilder:
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
    ) -> PipelineBuilder:
        """Attach working memory for context enrichment.

        Args:
            memory: Working memory instance.
        """
        self._working_memory = memory
        return self

    def build(self) -> RAGPipeline:
        """Build the RAG pipeline.

        Returns:
            Configured RAG pipeline

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate configuration
        self._validate_config()

        # Build stages
        stages = self._build_stages()

        # Add custom stages
        stages.extend(self._custom_stages)

        # Create pipeline
        return RAGPipeline(
            config=self.config,
            stages=stages,
            evaluator=getattr(self, "_evaluator", None),
            working_memory=getattr(self, "_working_memory", None),
        )

    def _validate_config(self) -> None:
        """Validate pipeline configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        # Check that at least synthesis is enabled
        if not self.config.synthesis.enabled:
            msg = "Synthesis must be enabled in pipeline configuration"
            raise ValueError(msg)

        # Check that retrieval is enabled if synthesis is enabled
        if self.config.synthesis.enabled and not self.config.retrieval.enabled:
            raise ValueError(
                "Retrieval stage must be enabled when synthesis is enabled",
            )

        # Validate quality thresholds
        qa_config = self.config.quality_assurance
        if qa_config.enabled:
            if not (0 <= qa_config.min_faithfulness <= 1):
                msg = "qa_config.min_faithfulness must be between 0 and 1"
                raise ValueError(msg)
            if not (0 <= qa_config.min_relevance <= 1):
                msg = "qa_config.min_relevance must be between 0 and 1"
                raise ValueError(msg)
            if not (0 <= qa_config.min_confidence <= 1):
                msg = "qa_config.min_confidence must be between 0 and 1"
                raise ValueError(msg)

    def _build_stages(self) -> list[PipelineStageProtocol]:
        """Build pipeline stages based on configuration.

        Returns:
            List of configured pipeline stages.
        """
        return build_pipeline_stages(self.config)
