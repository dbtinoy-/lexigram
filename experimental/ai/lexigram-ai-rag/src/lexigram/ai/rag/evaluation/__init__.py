"""
RAG Evaluation Framework

This module provides comprehensive evaluation metrics for RAG systems
to measure retrieval quality, answer relevance, faithfulness, and overall performance.
"""

from __future__ import annotations

from lexigram.ai.rag.evaluation.answer import (
    AnswerFaithfulnessEvaluator,
    AnswerRelevanceEvaluator,
)
from lexigram.ai.rag.evaluation.base import EvaluatorBase
from lexigram.ai.rag.evaluation.context import ContextRelevanceEvaluator
from lexigram.ai.rag.evaluation.convenience import evaluate_rag
from lexigram.ai.rag.evaluation.evaluator import RAGEvaluator
from lexigram.ai.rag.evaluation.hallucination import HallucinationDetector
from lexigram.ai.rag.evaluation.harness import (
    BenchmarkReport,
    EvalExample,
    PipelineResult,
    RAGBenchmark,
)
from lexigram.ai.rag.evaluation.retrieval import (
    RetrievalPrecisionEvaluator,
    RetrievalRecallEvaluator,
)
from lexigram.ai.rag.evaluation.types import (
    EvaluationResult,
    MetricType,
    RAGEvaluationReport,
)

__all__ = [
    "AnswerFaithfulnessEvaluator",
    "AnswerRelevanceEvaluator",
    "BenchmarkReport",
    "ContextRelevanceEvaluator",
    "EvalExample",
    "EvaluationResult",
    "EvaluatorBase",
    "HallucinationDetector",
    "MetricType",
    "PipelineResult",
    "RAGBenchmark",
    "RAGEvaluationReport",
    "RAGEvaluator",
    "RetrievalPrecisionEvaluator",
    "RetrievalRecallEvaluator",
    "evaluate_rag",
]
