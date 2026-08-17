"""Core types for RAG pipeline execution.

This module provides the foundational types used throughout the pipeline,
including context, errors, and configuration structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
import uuid

from lexigram.ai.rag.chunking import Chunk
from lexigram.ai.rag.query import TransformedQuery
from lexigram.ai.rag.routing import QueryIntent, RoutingDecision
from lexigram.ai.rag.synthesis import (
    ContextChunk,
    QualityMetrics,
    SynthesisResult,
)


class ErrorStrategy(StrEnum):
    """Strategy for handling errors in pipeline stages."""

    RETRY = "retry"  # Retry with exponential backoff
    FALLBACK = "fallback"  # Use fallback implementation
    SKIP = "skip"  # Skip stage and continue
    FAIL_FAST = "fail_fast"  # Raise exception immediately
    GRACEFUL = "graceful"  # Return partial results with warnings


class StageStatus(StrEnum):
    """Status of a pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineError:
    """Represents an error that occurred during pipeline execution."""

    stage: str
    error: Exception
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    recoverable: bool = True
    retry_count: int = 0


@dataclass
class StageMetrics:
    """Metrics for a single pipeline stage."""

    stage_name: str
    status: StageStatus
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_ms: float = 0.0
    error: PipelineError | None = None

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return self.duration_ms / 1000.0


@dataclass
class PipelineContext:
    """Context object that flows through pipeline stages.

    This context carries all state through the pipeline, accumulating
    results from each stage and tracking metrics/errors.
    """

    # Required input
    query: str

    # Optional input documents
    documents: list[str] = field(default_factory=list)
    document_paths: list[str] = field(default_factory=list)

    # Stage results - populated by pipeline stages
    transformed_queries: list[TransformedQuery] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    retrieved_chunks: list[ContextChunk] = field(default_factory=list)
    optimized_chunks: list[ContextChunk] = field(default_factory=list)
    synthesis_result: SynthesisResult | None = None
    quality_metrics: QualityMetrics | None = None

    # Routing and intent
    routing_decision: RoutingDecision | None = None
    intent: QueryIntent | None = None

    # Request tracking
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Custom metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # Performance metrics
    stage_metrics: list[StageMetrics] = field(default_factory=list)
    token_usage: dict[str, int] = field(default_factory=dict)
    cache_hits: dict[str, bool] = field(default_factory=dict)

    # Error tracking
    errors: list[PipelineError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if any warnings were issued."""
        return len(self.warnings) > 0

    @property
    def total_duration_ms(self) -> float:
        """Calculate total pipeline duration in milliseconds."""
        return sum(m.duration_ms for m in self.stage_metrics)

    @property
    def total_duration_seconds(self) -> float:
        """Calculate total pipeline duration in seconds."""
        return self.total_duration_ms / 1000.0

    @property
    def failed_stages(self) -> list[str]:
        """Get list of failed stage names."""
        return [
            m.stage_name for m in self.stage_metrics if m.status == StageStatus.FAILED
        ]

    @property
    def completed_stages(self) -> list[str]:
        """Get list of completed stage names."""
        return [
            m.stage_name
            for m in self.stage_metrics
            if m.status == StageStatus.COMPLETED
        ]

    def add_error(
        self,
        stage: str,
        error: Exception,
        recoverable: bool = True,
        retry_count: int = 0,
    ) -> None:
        """Add an error to the context.

        Args:
            stage: Name of the stage where error occurred
            error: The exception that was raised
            recoverable: Whether the error is recoverable
            retry_count: Number of times this error has been retried
        """
        pipeline_error = PipelineError(
            stage=stage,
            error=error,
            recoverable=recoverable,
            retry_count=retry_count,
        )
        self.errors.append(pipeline_error)

    def add_warning(self, message: str) -> None:
        """Add a warning message to the context.

        Args:
            message: Warning message
        """
        self.warnings.append(message)

    def start_stage(self, stage_name: str) -> None:
        """Mark a stage as started.

        Args:
            stage_name: Name of the stage
        """
        metrics = StageMetrics(
            stage_name=stage_name,
            status=StageStatus.RUNNING,
            start_time=datetime.now(UTC),
        )
        self.stage_metrics.append(metrics)

    def complete_stage(
        self,
        stage_name: str,
        status: StageStatus = StageStatus.COMPLETED,
        error: PipelineError | None = None,
    ) -> None:
        """Mark a stage as completed.

        Args:
            stage_name: Name of the stage
            status: Final status of the stage
            error: Optional error if stage failed
        """
        for metrics in reversed(self.stage_metrics):
            if (
                metrics.stage_name == stage_name
                and metrics.status == StageStatus.RUNNING
            ):
                metrics.status = status
                metrics.end_time = datetime.now(UTC)
                if metrics.start_time:
                    duration = (metrics.end_time - metrics.start_time).total_seconds()
                    metrics.duration_ms = duration * 1000.0
                metrics.error = error
                break

    def record_token_usage(self, operation: str, tokens: int) -> None:
        """Record token usage for an operation.

        Args:
            operation: Name of the operation (e.g., "embedding", "llm_call")
            tokens: Number of tokens used
        """
        if operation in self.token_usage:
            self.token_usage[operation] += tokens
        else:
            self.token_usage[operation] = tokens

    def record_cache_hit(self, cache_key: str, hit: bool) -> None:
        """Record a cache hit or miss.

        Args:
            cache_key: Key for the cache lookup
            hit: Whether the cache was hit
        """
        self.cache_hits[cache_key] = hit

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for serialization.

        Returns:
            Dictionary representation of the context
        """
        return {
            "request_id": self.request_id,
            "query": self.query,
            "created_at": self.created_at.isoformat(),
            "total_duration_ms": self.total_duration_ms,
            "completed_stages": self.completed_stages,
            "failed_stages": self.failed_stages,
            "has_errors": self.has_errors,
            "has_warnings": self.has_warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "token_usage": self.token_usage,
            "cache_hits": dict(self.cache_hits),
            "metadata": self.metadata,
        }
