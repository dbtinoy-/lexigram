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
