"""Run analysis for the AI evaluation framework.

The :class:`ErrorAnalysis` aggregates a tracked run's metric and error
records into an :class:`~lexigram.contracts.ai.experiment.AnalysisReport`
with error-kind counts, score statistics, and the most frequent errors —
the input for post-hoc error analysis of failed trials.
"""

from __future__ import annotations

from collections import Counter

from lexigram.ai.evaluation.exceptions import AnalysisError
from lexigram.contracts.ai.experiment import (
    AnalysisReport,
    ErrorRecord,
    ExperimentTrackerProtocol,
)

_SCORE_METRIC = "score"
_TOP_ERRORS_LIMIT = 10


class ErrorAnalysis:
    """Aggregate a run's tracked records into an analysis report.

    Args:
        tracker: Tracker holding the run's metric and error records.
    """

    def __init__(self, tracker: ExperimentTrackerProtocol) -> None:
        self._tracker = tracker

    async def report(self, run_id: str) -> AnalysisReport:
        """Produce an analysis report for a run.

        Args:
            run_id: Run identifier.

        Returns:
            Aggregated error kinds, score statistics, and top errors.

        Raises:
            AnalysisError: If the run is unknown to the tracker.
        """
        run = await self._tracker.resume(run_id)
        if run is None:
            raise AnalysisError(f"unknown run {run_id!r}")
        metrics = await self._tracker.metrics(run_id)
        errors = await self._tracker.errors(run_id)

        scores = [record.value for record in metrics if record.name == _SCORE_METRIC]
        score_stats = (
            (sum(scores) / len(scores), min(scores), max(scores))
            if scores
            else (None, None, None)
        )

        kinds = Counter(error.kind for error in errors)
        first_of_kind: dict[str, ErrorRecord] = {}
        for error in errors:
            if error.kind not in first_of_kind:
                first_of_kind[error.kind] = error
        top_errors = tuple(
            first_of_kind[kind] for kind, _count in kinds.most_common(_TOP_ERRORS_LIMIT)
        )

        return AnalysisReport(
            total_records=len(metrics),
            error_count=len(errors),
            error_kinds=dict(kinds),
            score_mean=score_stats[0],
            score_min=score_stats[1],
            score_max=score_stats[2],
            top_errors=top_errors,
        )


__all__ = ["ErrorAnalysis"]
