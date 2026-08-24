"""Tests for EvaluationResult and RAGEvaluationReport."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.evaluation import EvaluationResult, MetricType, RAGEvaluationReport
SAMPLE_QUERY = "What is machine learning?"
SAMPLE_ANSWER = "Machine learning is a subset of AI that enables systems to learn from data."
SAMPLE_DOCS = [
    {"id": "doc1", "content": "Machine learning is a branch of artificial intelligence."},
    {"id": "doc2", "content": "ML systems learn patterns from data."},
    {"id": "doc3", "content": "Deep learning is a type of machine learning."},
]


class TestEvaluationResult:
    """Tests for EvaluationResult."""

    def test_creation(self):
        result = EvaluationResult(
            metric_type=MetricType.ANSWER_RELEVANCE,
            score=0.85,
            details={"test": "value"},
        )

        assert result.metric_type == MetricType.ANSWER_RELEVANCE
        assert result.score == 0.85
        assert result.details["test"] == "value"
        assert result.timestamp is not None

    def test_repr(self):
        result = EvaluationResult(
            metric_type=MetricType.RETRIEVAL_PRECISION,
            score=0.75,
        )

        repr_str = repr(result)
        assert "retrieval_precision" in repr_str
        assert "0.750" in repr_str


class TestRAGEvaluationReport:
    """Tests for RAGEvaluationReport."""

    def test_creation(self):
        results = [
            EvaluationResult(MetricType.ANSWER_RELEVANCE, 0.9),
            EvaluationResult(MetricType.ANSWER_FAITHFULNESS, 0.85),
        ]

        report = RAGEvaluationReport(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
            results=results,
            overall_score=0.875,
        )

        assert report.query == SAMPLE_QUERY
        assert len(report.results) == 2
        assert report.overall_score == 0.875

    def test_get_metric(self):
        results = [
            EvaluationResult(MetricType.ANSWER_RELEVANCE, 0.9),
            EvaluationResult(MetricType.ANSWER_FAITHFULNESS, 0.85),
        ]

        report = RAGEvaluationReport(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
            results=results,
        )

        relevance = report.get_metric(MetricType.ANSWER_RELEVANCE)
        assert relevance is not None
        assert relevance.score == 0.9

        missing = report.get_metric(MetricType.RETRIEVAL_PRECISION)
        assert missing is None

    def test_get_score(self):
        results = [
            EvaluationResult(MetricType.ANSWER_RELEVANCE, 0.9),
        ]

        report = RAGEvaluationReport(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
            results=results,
        )

        score = report.get_score(MetricType.ANSWER_RELEVANCE)
        assert score == 0.9

        missing_score = report.get_score(MetricType.RETRIEVAL_PRECISION)
        assert missing_score is None
