"""Tests for answer evaluators."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.evaluation import AnswerFaithfulnessEvaluator, AnswerRelevanceEvaluator, MetricType
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


class TestAnswerRelevanceEvaluator:
    """Tests for AnswerRelevanceEvaluator."""

    @pytest.mark.asyncio
    async def test_high_relevance(self):
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
        llm_client = MockLLMClient(response="0.2")
        evaluator = AnswerRelevanceEvaluator(llm_client)

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer="The sky is blue.",
        )

        assert result.score == 0.2

    @pytest.mark.asyncio
    async def test_clamping(self):
        llm_client = MockLLMClient(response="1.5")
        evaluator = AnswerRelevanceEvaluator(llm_client)

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer=SAMPLE_ANSWER,
        )

        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_error_handling(self):
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
        assert "Machine learning" in llm_client.calls[0]

    @pytest.mark.asyncio
    async def test_unfaithful_answer(self):
        llm_client = MockLLMClient(response="0.1")
        evaluator = AnswerFaithfulnessEvaluator(llm_client)

        result = await evaluator.evaluate(
            query=SAMPLE_QUERY,
            retrieved_docs=SAMPLE_DOCS,
            generated_answer="Machine learning was invented in 3000 BC.",
        )

        assert result.score == 0.1
