"""Advanced tests for EvaluationHarness."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.evaluation.harness.runner import EvaluationHarness
from lexigram.contracts.ai.evaluation import (
    EvaluationDataset,
    EvaluationResult,
    EvaluationSample,
    EvaluationScoreType,
)
from lexigram.result import Ok, Err


class TestEvaluationHarnessAdvanced:
    """Advanced tests for EvaluationHarness."""

    @pytest.fixture
    def harness(self) -> EvaluationHarness:
        return EvaluationHarness(pass_threshold=0.7)

    @pytest.fixture
    def mock_evaluator(self) -> MagicMock:
        evaluator = MagicMock()
        evaluator.name = "test_evaluator"
        evaluator.evaluate = AsyncMock(
            return_value=Ok(
                EvaluationResult(score=0.9, score_type=EvaluationScoreType.EXACT_MATCH, feedback="good", metrics={}),
            ),
        )
        return evaluator

    @pytest.mark.asyncio
    async def test_run_with_single_sample(
        self, harness: EvaluationHarness, mock_evaluator: MagicMock,
    ) -> None:
        dataset = EvaluationDataset(
            name="test",
            samples=[EvaluationSample(input="q", reference="a", id="1", metadata={})],
            metadata={},
        )
        result = await harness.run(dataset, mock_evaluator)
        assert result.is_ok()
        report = result.unwrap()
        assert report.total_samples == 1
        assert report.passed_samples == 1

    @pytest.mark.asyncio
    async def test_run_with_mixed_results(self, harness: EvaluationHarness) -> None:
        evaluator = MagicMock()
        evaluator.name = "mixed"

        async def side_effect(inp: str, output: str, ref: str) -> Ok:
            score = 0.9 if inp == "good" else 0.3
            return Ok(EvaluationResult(score=score, score_type=EvaluationScoreType.EXACT_MATCH, feedback="", metrics={}))

        evaluator.evaluate = AsyncMock(side_effect=side_effect)
        dataset = EvaluationDataset(
            name="mixed",
            samples=[
                EvaluationSample(input="good", reference="a", id="1", metadata={}),
                EvaluationSample(input="bad", reference="b", id="2", metadata={}),
            ],
            metadata={},
        )
        result = await harness.run(dataset, evaluator)
        assert result.is_ok()
        report = result.unwrap()
        assert report.total_samples == 2
        assert report.passed_samples == 1
        assert report.average_score == pytest.approx(0.6)

    @pytest.mark.asyncio
    async def test_run_with_evaluator_error(self, harness: EvaluationHarness) -> None:
        evaluator = MagicMock()
        evaluator.name = "failing"
        evaluator.evaluate = AsyncMock(return_value=Err(ValueError("evaluation error")))

        dataset = EvaluationDataset(
            name="failing",
            samples=[EvaluationSample(input="q", reference="a", id="1", metadata={})],
            metadata={},
        )
        result = await harness.run(dataset, evaluator)
        assert result.is_ok()
        report = result.unwrap()
        assert report.total_samples == 1
        assert report.passed_samples == 0
        assert report.average_score == 0.0

    @pytest.mark.asyncio
    async def test_run_with_exception_in_loop(self, harness: EvaluationHarness) -> None:
        evaluator = MagicMock()
        evaluator.name = "crash"
        evaluator.evaluate = AsyncMock(side_effect=RuntimeError("unexpected crash"))

        dataset = EvaluationDataset(
            name="crash",
            samples=[EvaluationSample(input="q", reference="a", id="1", metadata={})],
            metadata={},
        )
        result = await harness.run(dataset, evaluator)
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_run_empty_dataset(self, harness: EvaluationHarness) -> None:
        evaluator = MagicMock()
        evaluator.name = "empty"
        evaluator.evaluate = AsyncMock()

        dataset = EvaluationDataset(name="empty", samples=[], metadata={})
        result = await harness.run(dataset, evaluator)
        assert result.is_ok()
        report = result.unwrap()
        assert report.total_samples == 0
        assert report.average_score == 0.0

    @pytest.mark.asyncio
    async def test_run_custom_pass_threshold(self) -> None:
        harness = EvaluationHarness(pass_threshold=0.5)
        evaluator = MagicMock()
        evaluator.name = "custom"
        evaluator.evaluate = AsyncMock(
            return_value=Ok(EvaluationResult(score=0.6, score_type=EvaluationScoreType.EXACT_MATCH, feedback="", metrics={})),
        )
        dataset = EvaluationDataset(
            name="custom",
            samples=[EvaluationSample(input="q", reference="a", id="1", metadata={})],
            metadata={},
        )
        result = await harness.run(dataset, evaluator)
        assert result.is_ok()
        assert result.unwrap().passed_samples == 1

    def test_name_property(self, harness: EvaluationHarness) -> None:
        assert harness.name == "evaluation_harness"
