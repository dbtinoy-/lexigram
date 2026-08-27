# Feedback-Loop Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `demos/feedback-loop/` — an offline CLI demo closing the loop from user ratings to enforced regression suites (`lexigram-ai-feedback` capture → `lexigram-ai-evaluation` datasets/harness/tracker/error-analysis). No UI: sequential pipeline with printed reports, event-driven-orders anatomy.

**Architecture:** Flat package `src/feedback_loop/` — root `@module FeedbackLoopModule` imports `FeedbackModule.configure(async_processing=False)` + `EvaluationModule.configure(seed=7, experiment_dir=…)`; `bot.py` canned registry; `regression.py` promotes ≤2-rated items into a duck-typed `ScoredSample` dataset scored by `QAEvaluator` through the real `EvaluationHarness`; `LocalTracker` persists seeded runs under `.runs/`; argparse CLI drives ask/rate/stats/regress/report/demo.

**Tech Stack:** Python 3.11+, `lexigram-ai-feedback`, `lexigram-ai-evaluation`, httpx-free plain pytest, ruff.

**Spec:** `.superpowers/specs/2026-08-22-feedback-loop-design.md` — read it first.

## Global Constraints

- Offline only; byte-stable stdout — **run ids are stable** (`make_run_id(name, seed, config)`, tracking.py:37) but never print wall-clock or absolute paths.
- **Degraded-mode feedback is intended**: no `DatabaseProviderProtocol` bound ⇒ collector memory-buffer mode (provider.py:86-92). All captures flow through `FeedbackCollector`; stats computed from its query results (never from `store.aggregate`, which needs a DB store).
- **Sample contract (verified):** runner duck-types
  `sample.output if hasattr(sample, "output") else ""` (runner.py:49);
  local frozen `ScoredSample` mirrors `EvaluationSample` plus `output`.
- **Scoring choice (design resolution):** one evaluator must handle
  per-case references ⇒ `QAEvaluator` (keyword overlap vs reference)
  through the single `EvaluationHarness`; `CriteriaEvaluator` is unused
  here because its fixed criteria list cannot vary per sample.
- Absolute imports; Google docstrings; full annotations; files <500 LOC.
- Commits: emoji conventional format, pathspec commits only; `git status --short` first.
- Scoped runs: `uv run pytest demos/feedback-loop/tests -q`.

---

### Task 1: Scaffold + bot registry

**Files:**
- Create: `demos/feedback-loop/conftest.py`
- Create: `src/feedback_loop/__init__.py`, `tests/__init__.py`
- Create: `src/feedback_loop/bot.py`
- Create: `src/feedback_loop/errors.py`
- Test: `tests/test_bot.py`

**Interfaces:**
- Produces: `BOT: dict[str, str]` (4 keys, two deliberately poor); `TRACE_IDS: dict[str, str]` (sorted-key order → t1..t4); `POOR_KEYS: set[str]`; `UnknownQuestionError/UnknownTraceError/InvalidRatingError(ValueError)`.

- [ ] **Step 1: conftest + skeletons**

```python
"""Pytest bootstrap for the feedback-loop demo (single shim — no UI)."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
```

Docstring-only `__init__.py`: `src/feedback_loop/__init__.py`
(`"""Ratings-to-regression loop demo."""`), empty `tests/__init__.py`.

- [ ] **Step 2: Write the failing test**

`tests/test_bot.py`:
```python
"""Bot registry surface tests."""

from __future__ import annotations

import pytest

from feedback_loop.bot import BOT, POOR_KEYS, TRACE_IDS
from feedback_loop.errors import InvalidRatingError


class TestBot:
    def test_four_questions_two_poor(self) -> None:
        assert len(BOT) == 4
        assert POOR_KEYS == {"refund-policy", "shipping-time"}

    def test_trace_ids_stable_and_unique(self) -> None:
        assert sorted(TRACE_IDS.values()) == ["t1", "t2", "t3", "t4"]
        assert set(TRACE_IDS) == set(BOT)

    def test_poor_answers_miss_reference_bars(self) -> None:
        assert "tracking" not in BOT["shipping-time"].lower()
        assert "24 month" not in BOT["refund-policy"].lower()


class TestErrors:
    def test_error_hierarchy(self) -> None:
        for exc in (InvalidRatingError("x"),):
            assert isinstance(exc, ValueError)
```

- [ ] **Step 3:** Run → FAIL (`feedback_loop.bot` missing).

- [ ] **Step 4: Implement**

