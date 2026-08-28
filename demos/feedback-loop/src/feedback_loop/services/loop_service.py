"""Orchestrates bot answers, rating capture, regression runs.

Convention: the service layer owns business logic.  ``LoopService``
exposes the five core operations — ``ask``, ``rate``, ``stats``,
``regress``, ``report`` — each returning ``Result[T, E]`` for expected
domain failures.

The service delegates storage to ``FeedbackCollector`` (in-memory mode)
and evaluation to ``EvaluationHarness`` via the container.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from feedback_loop.errors import (
    InvalidRatingError,
    NoLowRatedError,
    UnknownQuestionError,
    UnknownTraceError,
)
from feedback_loop.repository import BOT, TRACE_IDS
from feedback_loop.services.regression import build_dataset
from lexigram.contracts.ai.evaluation import EvaluationHarnessProtocol
from lexigram.contracts.ai.experiment import ExperimentConfig, RunStatus
from lexigram.contracts.ai.feedback import FeedbackType
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


PASS_THRESHOLD = 0.6
_EXPERIMENT_SEED = 7


@dataclass(frozen=True)
class Answer:
    """A canned reply bound to its stable trace id."""

    trace_id: str
    question_key: str
    question: str
    answer: str


@dataclass(frozen=True)
class StatsSnapshot:
    """Aggregate of captured ratings for one owner."""

    total: int
    average: float | None
    by_type: dict[str, int]


@dataclass(frozen=True)
class RunSummary:
    """Outcome of one regression run."""

    run_id: str
    total_samples: int
    passed_samples: int
    average_score: float
    failing_ids: list[str] = field(default_factory=list)


class LoopService:
    """Ask → rate → stats → regress → report as Result-returning steps."""

    def __init__(
        self,
        collector,
        harness: EvaluationHarnessProtocol | None = None,
        tracker=None,
    ) -> None:
        self._collector = collector
        if harness is not None:
            self._harness = harness
        else:
            from lexigram.ai.evaluation.harness.runner import EvaluationHarness

            self._harness = EvaluationHarness(pass_threshold=PASS_THRESHOLD)
        self._tracker = tracker

    async def ask(
        self,
        key: str,
        *,
        owner: str,
    ) -> Result[Answer, UnknownQuestionError]:
        """Answer a known question; issue its stable trace id."""
        if key not in BOT:
            return Err(UnknownQuestionError(f"unknown question: {key!r}"))
        return Ok(
            Answer(
                trace_id=TRACE_IDS[key],
                question_key=key,
                question=key.replace("-", " "),
                answer=BOT[key],
            ),
        )

    async def rate(
        self,
        trace_id: str,
        rating: float,
        *,
        owner: str,
        comment: str | None = None,
    ) -> Result[str, UnknownTraceError | InvalidRatingError]:
        """Capture a rating for a previously issued trace id."""
        keys_by_trace = {v: k for k, v in TRACE_IDS.items()}
        if trace_id not in keys_by_trace:
            return Err(UnknownTraceError(f"unknown trace: {trace_id!r}"))
        value = float(rating)
        if not 1.0 <= value <= 5.0:
            return Err(InvalidRatingError(f"rating out of range: {rating!r}"))

        key = keys_by_trace[trace_id]
        item_id = await self._collector.collect_rating(
            value,
            owner_id=owner,
            context={
                "trace_id": trace_id,
                "question_key": key,
                "question": key.replace("-", " "),
                "answer": BOT[key],
                "comment": comment or "",
            },
            metadata={"source": "web"},
        )
        return Ok(item_id)

    async def stats(self, *, owner: str) -> StatsSnapshot:
        """Aggregate this owner's captured ratings (memory mode)."""
        items = await self._collector.get_feedback(owner_id=owner)
        total = len(items)
        values = [float(i.value) for i in items]
        average = round(sum(values) / total, 4) if total else None
        by_type: dict[str, int] = {}
        for item in items:
            kind = item.type.value if hasattr(item.type, "value") else item.type
            name = str(kind)
            by_type[name] = by_type.get(name, 0) + 1
        return StatsSnapshot(total=total, average=average, by_type=by_type)

    async def regress(
        self,
        *,
        owner: str,
    ) -> Result[RunSummary, NoLowRatedError]:
        """Promote low-rated items, run the harness, log a tracked run."""
        items = await self._collector.get_feedback(
            owner_id=owner,
            feedback_type=FeedbackType.RATING,
        )
        dataset = build_dataset(items)
        if dataset is None:
            return Err(NoLowRatedError("no low-rated feedback to regress"))

        report_result = await self._harness.run(dataset, self._qa_evaluator())
        if report_result.is_err():
            raise RuntimeError(f"harness failed: {report_result.unwrap_err()}")
        report = report_result.unwrap()

        summary = RunSummary(
            run_id=f"pending-{owner}",
            total_samples=report.total_samples,
            passed_samples=sum(1 for r in report.results if r.score >= PASS_THRESHOLD),
            average_score=round(report.average_score, 4),
            failing_ids=[
                dataset.samples[idx].id
                for idx, r in enumerate(report.results)
                if r.score < PASS_THRESHOLD
            ],
        )
        if self._tracker is not None:
            run = await self._tracker.start(
                ExperimentConfig(
                    name=f"regression-{owner}",
                    seed=_EXPERIMENT_SEED,
                    config={
                        "threshold_rating": 2.0,
                        "pass_threshold": PASS_THRESHOLD,
                    },
                ),
            )
            for sample_score in report.results:
                await self._tracker.log_metric(run.run_id, "score", sample_score.score)
            await self._tracker.finish(run.run_id, RunStatus.COMPLETED)
            logger.info(
                "regression_run_tracked",
                run_id=run.run_id,
                samples=summary.total_samples,
                failing=len(summary.failing_ids),
            )
            summary = RunSummary(
                run_id=run.run_id,
                total_samples=summary.total_samples,
                passed_samples=summary.passed_samples,
                average_score=summary.average_score,
                failing_ids=summary.failing_ids,
            )
        return Ok(summary)

    async def report(self, run_id: str):
        """Post-hoc error analysis over a tracked run."""
        from lexigram.ai.evaluation.analysis import ErrorAnalysis

        return await ErrorAnalysis(self._tracker).report(run_id)

    def _qa_evaluator(self):
        """QA scorer (keyword overlap vs per-case reference bars)."""
        from lexigram.ai.evaluation.evaluators.qa import QAEvaluator

        return QAEvaluator()
