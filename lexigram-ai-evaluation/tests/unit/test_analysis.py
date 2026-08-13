"""Tests for the error analysis module."""

from __future__ import annotations

import pytest

from lexigram.ai.evaluation.analysis import ErrorAnalysis
from lexigram.ai.evaluation.exceptions import AnalysisError
from lexigram.ai.evaluation.tracking import LocalTracker
from lexigram.contracts.ai.experiment import ExperimentConfig


class TestErrorAnalysis:
    async def test_report_aggregates_scores_and_errors(self, tmp_path) -> None:
        tracker = LocalTracker(root=tmp_path)
        run = await tracker.start(ExperimentConfig(name="probe", seed=42, config={}))
        for step in range(3):
            await tracker.log_metric(run.run_id, "score", 0.9 - step * 0.1, step=step)
        await tracker.log_error(run.run_id, "LLM_RATE_LIMITED", "429", step=0)
        await tracker.log_error(run.run_id, "LLM_RATE_LIMITED", "429", step=1)
        await tracker.log_error(run.run_id, "TIMEOUT", "slow", step=2)

        report = await ErrorAnalysis(tracker).report(run.run_id)

        assert report.total_records == 3
        assert report.error_count == 3
        assert report.error_kinds == {"LLM_RATE_LIMITED": 2, "TIMEOUT": 1}
        assert report.score_mean == pytest.approx(0.8)
        assert report.score_min == 0.7
        assert report.score_max == 0.9
        assert report.top_errors[0].kind == "LLM_RATE_LIMITED"

    async def test_report_without_scores_has_none_stats(self, tmp_path) -> None:
        tracker = LocalTracker(root=tmp_path)
        run = await tracker.start(ExperimentConfig(name="probe", seed=42, config={}))
        await tracker.log_metric(run.run_id, "tokens", 100.0, step=0)
        report = await ErrorAnalysis(tracker).report(run.run_id)
        assert report.score_mean is None
        assert report.score_min is None
        assert report.score_max is None

    async def test_report_unknown_run_raises(self, tmp_path) -> None:
        tracker = LocalTracker(root=tmp_path)
        with pytest.raises(AnalysisError):
            await ErrorAnalysis(tracker).report("nope-1-abcdef12")