`src/feedback_loop/bot.py`:
```python
"""Canned Q→A registry with fixed trace ids (two deliberately poor answers)."""

from __future__ import annotations

BOT: dict[str, str] = {
    "refund-policy": "Contact support and maybe you get money back sometime.",
    "shipping-time": "It arrives when it arrives.",
    "track-order": "Use the tracking id in your shipment email to follow your parcel.",
    "warranty": "Every product includes a 24 month limited warranty covering manufacturing defects.",
}

TRACE_IDS: dict[str, str] = {
    key: f"t{index + 1}" for index, key in enumerate(sorted(BOT))
}

POOR_KEYS: set[str] = {"refund-policy", "shipping-time"}
```

`src/feedback_loop/errors.py`:
```python
"""Typed CLI-boundary errors for the feedback-loop demo."""

from __future__ import annotations


class UnknownQuestionError(ValueError):
    """Raised when an unknown question key is asked."""


class UnknownTraceError(ValueError):
    """Raised when rating an unissued trace id."""


class InvalidRatingError(ValueError):
    """Raised when a rating is outside the closed interval [1, 5]."""
```

- [ ] **Step 5:** Run → PASS (4). **Step 6:** Commit
  `✨ feat(demos): scaffold feedback-loop bot registry`

---

### Task 2: Regression builder

**Files:**
- Create: `src/feedback_loop/regression.py`
- Test: `tests/test_regression.py`

**Interfaces:**
- Consumes: `FeedbackItem`, `FeedbackType` from `lexigram.contracts.ai.feedback`; `EvaluationDataset` from `lexigram.contracts.ai.evaluation`.
- Produces: `ScoredSample(id, input, output, reference, metadata)` frozen dataclass (duck-typed harness contract, runner.py:49); `THRESHOLD_RATING = 2.0`; `REFERENCE_BARS: dict[str, str]`; `build_dataset(items: list[FeedbackItem]) -> EvaluationDataset | None` (None when nothing ≤ threshold).

- [ ] **Step 1: Write the failing test**

```python
"""Regression dataset builder tests."""

from __future__ import annotations

from lexigram.contracts.ai.feedback import FeedbackItem, FeedbackType

from feedback_loop.bot import BOT, TRACE_IDS
from feedback_loop.regression import REFERENCE_BARS, ScoredSample, build_dataset


def _item(key: str, rating: float, owner: str = "alice") -> FeedbackItem:
    return FeedbackItem(
        feedback_type=FeedbackType.RATING,
        value=rating,
        owner_id=owner,
        context={
            "trace_id": TRACE_IDS[key],
            "question_key": key,
            "answer": BOT[key],
            "question": key.replace("-", " "),
        },
    )


class TestBuildDataset:
    def test_low_ratings_promoted(self) -> None:
        dataset = build_dataset([_item("refund-policy", 1), _item("track-order", 5)])

        assert dataset is not None
        assert dataset.name == "regression"
        assert [s.id for s in dataset.samples] == ["t1"]

    def test_threshold_is_inclusive_at_two(self) -> None:
        dataset = build_dataset([_item("shipping-time", 2)])
        assert dataset is not None and len(dataset.samples) == 1

    def test_output_field_present_for_harness(self) -> None:
        dataset = build_dataset([_item("warranty", 1)])
        sample = dataset.samples[0]
        assert sample.output == BOT["warranty"]          # duck-typed attr
        assert sample.reference == REFERENCE_BARS["warranty"]

    def test_owner_filtering(self) -> None:
        items = [_item("refund-policy", 1), _item("shipping-time", 1, owner="bob")]
        mixed = build_dataset([items[0], items[1]])
        assert mixed is not None and len(mixed.samples) == 2  # caller filters owner

    def test_empty_when_all_good(self) -> None:
        assert build_dataset([_item("track-order", 5), _item("warranty", 4)]) is None

    def test_scored_sample_shape(self) -> None:
        sample = ScoredSample(id="x", input="q", output="a", reference="r")
        assert hasattr(sample, "output") and sample.metadata == {}
```

- [ ] **Step 2:** Run → FAIL.

- [ ] **Step 3: Implement**

