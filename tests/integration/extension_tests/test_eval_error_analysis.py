"""ErrorAnalysis aggregation over tracked run records.

``ErrorAnalysis`` folds a tracker's metric and error records into an
``AnalysisReport`` — error-kind counts, ``score`` statistics, and the most
frequent errors — which the experiment demo persists as
``analysis.json`` (see ``docs/ai/EVALUATION.md``).
"""

from __future__ import annotations

import pytest

from lexigram.ai.evaluation import ErrorAnalysis
from lexigram.ai.evaluation.exceptions import AnalysisError
from lexigram.contracts.ai.experiment import (
    ErrorRecord,
    ExperimentRun,
    MetricRecord,
    RunStatus,
)

_RUN_ID = "run-analysis-1"


def _run() -> ExperimentRun:
    return ExperimentRun(
        run_id=_RUN_ID,
        experiment="llm-relay-probe",
        seed=7,
        config={"model": "claude-3-5-sonnet"},
        config_hash="a" * 64,
        status=RunStatus.COMPLETED,
        started_at="2026-08-21T00:00:00+00:00",
    )


class StubTracker:
    """In-memory tracker stub satisfying the contract boundary."""

    def __init__(
        self,
        metrics: list[MetricRecord],
        errors: list[ErrorRecord],
        known: bool = True,
    ) -> None:
        self._metrics = metrics
        self._errors = errors
        self._known = known

    async def resume(self, run_id: str) -> ExperimentRun | None:
        return _run() if self._known else None

    async def metrics(self, run_id: str) -> list[MetricRecord]:
        return self._metrics

    async def errors(self, run_id: str) -> list[ErrorRecord]:
        return self._errors


@pytest.mark.asyncio
async def test_report_aggregates_error_kinds_and_counts() -> None:
    tracker = StubTracker(
        metrics=[MetricRecord(step=i, name="score", value=0.5) for i in range(3)],
        errors=[
            ErrorRecord(kind="LLM_RATE_LIMITED", message="429", step=0),
            ErrorRecord(kind="LLM_RATE_LIMITED", message="429 again", step=1),
            ErrorRecord(kind="TIMEOUT", message="timed out", step=2),
        ],
    )
    report = await ErrorAnalysis(tracker).report(_RUN_ID)
    assert report.total_records == 3
    assert report.error_count == 3
    assert report.error_kinds == {"LLM_RATE_LIMITED": 2, "TIMEOUT": 1}
    kinds = [error.kind for error in report.top_errors]
    assert kinds == ["LLM_RATE_LIMITED", "TIMEOUT"]


@pytest.mark.asyncio
async def test_report_computes_score_statistics() -> None:
    scores = [0.2, 0.4, 0.9]
    tracker = StubTracker(
        metrics=[MetricRecord(step=i, name="score", value=v) for i, v in enumerate(scores)]
        + [MetricRecord(step=9, name="tokens", value=120.0)],
        errors=[],
    )
    report = await ErrorAnalysis(tracker).report(_RUN_ID)
    assert report.score_mean == pytest.approx(sum(scores) / len(scores))
    assert report.score_min == pytest.approx(0.2)
    assert report.score_max == pytest.approx(0.9)
    assert report.total_records == 4


@pytest.mark.asyncio
async def test_report_without_scores_or_errors_yields_empty_stats() -> None:
    tracker = StubTracker(metrics=[], errors=[])
    report = await ErrorAnalysis(tracker).report(_RUN_ID)
    assert report.total_records == 0
    assert report.error_count == 0
    assert report.error_kinds == {}
    assert report.top_errors == ()
    assert report.score_mean is None
    assert report.score_min is None
    assert report.score_max is None


@pytest.mark.asyncio
async def test_unknown_run_raises_analysis_error() -> None:
    tracker = StubTracker(metrics=[], errors=[], known=False)
    with pytest.raises(AnalysisError, match="unknown run"):
        await ErrorAnalysis(tracker).report("missing-run")
