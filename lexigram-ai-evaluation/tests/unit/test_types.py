"""Tests for evaluation types."""

from __future__ import annotations

import pytest

from lexigram.ai.evaluation.types import BatchEvaluationResult, EvaluationRunContext
from lexigram.contracts.ai.evaluation import (
    EvaluationDataset,
    EvaluationResult,
    EvaluationSample,
    EvaluationScoreType,
)


class TestEvaluationRunContext:
    """Tests for EvaluationRunContext dataclass."""

    def test_stores_fields(self) -> None:
        dataset = EvaluationDataset(name="test", samples=[], metadata={})
        ctx = EvaluationRunContext(
            dataset=dataset,
            evaluator_name="criteria",
        )
        assert ctx.dataset is dataset
        assert ctx.evaluator_name == "criteria"
        assert ctx.config == {}

    def test_different_evaluator_names(self) -> None:
        dataset = EvaluationDataset(name="d", samples=[], metadata={})
        ctx = EvaluationRunContext(dataset=dataset, evaluator_name="qa")
        assert ctx.evaluator_name == "qa"


class TestBatchEvaluationResult:
    """Tests for BatchEvaluationResult."""

    def _make_result(self, score: float = 1.0) -> EvaluationResult:
        return EvaluationResult(
            score=score,
            score_type=EvaluationScoreType.EXACT_MATCH,
            feedback="ok",
            metrics={},
        )

    def test_stores_results_list(self) -> None:
        results = [self._make_result(0.8), self._make_result(0.6)]
        batch = BatchEvaluationResult(total_samples=2, passed_samples=2, results=results, average_score=0.7)
        assert len(batch.results) == 2
        assert batch.average_score == 0.7

    def test_empty_batch(self) -> None:
        batch = BatchEvaluationResult(total_samples=0, passed_samples=0, results=[], average_score=0.0)
        assert batch.results == []
        assert batch.average_score == 0.0


class TestEvaluationDataset:
    """Tests for EvaluationDataset from contracts."""

    def test_dataset_with_samples(self) -> None:
        sample = EvaluationSample(id="s1", input="q", reference="a", metadata={})
        dataset = EvaluationDataset(name="my_dataset", samples=[sample], metadata={})
        assert dataset.name == "my_dataset"
        assert len(dataset.samples) == 1

    def test_empty_dataset(self) -> None:
        dataset = EvaluationDataset(name="empty", samples=[], metadata={})
        assert len(dataset.samples) == 0