`src/feedback_loop/regression.py`:
```python
"""Promote low-rated exchanges into a regression dataset."""

from __future__ import annotations

from dataclasses import dataclass, field

from lexigram.contracts.ai.evaluation import EvaluationDataset
from lexigram.contracts.ai.feedback import FeedbackItem

THRESHOLD_RATING = 2.0

REFERENCE_BARS: dict[str, str] = {
    "refund-policy": "money back",
    "shipping-time": "business days",
    "track-order": "tracking id",
    "warranty": "24 month",
}


@dataclass(frozen=True)
class ScoredSample:
    """Harness duck-types on attribute presence (harness/runner.py:49)."""

    id: str
    input: str
    output: str
    reference: str
    metadata: dict = field(default_factory=dict)


def build_dataset(items: list[FeedbackItem]) -> EvaluationDataset | None:
    """Collect rated-below-threshold items into samples; None if none."""
    low = [
        item
        for item in items
        if float(item.value) <= THRESHOLD_RATING
        and {"trace_id", "question_key", "answer"} <= set(item.context)
    ]
    if not low:
        return None
    samples = [
        ScoredSample(
            id=str(item.context["trace_id"]),
            input=str(item.context.get("question", item.context["question_key"])),
            output=str(item.context["answer"]),
            reference=REFERENCE_BARS[str(item.context["question_key"])],
            metadata={},
        )
        for item in low
    ]
    return EvaluationDataset(name="regression", samples=list(samples), metadata={})
```

Note: owner filtering happens at the caller (`get_feedback(owner_id=…)`);
`build_dataset` stays pure over whatever list it receives — the
owner-test above documents that contract.

- [ ] **Step 4:** Run → PASS (6). **Step 5:** Commit
  `✨ feat(demos): add feedback-loop regression builder`

---

### Task 3: Service + provider + module (boot path)

**Files:**
- Create: `src/feedback_loop/loop_service.py`
- Create: `di/__init__.py`, `di/provider.py`, `module.py`
- Modify: `conftest.py` (append boot fixture — resolves services directly, no HTTP)
- Test: `tests/test_loop_service.py`

**Interfaces:**
- Consumes: `FeedbackCollector` (concrete singleton), `EvaluationHarness` (concrete binding), `ExperimentTrackerProtocol`, `QAEvaluator` via named `EvaluatorProtocol` binding `"qa"` (pin resolution mechanism below), `RunStatus`, `ExperimentConfig` from contracts.
- Produces: `Answer(trace_id, question_key, question, answer)`; `StatsSnapshot(total, average, by_type)`; `RunSummary(run_id, total_samples, passed_samples, average_score, failing_ids)`; `LoopService(collector, harness, qa_evaluator, tracker)` with async `ask(key, owner)`, `rate(trace_id, rating, owner, comment=None)`, `stats(owner)`, `regress(owner)`, `report(run_id)`; `LoopProvider`; `FeedbackLoopModule.configure(experiment_dir=".runs")` exporting `[LoopService]`. `PASS_THRESHOLD = 0.6` module constant.

- [ ] **Step 1: Extend conftest**

```python
import pytest


@pytest.fixture
async def service(tmp_path):
    """Boot the module graph with tmp experiment dir; yield LoopService."""
    from lexigram.app import Application

    from feedback_loop.loop_service import LoopService
    from feedback_loop.module import FeedbackLoopModule

    async with Application.boot(
        name="feedback-loop-test",
        modules=[FeedbackLoopModule.configure(experiment_dir=str(tmp_path))],
    ) as application:
        yield await application.container.resolve(LoopService)
```

- [ ] **Step 2: Write the failing tests**

