"""Types and data structures for RAG evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# Type aliases for clarity
LLMClientProtocol = Any  # Will be protocol for LLM client
EmbeddingClientProtocol = Any  # Will be protocol for embedding client


class MetricType(str, Enum):
    """Types of evaluation metrics."""

    # Retrieval metrics
    RETRIEVAL_PRECISION = "retrieval_precision"
    RETRIEVAL_RECALL = "retrieval_recall"
    RETRIEVAL_F1 = "retrieval_f1"
    RETRIEVAL_MRR = "retrieval_mrr"  # Mean Reciprocal Rank
    RETRIEVAL_NDCG = "retrieval_ndcg"  # Normalized Discounted Cumulative Gain

    # Answer quality metrics
    ANSWER_RELEVANCE = "answer_relevance"
    ANSWER_FAITHFULNESS = "answer_faithfulness"
    ANSWER_COHERENCE = "answer_coherence"
    ANSWER_COMPLETENESS = "answer_completeness"

    # Context metrics
    CONTEXT_RELEVANCE = "context_relevance"
    CONTEXT_PRECISION = "context_precision"
    CONTEXT_RECALL = "context_recall"

    # Overall metrics
    HALLUCINATION_RATE = "hallucination_rate"
    LATENCY = "latency"
    TOKEN_USAGE = "token_usage"  # noqa: S105  # metric name, not a credential
    COST = "cost"


@dataclass
class EvaluationResult:
    """Result of a single metric evaluation.

    Attributes:
        metric_type: Type of metric evaluated.
        score: Numerical score (0.0 to 1.0).
        details: Additional details about the evaluation.
        timestamp: When the evaluation was performed.
    """

    metric_type: MetricType
    score: float
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        """String representation."""
        return f"EvaluationResult({self.metric_type.value}={self.score:.3f})"


@dataclass
class RAGEvaluationReport:
    """Complete evaluation report for a RAG system.

    Attributes:
        query: The original query.
        retrieved_docs: Retrieved document IDs or content.
        generated_answer: Generated answer.
        reference_answer: Optional reference/ground truth answer.
        results: Individual metric results.
        overall_score: Aggregated overall score.
        metadata: Additional metadata.
        timestamp: When the evaluation was performed.
    """

    query: str
    retrieved_docs: list[Any]
    generated_answer: str
    reference_answer: str | None = None
    results: list[EvaluationResult] = field(default_factory=list)
    overall_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def get_metric(self, metric_type: MetricType) -> EvaluationResult | None:
        """Get specific metric result."""
        for result in self.results:
            if result.metric_type == metric_type:
                return result
        return None

    def get_score(self, metric_type: MetricType) -> float | None:
        """Get score for specific metric."""
        result = self.get_metric(metric_type)
        return result.score if result else None

    def __repr__(self) -> str:
        """String representation."""
        return f"RAGEvaluationReport(overall={self.overall_score:.3f}, metrics={len(self.results)})"
