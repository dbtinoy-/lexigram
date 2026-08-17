"""Additional tests for StringDistanceEvaluator."""

from __future__ import annotations

import pytest

from lexigram.ai.evaluation.evaluators.string_distance import StringDistanceEvaluator


class TestStringDistanceEvaluatorEdgeCases:
    """Edge case tests for StringDistanceEvaluator."""

    @pytest.mark.asyncio
    async def test_levenshtein_empty_strings(self) -> None:
        evaluator = StringDistanceEvaluator(metric="levenshtein")
        result = await evaluator.evaluate("", "", "")
        assert result.is_ok()
        assert result.unwrap().score == 1.0

    @pytest.mark.asyncio
    async def test_levenshtein_completely_different(self) -> None:
        evaluator = StringDistanceEvaluator(metric="levenshtein")
        result = await evaluator.evaluate("q", "abc", "xyz")
        assert result.unwrap().score < 0.5

    @pytest.mark.asyncio
    async def test_jaccard_empty_set(self) -> None:
        evaluator = StringDistanceEvaluator(metric="jaccard")
        result = await evaluator.evaluate("q", "", "")
        assert result.is_ok()
        assert result.unwrap().score == 0.0

    @pytest.mark.asyncio
    async def test_jaccard_partial_overlap(self) -> None:
        evaluator = StringDistanceEvaluator(metric="jaccard")
        result = await evaluator.evaluate("q", "hello world", "world hello")
        assert result.unwrap().score == 1.0

    @pytest.mark.asyncio
    async def test_unknown_metric_fallback_to_jaccard(self) -> None:
        evaluator = StringDistanceEvaluator(metric="unknown")
        result = await evaluator.evaluate("q", "hello", "hello")
        assert result.unwrap().score == 1.0

    @pytest.mark.asyncio
    async def test_levenshtein_distance_internal(self) -> None:
        evaluator = StringDistanceEvaluator()
        dist = evaluator._levenshtein_distance("kitten", "sitting")
        assert dist == 3

    @pytest.mark.asyncio
    async def test_levenshtein_distance_second_longer(self) -> None:
        evaluator = StringDistanceEvaluator()
        dist = evaluator._levenshtein_distance("a", "abc")
        assert dist == 2

    @pytest.mark.asyncio
    async def test_levenshtein_distance_empty_second(self) -> None:
        evaluator = StringDistanceEvaluator()
        dist = evaluator._levenshtein_distance("abc", "")
        assert dist == 3

    def test_name_property(self) -> None:
        evaluator = StringDistanceEvaluator()
        assert evaluator.name == "string_distance"