```python
"""Boot-level service tests (ratings → stats → regression → report)."""

from __future__ import annotations

import pytest

from feedback_loop.bot import BOT, POOR_KEYS, TRACE_IDS
from feedback_loop.errors import (
    InvalidRatingError,
    UnknownQuestionError,
    UnknownTraceError,
)


async def test_ask_issues_known_trace(service) -> None:
    answer = await service.ask("track-order", owner="alice")

    assert answer.trace_id == TRACE_IDS["track-order"]
    assert answer.answer == BOT["track-order"]


async def test_ask_unknown_question_raises(service) -> None:
    with pytest.raises(UnknownQuestionError):
        await service.ask("nope", owner="alice")


async def test_rate_validates_trace_and_bounds(service) -> None:
    await service.ask("track-order", owner="alice")

    item_id = await service.rate(TRACE_IDS["track-order"], 5, owner="alice")
    assert item_id

    with pytest.raises(UnknownTraceError):
        await service.rate("t9", 5, owner="alice")
    with pytest.raises(InvalidRatingError):
        await service.rate(TRACE_IDS["track-order"], 0, owner="alice")
    with pytest.raises(InvalidRatingError):
        await service.rate(TRACE_IDS["track-order"], 6, owner="alice")


async def test_stats_aggregates_from_memory_mode(service) -> None:
    trace = (await service.ask("warranty", owner="alice")).trace_id
    await service.rate(trace, 2, owner="alice")

    snapshot = await service.stats("alice")
    assert snapshot.total == 1
    assert snapshot.average == 2.0
    assert snapshot.by_type == {"rating": 1}


async def test_regress_promotes_only_low_ratings(service) -> None:
    for key in sorted(BOT):
        await service.ask(key, owner="alice")
    await service.rate(TRACE_IDS["refund-policy"], 1, owner="alice")
    await service.rate(TRACE_IDS["shipping-time"], 2, owner="alice")
    await service.rate(TRACE_IDS["track-order"], 5, owner="alice")
    await service.rate(TRACE_IDS["warranty"], 4, owner="alice")

    summary = await service.regress("alice")

    assert set(summary.failing_ids) == {TRACE_IDS[k] for k in POOR_KEYS}
    assert summary.total_samples == 2
    assert summary.run_id  # seeded id string


async def test_regress_without_low_ratings_raises_valueerror(service) -> None:
    await service.ask("track-order", owner="alice")
    await service.rate(TRACE_IDS["track-order"], 5, owner="alice")

    with pytest.raises(ValueError, match="no low-rated"):
        await service.regress("alice")


async def test_report_matches_run(service) -> None:
    for key in sorted(BOT):
        await service.ask(key, owner="alice")
    await service.rate(TRACE_IDS["refund-policy"], 1, owner="alice")
    await service.rate(TRACE_IDS["shipping-time"], 2, owner="alice")

    summary = await service.regress("alice")
    analysis = await service.report(summary.run_id)

    assert analysis.total_records == summary.total_samples * 1  # one metric/sample
    assert analysis.error_count == 0
```

(`total_records` counts metrics logged; adjust assertion to the actual
`AnalysisReport` semantics once confirmed against analysis.py:24.)

- [ ] **Step 3:** Run → FAIL (`cannot import name 'FeedbackLoopModule'`).

- [ ] **Step 4: Implement service, provider, module**

`loop_service.py`:
```python
"""Orchestrates bot answers, rating capture, regression runs."""

from __future__ import annotations

from dataclasses import dataclass, field

from lexigram.contracts.ai.experiment import ExperimentConfig, RunStatus
from lexigram.contracts.ai.feedback import FeedbackType

from feedback_loop.bot import BOT, TRACE_IDS
from feedback_loop.errors import (
    InvalidRatingError,
    UnknownQuestionError,
    UnknownTraceError,
)
from feedback_loop.regression import build_dataset

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
    """Ask → rate → stats → regress → report, all in-memory + .runs files."""

    def __init__(self, collector, harness, qa_evaluator, tracker) -> None:
        self._collector = collector
        self._harness = harness
        self._qa = qa_evaluator
        self._tracker = tracker

    async def ask(self, key: str, *, owner: str) -> Answer:
        """Answer a known question; issue its stable trace id."""
        if key not in BOT:
            raise UnknownQuestionError(f"unknown question: {key!r}")
        answer = Answer(
            trace_id=TRACE_IDS[key],
            question_key=key,
            question=key.replace("-", " "),
            answer=BOT[key],
        )
        return answer

    async def rate(
        self,
        trace_id: str,
        rating: float,
        *,
        owner: str,
        comment: str | None = None,
    ) -> str:
        """Capture a rating for a previously issued trace id."""
        keys_by_trace = {v: k for k, v in TRACE_IDS.items()}
        if trace_id not in keys_by_trace:
            raise UnknownTraceError(f"unknown trace: {trace_id!r}")
        value = float(rating)
        if not 1.0 <= value <= 5.0:
            raise InvalidRatingError(f"rating out of range: {rating!r}")

        key = keys_by_trace[trace_id]
        return await self._collector.collect_rating(
            value,
            owner_id=owner,
            context={
                "trace_id": trace_id,
                "question_key": key,
                "question": key.replace("-", " "),
                "answer": BOT[key],
                "comment": comment or "",
            },
            metadata={"source": "cli"},
        )

    async def stats(self, *, owner: str) -> StatsSnapshot:
        """Aggregate this owner's captured ratings (memory mode)."""
        items = self._collector.get_feedback(owner_id=owner)
        total = len(items)
        values = [float(i.value) for i in items]
        average = round(sum(values) / total, 4) if total else None
        by_type: dict[str, int] = {}
        for item in items:
            name = str(item.type.value if hasattr(item.type, "value") else item.type)
            by_type[name] = by_type.get(name, 0) + 1
        return StatsSnapshot(total=total, average=average, by_type=by_type)

    async def regress(self, *, owner: str) -> RunSummary:
        """Promote low-rated items, run the harness, log a tracked run."""
        items = self._collector.get_feedback(owner_id=owner)
        dataset = build_dataset(items)
        if dataset is None:
            raise ValueError("no low-rated feedback to regress")

        report_result = await self._harness.run(dataset, self._qa)
        if report_result.is_err():
            raise RuntimeError(f"harness failed: {report_result.unwrap_err()}")
        report = report_result.unwrap()

        run = self._tracker.start(
            ExperimentConfig(
                name=f"regression-{owner}",
                seed=_EXPERIMENT_SEED,
                config={"threshold_rating": 2.0, "pass_threshold": PASS_THRESHOLD},
            ),
        )
        for sample_score in report.results:
            self._tracker.log_metric(run.run_id, "score", sample_score.score)
        self._tracker.finish(run.run_id, RunStatus.COMPLETED)

        failing = [
            dataset.samples[idx].id
            for idx, r in enumerate(report.results)
            if r.score < PASS_THRESHOLD
        ]
        passed = sum(1 for r in report.results if r.score >= PASS_THRESHOLD)
        return RunSummary(
            run_id=run.run_id,
            total_samples=report.total_samples,
            passed_samples=passed,
            average_score=round(report.average_score, 4),
            failing_ids=failing,
        )

    async def report(self, run_id: str):
        """Post-hoc error analysis over a tracked run."""
        from lexigram.ai.evaluation.analysis import ErrorAnalysis

        return ErrorAnalysis(self._tracker).report(run_id)
```

