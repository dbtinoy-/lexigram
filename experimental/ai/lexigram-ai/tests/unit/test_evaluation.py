"""Tests for RAG evaluation framework."""

from __future__ import annotations

from enum import Enum

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.evaluation import (
    AnswerFaithfulnessEvaluator,
    AnswerRelevanceEvaluator,
    ContextRelevanceEvaluator,
    EvaluationResult,
    HallucinationDetector,
    MetricType,
    RAGEvaluationReport,
    RAGEvaluator,
    RetrievalPrecisionEvaluator,
    RetrievalRecallEvaluator,
    evaluate_rag,
)


# Mock LLM client for testing
class _OkResult:
    """Minimal Result-like success wrapper for evaluator tests."""

    def __init__(self, value):
        self._value = value

    def is_err(self):
        return False

    def unwrap(self):
        return self._value

    def unwrap_err(self):
        raise AssertionError("_OkResult has no error")


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, response="0.85"):
        """Initialize with response."""
        self.response = response
        self.calls = []

    async def complete(self, messages=None, prompt=None, **kwargs):
        """Mock completion."""
        if messages:
            content = messages[-1].content if hasattr(messages[-1], 'content') else messages[-1].get('content', '')
        else:
            content = prompt or ""
        self.calls.append(content)

        class MockCompletion:
            def __init__(self, content):
                self.content = content

        return _OkResult(MockCompletion(self.response))


# Test data
SAMPLE_QUERY = "What is machine learning?"
SAMPLE_ANSWER = (
    "Machine learning is a subset of AI that enables systems to learn from data."
)
SAMPLE_DOCS = [
    {
        "id": "doc1",
        "content": "Machine learning is a branch of artificial intelligence.",
    },
    {"id": "doc2", "content": "ML systems learn patterns from data."},
    {"id": "doc3", "content": "Deep learning is a type of machine learning."},
]
RELEVANT_DOC_IDS = {"doc1", "doc2"}


class TestEvaluationResult:
    """Tests for EvaluationResult."""

    def test_creation(self):
        """Test basic creation."""
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
        """Test string representation."""
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
        """Test report creation."""
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
        """Test getting specific metric."""
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
        """Test getting score directly."""
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


class TestRetrievalPrecisionEvaluator:
    """Tests for RetrievalPrecisionEvaluator."""

    @pytest.mark.asyncio
    async def test_perfect_precision(self):
        """Test perfect precision (all retrieved are relevant)."""
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
        """Test partial precision."""
        evaluator = RetrievalPrecisionEvaluator()

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=[{"id": "doc1"}, {"id": "doc3"}],  # doc3 not relevant
            generated_answer=SAMPLE_ANSWER,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        assert result.score == 0.5  # 1 out of 2
        assert result.details["retrieved_count"] == 2
        assert result.details["relevant_retrieved"] == 1

    @pytest.mark.asyncio
    async def test_empty_retrieval(self):
        """Test with no retrieved documents."""
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
        """Test perfect recall (all relevant docs retrieved)."""
        evaluator = RetrievalRecallEvaluator()

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=[{"id": "doc1"}, {"id": "doc2"}, {"id": "doc3"}],
            generated_answer=SAMPLE_ANSWER,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        assert result.metric_type == MetricType.RETRIEVAL_RECALL
        assert result.score == 1.0  # Both relevant docs retrieved
        assert result.details["relevant_count"] == 2
        assert result.details["relevant_retrieved"] == 2

    @pytest.mark.asyncio
    async def test_partial_recall(self):
        """Test partial recall."""
        evaluator = RetrievalRecallEvaluator()

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=[{"id": "doc1"}],  # Missing doc2
            generated_answer=SAMPLE_ANSWER,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        assert result.score == 0.5  # 1 out of 2 relevant
        assert result.details["relevant_retrieved"] == 1

    @pytest.mark.asyncio
    async def test_no_relevant_docs(self):
        """Test with no relevant docs specified."""
        evaluator = RetrievalRecallEvaluator()

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=[{"id": "doc1"}],
            generated_answer=SAMPLE_ANSWER,
            relevant_doc_ids=set(),
        )

        assert result.score == 0.0
        assert "reason" in result.details


