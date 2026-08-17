"""Pipeline executor for orchestrating stage execution."""

from __future__ import annotations

# to annotate failures and continue per configured error strategies rather than crash the runner
import asyncio

from lexigram.ai.rag.pipeline.base import PipelineStageProtocol
from lexigram.ai.rag.pipeline.types import (
    ErrorStrategy,
    PipelineContext,
    StageStatus,
)
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class PipelineExecutor:
    """Executes pipeline stages in sequence with error handling.

    The executor orchestrates the execution of pipeline stages,
    handling errors according to configured strategies and
    tracking metrics throughout execution.
    """

    def __init__(
        self,
        stages: list[PipelineStageProtocol],
        default_error_strategy: ErrorStrategy = ErrorStrategy.GRACEFUL,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize the pipeline executor.

        Args:
            stages: List of pipeline stages to execute
            default_error_strategy: Default error handling strategy
            max_retries: Maximum number of retries for RETRY strategy
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.stages = stages
        self.default_error_strategy = default_error_strategy
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute all pipeline stages in sequence.

        Args:
            context: Initial pipeline context

        Returns:
            Final pipeline context after all stages

        Raises:
            Exception: If a stage fails with FAIL_FAST error strategy
        """
        logger.info(
            "Starting pipeline execution",
            extra={
                "request_id": context.request_id,
                "query": context.query,
                "num_stages": len(self.stages),
            },
        )

        for stage in self.stages:
            try:
                context = await self._execute_stage(stage, context)
            except Exception as e:
                logger.exception(
                    "Pipeline execution failed",
                    extra={
                        "request_id": context.request_id,
                        "stage": stage.name,
                        "error": str(e),
                    },
                )
                # If we reach here, error strategy was FAIL_FAST
                context.complete_stage(
                    stage.name,
                    status=StageStatus.FAILED,
                )
                raise

        logger.info(
            "Pipeline execution completed",
            extra={
                "request_id": context.request_id,
                "duration_ms": context.total_duration_ms,
                "completed_stages": len(context.completed_stages),
                "failed_stages": len(context.failed_stages),
                "has_errors": context.has_errors,
            },
        )

        return context

    async def _execute_stage(
        self,
        stage: PipelineStageProtocol,
        context: PipelineContext,
        retry_count: int = 0,
    ) -> PipelineContext:
        """Execute a single pipeline stage with error handling.

        Args:
            stage: The stage to execute
            context: Current pipeline context
            retry_count: Current retry attempt count

        Returns:
            Updated pipeline context

        Raises:
            Exception: If error strategy is FAIL_FAST
        """
        stage_name = stage.name

        logger.debug(
            "Starting stage execution",
            extra={
                "request_id": context.request_id,
                "stage": stage_name,
                "retry_count": retry_count,
            },
        )

        context.start_stage(stage_name)

        try:
            # Execute the stage
            updated_context = await stage.process(context)

            # Mark as completed
            updated_context.complete_stage(stage_name, status=StageStatus.COMPLETED)

            logger.info(
                "Stage execution completed",
                extra={
                    "request_id": context.request_id,
                    "stage": stage_name,
                    "duration_ms": [
                        m.duration_ms
                        for m in filter(
                            lambda m: m.stage_name == stage_name,
                            updated_context.stage_metrics,
                        )
                    ][-1],
                },
            )

        except (RuntimeError, ValueError, TypeError, OSError) as e:
            logger.warning(
                "Stage execution failed",
                extra={
                    "request_id": context.request_id,
                    "stage": stage_name,
                    "error": str(e),
                    "retry_count": retry_count,
                },
            )

            # Add error to context
            context.add_error(
                stage=stage_name,
                error=e,
                recoverable=retry_count < self.max_retries,
                retry_count=retry_count,
            )

            # Apply error strategy
            return await self._handle_error(stage, context, e, retry_count)
        else:
            return updated_context

    async def _handle_error(
        self,
        stage: PipelineStageProtocol,
        context: PipelineContext,
        error: Exception,
        retry_count: int,
    ) -> PipelineContext:
        """Handle stage execution error based on error strategy.

        Args:
            stage: The stage that failed
            context: Current pipeline context
            error: The exception that was raised
            retry_count: Current retry attempt count

        Returns:
            Updated pipeline context

        Raises:
            Exception: If error strategy is FAIL_FAST
        """
        strategy = self.default_error_strategy

        if strategy == ErrorStrategy.FAIL_FAST:
            logger.error(
                "Failing fast due to stage error",
                extra={
                    "request_id": context.request_id,
                    "stage": stage.name,
                    "error": str(error),
                },
            )
            context.complete_stage(stage.name, status=StageStatus.FAILED)
            raise error

        if strategy == ErrorStrategy.RETRY and retry_count < self.max_retries:
            # Exponential backoff
            delay = self.retry_delay * (2**retry_count)
            logger.info(
                "Retrying stage after delay",
                extra={
                    "request_id": context.request_id,
                    "stage": stage.name,
                    "retry_count": retry_count + 1,
                    "delay_seconds": delay,
                },
            )

            await asyncio.sleep(delay)

            # Complete the failed attempt
            context.complete_stage(stage.name, status=StageStatus.FAILED)

            # Retry
            return await self._execute_stage(stage, context, retry_count + 1)

        if strategy == ErrorStrategy.SKIP:
            logger.warning(
                "Skipping stage due to error",
                extra={
                    "request_id": context.request_id,
                    "stage": stage.name,
                    "error": str(error),
                },
            )
            context.add_warning(f"Skipped stage {stage.name} due to error: {error}")
            context.complete_stage(stage.name, status=StageStatus.SKIPPED)
            return context

        if strategy == ErrorStrategy.GRACEFUL:
            logger.warning(
                "Continuing with partial results due to stage error",
                extra={
                    "request_id": context.request_id,
                    "stage": stage.name,
                    "error": str(error),
                },
            )
            context.add_warning(
                f"Stage {stage.name} failed but continuing: {error}",
            )
            context.complete_stage(stage.name, status=StageStatus.FAILED)
            return context

        # Default to graceful degradation
        logger.warning(
            "Unknown error strategy, using graceful degradation",
            extra={
                "request_id": context.request_id,
                "stage": stage.name,
                "strategy": strategy,
            },
        )
        context.add_warning(
            f"Stage {stage.name} failed but continuing: {error}",
        )
        context.complete_stage(stage.name, status=StageStatus.FAILED)
        return context

    async def execute_parallel(
        self,
        context: PipelineContext,
        stages: list[PipelineStageProtocol] | None = None,
    ) -> PipelineContext:
        """Execute multiple stages in parallel.

        Args:
            context: Pipeline context
            stages: Stages to execute in parallel (default: all stages)

        Returns:
            Updated pipeline context with results from all parallel stages
        """
        if stages is None:
            stages = self.stages

        logger.info(
            "Starting parallel stage execution",
            extra={
                "request_id": context.request_id,
                "num_stages": len(stages),
            },
        )

        # Execute all stages in parallel
        tasks = [self._execute_stage(stage, context) for stage in stages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Parallel stage execution failed",
                    extra={
                        "request_id": context.request_id,
                        "stage": stages[i].name,
                        "error": str(result),
                    },
                )
                context.add_error(
                    stage=stages[i].name,
                    error=result,
                    recoverable=False,
                )
            elif isinstance(result, PipelineContext):
                # Merge context results
                # Note: This is simplified - real merging would be more sophisticated
                context = result

        return context