Pins at implementation: `collect_rating` kwarg names (collector.py:50),
`get_feedback` filter kwargs (:209), `tracker.start/log_metric/finish`
signatures (contracts experiment :168/:178/:242), `AnalysisReport`
fields (contracts :138) and `ErrorAnalysis.report` metric-name
expectation (`"score"` — constants.py:47-52 confirms metric names).
Named evaluator resolution: if `resolve(EvaluatorProtocol)` returns the
last-registered singleton instead of honoring a name, resolve
`QAEvaluator` concretely from `lexigram.ai.evaluation.qa` — prefer the
named binding only if the container's Named-DI supports it (core di
notes: `Annotated[T, Named(name)]`).

`di/provider.py`:
```python
"""DI wiring for the feedback-loop demo (internal)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

from feedback_loop.loop_service import LoopService


class LoopProvider(Provider):
    """Assembles LoopService from booted collaborators."""

    name = "loop"

    def __init__(self) -> None:
        super().__init__()
        self._service: LoopService | None = None

    def _get_service(self) -> LoopService:
        if self._service is None:
            raise RuntimeError("LoopProvider has not been booted yet")
        return self._service

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(LoopService, factory=self._get_service)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        from lexigram.ai.evaluation.harness.runner import EvaluationHarness

        collector = await container.resolve(FeedbackCollectorToken())
        tracker = await container.resolve(ExperimentTrackerToken())
        qa = await resolve_qa(container)

        self._service = LoopService(
            collector=collector,
            harness=EvaluationHarness(pass_threshold=PASS_THRESHOLD_SENTINEL()),
            qa_evaluator=qa,
            tracker=tracker,
        )


# --- write-time cleanup block: replace the three sentinels above with
# hoisted imports; final boot() body reads: ---
#
#     from lexigram.contracts.ai.experiment import ExperimentTrackerProtocol
#     from lexigram.contracts.ai.evaluation import EvaluatorProtocol
#     from feedback_loop.constants import PASS_THRESHOLD   # or inline 0.6
#
#     collector = await container.resolve(FeedbackCollector)
#     tracker = await container.resolve(ExperimentTrackerProtocol)
#     try:
#         qa = await container.resolve(
#             Annotated[EvaluatorProtocol, Named("qa")])
#     except Exception:
#         from lexigram.ai.evaluation.qa import QAEvaluator
#         qa = QAEvaluator()
#
# Import FeedbackCollector from lexigram.ai.feedback.services.collector;
# Named from the core DI namespace (verify exact path: di/resolution or
# contracts/core/di). PASS_THRESHOLD lives as module constant 0.6.
```

