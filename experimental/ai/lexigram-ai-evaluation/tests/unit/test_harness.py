"""Unit tests for evaluation harness."""

from __future__ import annotations

import pytest

from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator
from lexigram.ai.evaluation.harness.runner import EvaluationHarness
from lexigram.contracts.ai.evaluation import EvaluationDataset, EvaluationSample


class TestEvaluationHarness:
    """Tests for EvaluationHarness."""

    @pytest.mark.asyncio
    async def test_run_single_sample(self) -> None:
        harness = EvaluationHarness()
        dataset = EvaluationDataset(
            name="test",
            samples=[
                EvaluationSample(
                    id="1",
                    input="What is 2+2?",
                    reference="4",
                    metadata={},
                )
            ],
            metadata={},
        )
        evaluator = CriteriaEvaluator()

        report = (await harness.run(dataset, evaluator)).unwrap()

        assert report.total_samples == 1
        assert report.dataset_name == "test"
        assert report.evaluator_name == "criteria"

    @pytest.mark.asyncio
    async def test_run_multiple_samples(self) -> None:
        harness = EvaluationHarness()
        dataset = EvaluationDataset(
            name="test",
            samples=[
                EvaluationSample(id="1", input="Q1", reference="A", metadata={}),
                EvaluationSample(id="2", input="Q2", reference="B", metadata={}),
            ],
            metadata={},
        )
        evaluator = CriteriaEvaluator()

        report = (await harness.run(dataset, evaluator)).unwrap()

        assert report.total_samples == 2

    @pytest.mark.asyncio
    async def test_average_score_calculation(self) -> None:
        harness = EvaluationHarness()
        dataset = EvaluationDataset(
            name="test",
            samples=[
                EvaluationSample(id="1", input="Q1", reference="correct", metadata={}),
                EvaluationSample(id="2", input="Q2", reference="wrong", metadata={}),
            ],
            metadata={},
        )
        evaluator = CriteriaEvaluator()

        report = (await harness.run(dataset, evaluator)).unwrap()

        assert report.average_score >= 0.0
        assert report.average_score <= 1.0

    @pytest.mark.asyncio
    async def test_repeated_runs_produce_identical_reports(self) -> None:
        """Two runs over a fixed dataset yield identical reports.

        Pins the reproducibility contract at the harness boundary: given
        a deterministic evaluator and an immutable dataset, repeated
        ``run`` calls must agree on totals and per-sample scores, so
        downstream seeded experiments can diff run artifacts reliably.
        """
        harness = EvaluationHarness(pass_threshold=0.5)
        dataset = EvaluationDataset(
            name="repro",
            samples=[
                EvaluationSample(id=f"s{i}", input=f"q{i}", reference="", metadata={})
                for i in range(5)
            ],
            metadata={"seed": 42},
        )
        evaluator = CriteriaEvaluator()

        first = (await harness.run(dataset, evaluator)).unwrap()
        second = (await harness.run(dataset, evaluator)).unwrap()

        assert second.total_samples == first.total_samples == 5
        assert second.passed_samples == first.passed_samples
        assert (
            [r.score for r in second.results] == [r.score for r in first.results]
        )
        assert second.average_score == pytest.approx(first.average_score)
