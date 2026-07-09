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
    async def test_wrong_output_against_keywordless_reference_scores_zero(
        self, evaluator: QAEvaluator
    ) -> None:
        result = await evaluator.evaluate("q", "some output", "a")
        assert result.is_ok()
        assert result.unwrap().score == 0.0

    @pytest.mark.asyncio
    async def test_empty_reference_and_empty_output(self, evaluator: QAEvaluator) -> None:
        result = await evaluator.evaluate("q", "", "a")
        assert result.unwrap().score == 0.0

    @pytest.mark.asyncio
    async def test_numeric_reference_exact_match_scores_one(
        self, evaluator: QAEvaluator
    ) -> None:
        result = await evaluator.evaluate("2 + 2?", "42", "42")
        assert result.unwrap().score == 1.0

    @pytest.mark.asyncio
    async def test_numeric_reference_wrong_output_scores_zero(
        self, evaluator: QAEvaluator
    ) -> None:
        result = await evaluator.evaluate("2 + 2?", "The sky is green", "42")
        assert result.unwrap().score == 0.0

    @pytest.mark.asyncio
    async def test_keywordless_reference_substring_match_scores_one(
        self, evaluator: QAEvaluator
    ) -> None:
        result = await evaluator.evaluate("q", "yes please", "yes")
        assert result.unwrap().score == 1.0

    @pytest.mark.asyncio
    async def test_keywordless_reference_containment_is_case_insensitive(
        self, evaluator: QAEvaluator
    ) -> None:
        result = await evaluator.evaluate("q", "N/A unavailable", "n/a")
        assert result.unwrap().score == 1.0

    @pytest.mark.asyncio
    async def test_blank_reference_scores_zero_for_any_output(
        self, evaluator: QAEvaluator
    ) -> None:
        result = await evaluator.evaluate("q", "anything at all", "")
        assert result.unwrap().score == 0.0

    @pytest.mark.asyncio
    async def test_fallback_feedback_declares_containment_match(
        self, evaluator: QAEvaluator
    ) -> None:
        result = await evaluator.evaluate("q", "42", "42")
        assert "containment" in result.unwrap().feedback

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