The sentinel block is an intentional trap: final file contains ONLY the
cleaned form described in the trailing comment — no sentinels ship.

`module.py`:
```python
"""Root module for the feedback-loop demo."""

from __future__ import annotations

from lexigram.ai.evaluation.config import EvaluationConfig
from lexigram.ai.evaluation.module import EvaluationModule
from lexigram.ai.feedback.config import FeedbackConfig
from lexigram.ai.feedback.module import FeedbackModule
from lexigram.di.module import DynamicModule, Module, module

from feedback_loop.chat_free_zone import nothing  # DELETE ME before save
from feedback_loop.di.provider import LoopProvider
from feedback_loop.loop_service import LoopService


@module()
class FeedbackLoopModule(Module):
    """Ratings-to-regression loop with tracked experiments."""

    @classmethod
    def configure(cls, experiment_dir: str = ".runs") -> DynamicModule:
        return DynamicModule(
            module=cls,
            imports=[
                FeedbackModule.configure(
                    FeedbackConfig(async_processing=False),
                ),
                EvaluationModule.configure(EvaluationConfig(
                    default_threshold=0.6,
                    default_seed=7,
                    experiment_dir=experiment_dir,
                )),
            ],
            providers=[LoopProvider],
            exports=[LoopService],
        )


__all__ = ["FeedbackLoopModule"]
```

DELETE the `chat_free_zone` import line before saving (trap marker —
final file has no such import).

- [ ] **Step 5:** Full suite run:

```bash
uv run pytest demos/feedback-loop/tests -q
```
Expected: ALL PASS (10 prior + 7 service). If degraded-mode drops data
(`submit_feedback` no-store path — provider pokes `service._store`
directly), our flows already bypass `FeedbackService` entirely (collector
only), matching spec §10's contingency.

- [ ] **Step 6:** Commit
  `✨ feat(demos): wire feedback-loop service with tracked regressions`

---

### Task 4: CLI entry point

**Files:**
- Create: `src/feedback_loop/main.py`, `src/feedback_loop/__main__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: subcommands `ask KEY --owner O`, `rate T R [--comment C] --owner O`, `stats --owner O`, `regress --owner O`, `report RUN_ID`, `demo`; `build_parser()`, `async run(args) -> int`, `main() -> int` (exit 0 ok / 1 typed errors / 130 SIGINT).

- [ ] **Step 1: Write the failing test**

```python
"""CLI routing and smoke tests (in-process)."""

from __future__ import annotations

import pytest

from feedback_loop.main import build_parser, run


class TestParser:
    def test_routes(self) -> None:
        p = build_parser()
        assert p.parse_args(["ask", "track-order", "--owner", "a"]).command == "ask"
        rate = p.parse_args(
            ["rate", "t1", "2", "--owner", "a", "--comment", "bad"])
        assert rate.command == "rate" and rate.rating == 2.0
        assert p.parse_args(["stats", "--owner", "a"]).command == "stats"
        assert p.parse_args(["regress", "--owner", "a"]).command == "regress"
        assert p.parse_args(["report", "rid"]).command == "report"
        assert p.parse_args(["demo"]).command == "demo"

    def test_requires_command(self) -> None:
        with pytest.raises(SystemExit):
            build_parser().parse_args([])


class TestRun:
    @pytest.mark.asyncio
    async def test_demo_full_loop(self, capsys, tmp_path) -> None:
        args = build_parser().parse_args(
            ["demo", "--experiment-dir", str(tmp_path)],
        )
        code = await run(args)
        out = capsys.readouterr().out

        assert code == 0
        assert "failing:" in out
        assert "t1" in out and "t2" in out          # poor traces fail
        assert "t3" not in out.split("failing:")[1] # good ones don't

    @pytest.mark.asyncio
    async def test_typed_error_exits_one(self, capsys, tmp_path) -> None:
        args = build_parser().parse_args(
            ["ask", "nope", "--owner", "a",
             "--experiment-dir", str(tmp_path)])
        code = await run(args)

        assert code == 1
        assert "unknown question" in capsys.readouterr().out.lower()
