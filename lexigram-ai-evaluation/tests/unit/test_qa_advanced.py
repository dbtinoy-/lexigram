"""Advanced tests for QAEvaluator."""

from __future__ import annotations

import pytest

from lexigram.ai.evaluation.evaluators.qa import QAEvaluator


class TestQAEvaluatorAdvanced:
    """Advanced tests for QAEvaluator."""

    @pytest.fixture
    def evaluator(self) -> QAEvaluator:
        return QAEvaluator()

    @pytest.mark.asyncio
    async def test_empty_reference_keywords(self, evaluator: QAEvaluator) -> None:
        result = await evaluator.evaluate("q", "some output", "a")
        assert result.is_ok()
        assert result.unwrap().score == 1.0

    @pytest.mark.asyncio
    async def test_empty_reference_and_empty_output(self, evaluator: QAEvaluator) -> None:
        result = await evaluator.evaluate("q", "", "a")
        assert result.unwrap().score == 0.0

    @pytest.mark.asyncio
    async def test_extract_keywords_skips_stopwords(self, evaluator: QAEvaluator) -> None:
        keywords = evaluator._extract_keywords("the and are for")
        assert keywords == []

    @pytest.mark.asyncio
    async def test_extract_keywords_short_words(self, evaluator: QAEvaluator) -> None:
        keywords = evaluator._extract_keywords("a an is it")
        assert keywords == []

    @pytest.mark.asyncio
    async def test_extract_keywords_only_content_words(self, evaluator: QAEvaluator) -> None:
        keywords = evaluator._extract_keywords("python programming language")
        assert "python" in keywords
        assert "programming" in keywords
        assert "language" in keywords

    @pytest.mark.asyncio
    async def test_extract_keywords_mixed(self, evaluator: QAEvaluator) -> None:
        keywords = evaluator._extract_keywords("the quick brown fox jumps")
        assert "the" not in keywords
        assert "quick" in keywords

    @pytest.mark.asyncio
    async def test_name_property(self, evaluator: QAEvaluator) -> None:
        assert evaluator.name == "qa"

    @pytest.mark.asyncio
    async def test_feedback_mentions_matched_concepts(self, evaluator: QAEvaluator) -> None:
        result = await evaluator.evaluate(
            "What is Python?",
            "Python is a programming language",
            "Python programming language",
        )
        assert result.is_ok()
        assert "Matched" in result.unwrap().feedback

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self, evaluator: QAEvaluator) -> None:
        result = await evaluator.evaluate("q", "PYTHON IS GREAT", "python is great")
        assert result.unwrap().score == 1.0