class TestAnswerRelevanceEvaluator:
    """Tests for AnswerRelevanceEvaluator."""

    @pytest.mark.asyncio
    async def test_high_relevance(self):
        """Test high relevance score."""
        llm_client = MockLLMClient(response="0.95")
        evaluator = AnswerRelevanceEvaluator(llm_client)

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
        )

        assert result.metric_type == MetricType.ANSWER_RELEVANCE
        assert result.score == 0.95
        assert len(llm_client.calls) == 1
        assert SAMPLE_QUERY in llm_client.calls[0]
        assert SAMPLE_ANSWER in llm_client.calls[0]

    @pytest.mark.asyncio
    async def test_low_relevance(self):
        """Test low relevance score."""
        llm_client = MockLLMClient(response="0.2")
        evaluator = AnswerRelevanceEvaluator(llm_client)

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer="The sky is blue.",  # Irrelevant
        )

        assert result.score == 0.2

    @pytest.mark.asyncio
    async def test_clamping(self):
        """Test score clamping to [0, 1]."""
        llm_client = MockLLMClient(response="1.5")  # Over 1.0
        evaluator = AnswerRelevanceEvaluator(llm_client)

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
        )

        assert result.score == 1.0  # Clamped

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling."""
        llm_client = MockLLMClient(response="invalid")
        evaluator = AnswerRelevanceEvaluator(llm_client)

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
        )

        assert result.score == 0.0
        assert "error" in result.details


class TestAnswerFaithfulnessEvaluator:
    """Tests for AnswerFaithfulnessEvaluator."""

    @pytest.mark.asyncio
    async def test_faithful_answer(self):
        """Test faithful answer."""
        llm_client = MockLLMClient(response="0.95")
        evaluator = AnswerFaithfulnessEvaluator(llm_client)

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
        )

        assert result.metric_type == MetricType.ANSWER_FAITHFULNESS
        assert result.score == 0.95
        assert len(llm_client.calls) == 1
        # Check context was included
        assert "Machine learning" in llm_client.calls[0]

    @pytest.mark.asyncio
    async def test_unfaithful_answer(self):
        """Test unfaithful answer."""
        llm_client = MockLLMClient(response="0.1")
        evaluator = AnswerFaithfulnessEvaluator(llm_client)

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer="Machine learning was invented in 3000 BC.",  # Not in context
        )

        assert result.score == 0.1


class TestContextRelevanceEvaluator:
    """Tests for ContextRelevanceEvaluator."""

    @pytest.mark.asyncio
    async def test_relevant_context(self):
        """Test relevant context."""
        llm_client = MockLLMClient(response="0.9")
        evaluator = ContextRelevanceEvaluator(llm_client)

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
        )

        assert result.metric_type == MetricType.CONTEXT_RELEVANCE
        assert result.score == 0.9
        assert result.details["context_chunks"] == 3

    @pytest.mark.asyncio
    async def test_empty_context(self):
        """Test empty context."""
        llm_client = MockLLMClient(response="0.9")
        evaluator = ContextRelevanceEvaluator(llm_client)

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=[],
            generated_answer=SAMPLE_ANSWER,
        )

        assert result.score == 0.0
        assert "reason" in result.details
        assert len(llm_client.calls) == 0  # Should not call LLM


class TestHallucinationDetector:
    """Tests for HallucinationDetector."""

    @pytest.mark.asyncio
    async def test_no_hallucinations(self):
        """Test answer with no hallucinations."""
        llm_client = MockLLMClient(response="0.0")
        detector = HallucinationDetector(llm_client)

        result = await detector.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
        )

        assert result.metric_type == MetricType.HALLUCINATION_RATE
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_high_hallucination(self):
        """Test answer with high hallucinations."""
        llm_client = MockLLMClient(response="0.8")
        detector = HallucinationDetector(llm_client)

        result = await detector.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer="Machine learning was created by aliens.",
        )

        assert result.score == 0.8

    @pytest.mark.asyncio
    async def test_error_defaults_to_worst(self):
        """Test that errors default to worst case (1.0)."""
        llm_client = MockLLMClient(response="invalid")
        detector = HallucinationDetector(llm_client)

        result = await detector.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
        )

        assert result.score == 1.0  # Worst case
        assert "error" in result.details


class TestRAGEvaluator:
    """Tests for RAGEvaluator."""

    @pytest.mark.asyncio
    async def test_multiple_evaluators(self):
        """Test running multiple evaluators."""
        llm_client = MockLLMClient(response="0.85")

        evaluator = RAGEvaluator(
            evaluators=[
                RetrievalPrecisionEvaluator(),
                AnswerRelevanceEvaluator(llm_client),
            ],
        )

        report = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        assert len(report.results) == 2
        assert report.query == SAMPLE_QUERY
        assert report.overall_score > 0

    @pytest.mark.asyncio
    async def test_add_evaluator(self):
        """Test adding evaluators."""
        evaluator = RAGEvaluator()
        assert len(evaluator.evaluators) == 0

        evaluator.add_evaluator(RetrievalPrecisionEvaluator())
        assert len(evaluator.evaluators) == 1

    @pytest.mark.asyncio
    async def test_weighted_overall_score(self):
        """Test weighted overall score calculation."""
        llm_client = MockLLMClient(response="0.8")

        weights = {
            MetricType.ANSWER_RELEVANCE: 0.6,
            MetricType.ANSWER_FAITHFULNESS: 0.4,
        }

        evaluator = RAGEvaluator(
            evaluators=[
                AnswerRelevanceEvaluator(llm_client),
                AnswerFaithfulnessEvaluator(llm_client),
            ],
            weights=weights,
        )

        report = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
        )

        # Both metrics return 0.8, so weighted average should be 0.8
        assert report.overall_score == 0.8

    @pytest.mark.asyncio
    async def test_hallucination_inverted_in_overall_score(self):
        """Test that hallucination rate is inverted in overall score."""
        llm_client = MockLLMClient(response="0.2")  # Low hallucination

        evaluator = RAGEvaluator(
            evaluators=[
                HallucinationDetector(llm_client),
            ],
        )

        report = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
        )

        # Hallucination rate is 0.2, but should be inverted for overall score
        # So overall score should be 0.8 (1.0 - 0.2)
        assert report.overall_score == 0.8


class TestEvaluateRAGFunction:
    """Tests for evaluate_rag convenience function."""

    @pytest.mark.asyncio
    async def test_with_llm_client(self):
        """Test with LLM client (should add LLM-based evaluators)."""
        llm_client = MockLLMClient(response="0.85")

        report = await evaluate_rag(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
            llm_client=llm_client,
        )

        # Should have LLM-based metrics
        assert (
            len(report.results) == 4
        )  # relevance, faithfulness, context, hallucination

    @pytest.mark.asyncio
    async def test_with_relevant_doc_ids(self):
        """Test with relevant doc IDs (should add retrieval metrics)."""
        report = await evaluate_rag(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        # Should have retrieval metrics
        assert report.get_metric(MetricType.RETRIEVAL_PRECISION) is not None
        assert report.get_metric(MetricType.RETRIEVAL_RECALL) is not None

    @pytest.mark.asyncio
    async def test_with_custom_evaluators(self):
        """Test with custom evaluators."""
        custom_evaluator = RetrievalPrecisionEvaluator()

        report = await evaluate_rag(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
            evaluators=[custom_evaluator],
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        assert len(report.results) == 1


class TestIntegration:
    """Integration tests for complete evaluation workflows."""

    @pytest.mark.asyncio
    async def test_complete_evaluation(self):
        """Test complete evaluation with all metrics."""
        llm_client = MockLLMClient(response="0.85")

        report = await evaluate_rag(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
            reference_answer="ML is a subset of AI.",
            llm_client=llm_client,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        # Should have both retrieval and LLM-based metrics
        assert len(report.results) >= 6
        assert report.overall_score > 0
        assert report.reference_answer is not None

    @pytest.mark.asyncio
    async def test_report_access_methods(self):
        """Test report access methods."""
        llm_client = MockLLMClient(response="0.9")

        report = await evaluate_rag(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
            llm_client=llm_client,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        # Test get_metric
        relevance_result = report.get_metric(MetricType.ANSWER_RELEVANCE)
        assert relevance_result is not None
        assert relevance_result.score == 0.9

        # Test get_score
        relevance_score = report.get_score(MetricType.ANSWER_RELEVANCE)
        assert relevance_score == 0.9

        # Test missing metric
        assert report.get_metric(MetricType.COST) is None
        assert report.get_score(MetricType.COST) is None