```

- [ ] **Step 2:** Run → FAIL (`feedback_loop.main` missing).

- [ ] **Step 3: Implement**

`main.py`:
```python
"""Entry points for the feedback-loop demo.

Run::

    PYTHONPATH=demos/feedback-loop/src uv run python -m feedback_loop demo
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from lexigram.app import Application

from feedback_loop.bot import BOT, TRACE_IDS
from feedback_loop.errors import (
    InvalidRatingError,
    UnknownQuestionError,
    UnknownTraceError,
)
from feedback_loop.loop_service import LoopService
from feedback_loop.module import FeedbackLoopModule

_TYPED_ERRORS = (UnknownQuestionError, UnknownTraceError, InvalidRatingError)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="feedback_loop")
    parser.add_argument(
        "--experiment-dir",
        default=".runs",
        help="Tracker/checkpoint root (default .runs)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ask = sub.add_parser("ask", help="ask a canned question")
    p_ask.add_argument("key", choices=sorted(BOT))
    p_ask.add_argument("--owner", required=True)

    p_rate = sub.add_parser("rate", help="rate a trace 1..5")
    p_rate.add_argument("trace_id", choices=sorted(TRACE_IDS.values()))
    p_rate.add_argument("rating", type=float)
    p_rate.add_argument("--comment", default=None)
    p_rate.add_argument("--owner", required=True)

    p_stats = sub.add_parser("stats", help="aggregate my ratings")
    p_stats.add_argument("--owner", required=True)

    p_reg = sub.add_parser("regress", help="run regression from low ratings")
    p_reg.add_argument("--owner", required=True)

    p_rep = sub.add_parser("report", help="error analysis for a run")
    p_rep.add_argument("run_id")

    sub.add_parser("demo", help="full loop: asks, ratings, regress, report")
    return parser


def _add_experiment_dir(args: argparse.Namespace) -> None:
    """Thread the global flag into configure() for every subcommand."""
    args.experiment_dir = getattr(args, "experiment_dir", ".runs")


async def _boot_service(args: argparse.Namespace) -> tuple:
    _add_experiment_dir(args)
    app_ctx = Application.boot(
        name="feedback-loop",
        modules=[FeedbackLoopModule.configure(experiment_dir=args.experiment_dir)],
    )
    app = await app_ctx.__aenter__()
    service = await app.container.resolve(LoopService)
    return app_ctx, service


async def run(args: argparse.Namespace) -> int:
    try:
        app_ctx, service = await _boot_service(args)
    except _TYPED_ERRORS as exc:
        print(f"error: {exc}")
        return 1

    try:
        if args.command == "demo":
            return await _demo(service)
        return await _single(service, args)
    except _TYPED_ERRORS as exc:
        print(f"error: {exc}")
        return 1
    finally:
        await app_ctx.__aexit__(None, None, None)


async def _single(service: LoopService, args: argparse.Namespace) -> int:
    if args.command == "ask":
        answer = await service.ask(args.key, owner=args.owner)
        print(f"[{answer.trace_id}] {answer.answer}")
        print(f"rate it:  feedback_loop rate {answer.trace_id} <1-5> "
              f"--owner {args.owner}")
    elif args.command == "rate":
        item_id = await service.rate(
            args.trace_id, args.rating,
            owner=args.owner, comment=args.comment,
        )
        print(f"captured rating {args.rating:g} ({item_id})")
    elif args.command == "stats":
        snap = await service.stats(owner=args.owner)
        print(f"total={snap.total} average={snap.average} by_type={snap.by_type}")
    elif args.command == "regress":
        summary = await service.regress(owner=args.owner)
        print(f"run={summary.run_id}")
        print(f"samples={summary.total_samples} "
              f"passed={summary.passed_samples} "
              f"average={summary.average_score}")
        print(f"failing: {', '.join(summary.failing_ids) or '(none)'}")
    elif args.command == "report":
        analysis = await service.report(args.run_id)
        print(f"records={analysis.total_records} errors={analysis.error_count}")
        print(f"score mean={analysis.score_mean} min={analysis.score_min} "
              f"max={analysis.score_max}")
    return 0


async def _demo(service: LoopService) -> int:
    print("== ask ==")
    for key in sorted(BOT):
        answer = await service.ask(key, owner="alice")
        print(f"[{answer.trace_id}] {key}: {answer.answer}")

    print("\n== rate ==")
    ratings = {k: 1.0 if k in {"refund-policy"} else
               2.0 if k in {"shipping-time"} else
               5.0 if k == "track-order" else 4.0
               for k in sorted(BOT)}
    for key, value in ratings.items():
        item_id = await service.rate(
            TRACE_IDS[key], value, owner="alice", comment=f"auto:{value}",
        )
        print(f"{TRACE_IDS[key]} <- {value:g} ({item_id})")

    print("\n== stats ==")
    snap = await service.stats(owner="alice")
    print(f"total={snap.total} average={snap.average} by_type={snap.by_type}")

    print("\n== regress ==")
    summary = await service.regress(owner="alice")
    print(f"run={summary.run_id}")
    print(f"samples={summary.total_samples} passed={summary.passed_samples} "
          f"average={summary.average_score}")
    print(f"failing: {', '.join(summary.failing_ids)}")

    print("\n== report ==")
    analysis = await service.report(summary.run_id)
    print(f"records={analysis.total_records} errors={analysis.error_count}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
```

`__main__.py`:
```python
"""Enable ``python -m feedback_loop``."""

from __future__ import annotations

import sys

from feedback_loop.main import main

sys.exit(main())
```

Pin at implementation: `AnalysisReport` attribute names
(`score_mean/score_min/score_max/total_records/error_count`) against
contracts/ai/experiment.py:138-156 — align prints/tests to actuals.
Manual smoke after suite:

```bash
PYTHONPATH=demos/feedback-loop/src uv run python -m feedback_loop demo
PYTHONPATH=demos/feedback-loop/src uv run python -m feedback_loop demo   # same run id? no—new run each boot; ids differ per config only. Assert stdout identical modulo run_id line.
```
Expected: identical output except the `run=` line (fresh run each boot);
second invocation exits 0.

- [ ] **Step 4:** Full suite green. **Step 5:** Commit
  `✨ feat(demos): add feedback-loop CLI entry point`

---

### Task 5: README + Makefile gating + .gitignore + gates

**Files:**
- Create: `demos/feedback-loop/README.md`
- Modify: `Makefile:114-115`, `demos/README.md`, `.gitignore` (+1 line)

- [ ] **Step 1:** Makefile append `demos/feedback-loop/tests` /
  `demos/feedback-loop` (diff-first). `.gitignore`: append
  `demos/feedback-loop/.runs/`.
- [ ] **Step 2:** `demos/README.md` section:

```markdown
### 🔁 [feedback-loop](feedback-loop/) — ratings become regression suites

Close the quality loop without a model call:

- ⭐ **Rate canned answers** — 1–5 stars captured per trace id
- 📉 **Low ratings promote** — ≤2-rated exchanges become eval samples
- 🎯 **Real harness runs** — QA-scored, tracked under seeded run ids
- 🔎 **Error analysis** — mean/min/max scores and top failing cases printed
- 💻 **CLI-first** — six subcommands; `demo` plays the whole loop
```

Demo-local README expands commands/layout/gotchas (state lives per
process; `demo` is the full story).

- [ ] **Step 3:** Gates:

```bash
uv run ruff check demos/feedback-loop && uv run ruff format --check demos/feedback-loop
make test-demos && make verify-demos
find demos/feedback-loop -name "*.py" | xargs wc -l | sort -n   # all <500
git status --short                                              # + check .runs ignored
```

- [ ] **Step 4:** Commit

```bash
git add demos/README.md demos/feedback-loop/README.md Makefile .gitignore && git commit demos/README.md demos/feedback-loop/README.md Makefile .gitignore -m "📝 docs(demos): document feedback-loop and gate make targets"
```

---

## Self-Review Notes

- Spec coverage: CLI shape (orders-style) ✓(T4); bot registry w/ 2 poor answers + stable trace ids ✓(T1); ≤2 promotion + ScoredSample duck-typed output ✓(T2); in-memory degraded mode asserted implicitly (no DB anywhere) + collector-only data path per spec §10 contingency ✓(T3); seeded tracker runs + error analysis ✓(T3/T4); byte-stability scoped to stdout-modulo-run-id, documented ✓(T4 smoke); Makefile/.gitignore/README ✓(T5).
- Type consistency: `Answer/StatsSnapshot/RunSummary` identical across service/CLI/tests; error trio shared by service+main.
- Intentional traps flagged (delete-before-save): provider sentinel helpers, module stray import.
- Design resolution recorded: QAEvaluator-through-harness chosen because CriteriaEvaluator's fixed criteria list cannot vary per case (spec §3 alternative resolved).
- Known risks pinned: collect_rating/get_feedback kwargs (collector.py:50/:209); tracker method signatures (contracts experiment :168/:178/:242); AnalysisReport fields (:138); Named-DI resolution fallback to concrete QAEvaluator.
