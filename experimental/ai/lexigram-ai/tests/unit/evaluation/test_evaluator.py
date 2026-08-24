"""Tests for RAGEvaluator and evaluate_rag convenience function."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.evaluation import (
    AnswerFaithfulnessEvaluator,
    AnswerRelevanceEvaluator,
    MetricType,
    RAGEvaluator,
    RetrievalPrecisionEvaluator,
    evaluate_rag,
)
SAMPLE_QUERY = "What is machine learning?"
SAMPLE_ANSWER = "Machine learning is a subset of AI that enables systems to learn from data."
SAMPLE_DOCS = [
    {"id": "doc1", "content": "Machine learning is a branch of artificial intelligence."},
    {"id": "doc2", "content": "ML systems learn patterns from data."},
    {"id": "doc3", "content": "Deep learning is a type of machine learning."},
]
RELEVANT_DOC_IDS = {"doc1", "doc2"}


class _OkResult:
    def __init__(self, value):
        self._value = value
    def is_err(self):
        return False
    def unwrap(self):
        return self._value
    def unwrap_err(self):
        raise AssertionError("_OkResult has no error")


class MockLLMClient:
    def __init__(self, response="0.85"):
        self.response = response
        self.calls = []
    async def complete(self, messages=None, prompt=None, **kwargs):
        if messages:
            content = messages[-1].content if hasattr(messages[-1], 'content') else messages[-1].get('content', '')
        else:
            content = prompt or ""
        self.calls.append(content)
        class MockCompletion:
            def __init__(self, content):
                self.content = content
        return _OkResult(MockCompletion(self.response))


class TestRAGEvaluator:
    """Tests for RAGEvaluator."""

    @pytest.mark.asyncio
    async def test_multiple_evaluators(self):
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
        evaluator = RAGEvaluator()
        assert len(evaluator.evaluators) == 0

        evaluator.add_evaluator(RetrievalPrecisionEvaluator())
        assert len(evaluator.evaluators) == 1

    @pytest.mark.asyncio
    async def test_weighted_overall_score(self):
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

        assert report.overall_score == 0.8

    @pytest.mark.asyncio
    async def test_hallucination_inverted_in_overall_score(self):
        llm_client = MockLLMClient(response="0.2")

        from lexigram.ai.rag.evaluation import HallucinationDetector

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

        assert report.overall_score == 0.8


class TestEvaluateRAGFunction:
    """Tests for evaluate_rag convenience function."""

    @pytest.mark.asyncio
    async def test_with_llm_client(self):
        llm_client = MockLLMClient(response="0.85")

        report = await evaluate_rag(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
            llm_client=llm_client,
        )

        assert len(report.results) == 4

    @pytest.mark.asyncio
    async def test_with_relevant_doc_ids(self):
        report = await evaluate_rag(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        assert report.get_metric(MetricType.RETRIEVAL_PRECISION) is not None
        assert report.get_metric(MetricType.RETRIEVAL_RECALL) is not None

    @pytest.mark.asyncio
    async def test_with_custom_evaluators(self):
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
        llm_client = MockLLMClient(response="0.85")

        report = await evaluate_rag(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
            reference_answer="ML is a subset of AI.",
            llm_client=llm_client,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        assert len(report.results) >= 6
        assert report.overall_score > 0
        assert report.reference_answer is not None

    @pytest.mark.asyncio
    async def test_report_access_methods(self):
        llm_client = MockLLMClient(response="0.9")

        report = await evaluate_rag(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
            llm_client=llm_client,
            relevant_doc_ids=RELEVANT_DOC_IDS,
        )

        relevance_result = report.get_metric(MetricType.ANSWER_RELEVANCE)
        assert relevance_result is not None
        assert relevance_result.score == 0.9

        relevance_score = report.get_score(MetricType.ANSWER_RELEVANCE)
        assert relevance_score == 0.9

        assert report.get_metric(MetricType.COST) is None
        assert report.get_score(MetricType.COST) is None
