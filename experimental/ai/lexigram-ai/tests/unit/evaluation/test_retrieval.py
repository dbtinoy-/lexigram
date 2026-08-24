"""Tests for retrieval evaluators."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.evaluation import MetricType, RetrievalPrecisionEvaluator, RetrievalRecallEvaluator
SAMPLE_QUERY = "What is machine learning?"
SAMPLE_ANSWER = "Machine learning is a subset of AI that enables systems to learn from data."
SAMPLE_DOCS = [
    {"id": "doc1", "content": "Machine learning is a branch of artificial intelligence."},
    {"id": "doc2", "content": "ML systems learn patterns from data."},
    {"id": "doc3", "content": "Deep learning is a type of machine learning."},
]
RELEVANT_DOC_IDS = {"doc1", "doc2"}


class TestRetrievalPrecisionEvaluator:
    """Tests for RetrievalPrecisionEvaluator."""

    @pytest.mark.asyncio
    async def test_perfect_precision(self):
        evaluator = RetrievalPrecisionEvaluator()

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=[{"id": "doc1"}, {"id": "doc2"}],
            generated_answer=SAMPLE_ANSWER,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        assert result.metric_type == MetricType.RETRIEVAL_PRECISION
        assert result.score == 1.0
        assert result.details["retrieved_count"] == 2
        assert result.details["relevant_retrieved"] == 2

    @pytest.mark.asyncio
    async def test_partial_precision(self):
        evaluator = RetrievalPrecisionEvaluator()

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=[{"id": "doc1"}, {"id": "doc3"}],
            generated_answer=SAMPLE_ANSWER,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        assert result.score == 0.5
        assert result.details["retrieved_count"] == 2
        assert result.details["relevant_retrieved"] == 1

    @pytest.mark.asyncio
    async def test_empty_retrieval(self):
        evaluator = RetrievalPrecisionEvaluator()

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=[],
            generated_answer=SAMPLE_ANSWER,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        assert result.score == 0.0
        assert "reason" in result.details


class TestRetrievalRecallEvaluator:
    """Tests for RetrievalRecallEvaluator."""

    @pytest.mark.asyncio
    async def test_perfect_recall(self):
        evaluator = RetrievalRecallEvaluator()

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=[{"id": "doc1"}, {"id": "doc2"}, {"id": "doc3"}],
            generated_answer=SAMPLE_ANSWER,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        assert result.metric_type == MetricType.RETRIEVAL_RECALL
        assert result.score == 1.0
        assert result.details["relevant_count"] == 2
        assert result.details["relevant_retrieved"] == 2

    @pytest.mark.asyncio
    async def test_partial_recall(self):
        evaluator = RetrievalRecallEvaluator()

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=[{"id": "doc1"}],
            generated_answer=SAMPLE_ANSWER,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        assert result.score == 0.5
        assert result.details["relevant_retrieved"] == 1

    @pytest.mark.asyncio
    async def test_no_relevant_docs(self):
        evaluator = RetrievalRecallEvaluator()

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=[{"id": "doc1"}],
            generated_answer=SAMPLE_ANSWER,
            relevant_doc_ids=set(),
        )

        assert result.score == 0.0
        assert "reason" in result.details
