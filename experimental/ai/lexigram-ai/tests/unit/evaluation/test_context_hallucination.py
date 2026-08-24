"""Tests for context and hallucination evaluators."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.evaluation import ContextRelevanceEvaluator, HallucinationDetector, MetricType
SAMPLE_QUERY = "What is machine learning?"
SAMPLE_ANSWER = "Machine learning is a subset of AI that enables systems to learn from data."
SAMPLE_DOCS = [
    {"id": "doc1", "content": "Machine learning is a branch of artificial intelligence."},
    {"id": "doc2", "content": "ML systems learn patterns from data."},
    {"id": "doc3", "content": "Deep learning is a type of machine learning."},
]


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


class TestContextRelevanceEvaluator:
    """Tests for ContextRelevanceEvaluator."""

    @pytest.mark.asyncio
    async def test_relevant_context(self):
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
        llm_client = MockLLMClient(response="0.9")
        evaluator = ContextRelevanceEvaluator(llm_client)

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=[],
            generated_answer=SAMPLE_ANSWER,
        )

        assert result.score == 0.0
        assert "reason" in result.details
        assert len(llm_client.calls) == 0


class TestHallucinationDetector:
    """Tests for HallucinationDetector."""

    @pytest.mark.asyncio
    async def test_no_hallucinations(self):
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
        llm_client = MockLLMClient(response="invalid")
        detector = HallucinationDetector(llm_client)

        result = await detector.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
        )

        assert result.score == 1.0
        assert "error" in result.details
