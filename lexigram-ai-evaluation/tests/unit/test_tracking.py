"""Tests for the experiment tracking module."""

from __future__ import annotations

import pytest

from lexigram.ai.evaluation.exceptions import TrackingError
from lexigram.ai.evaluation.tracking import LocalTracker, make_run_id
from lexigram.contracts.ai.experiment import (
    ExperimentConfig,
    RunStatus,
)


class TestMakeRunId:
    def test_identical_config_produces_identical_id(self) -> None:
        config: dict[str, object] = {"model": "gpt-4o", "max_tokens": 128}
        assert make_run_id("probe", 42, config) == make_run_id("probe", 42, config)

    def test_seed_changes_id(self) -> None:
        config: dict[str, object] = {"model": "gpt-4o"}
        assert make_run_id("probe", 42, config) != make_run_id("probe", 43, config)

    def test_key_order_is_insensitive(self) -> None:
        first = make_run_id("probe", 42, {"a": 1, "b": 2})
        second = make_run_id("probe", 42, {"b": 2, "a": 1})
        assert first == second


class TestLocalTracker:
    @pytest.fixture
    def tracker(self, tmp_path) -> LocalTracker:
        return LocalTracker(root=tmp_path)

    async def test_start_creates_seed_stable_run(self, tracker: LocalTracker) -> None:
        config = ExperimentConfig(name="probe", seed=42, config={"model": "gpt-4o"})
        run = await tracker.start(config)
        assert run.run_id.startswith("probe-42-")
        assert run.status == RunStatus.RUNNING
        resumed = await tracker.start(
            ExperimentConfig(name="probe", seed=42, config={"model": "gpt-4o"})
        )
        assert resumed.run_id == run.run_id

    async def test_different_seed_creates_distinct_run(
        self, tracker: LocalTracker
    ) -> None:
        first = await tracker.start(
            ExperimentConfig(name="probe", seed=42, config={"model": "gpt-4o"})
        )
        second = await tracker.start(
            ExperimentConfig(name="probe", seed=43, config={"model": "gpt-4o"})
        )
        assert first.run_id != second.run_id

    async def test_log_metric_and_snapshot(
        self,
        tracker: LocalTracker,
    ) -> None:
        run = await tracker.start(ExperimentConfig(name="probe", seed=42, config={}))
        await tracker.log_metric(run.run_id, "tokens", 100.0, step=0)
        await tracker.log_metric(run.run_id, "tokens", 150.0, step=1)
        await tracker.log_metric(run.run_id, "score", 0.9, step=1)
        snapshot = await tracker.snapshot(run.run_id)
        assert snapshot["metrics"]["tokens"] == 150.0
        assert snapshot["metrics"]["score"] == 0.9

    async def test_log_error_and_snapshot_counts(
        self,
        tracker: LocalTracker,
    ) -> None:
        run = await tracker.start(ExperimentConfig(name="probe", seed=42, config={}))
        await tracker.log_error(run.run_id, "LLM_RATE_LIMITED", "503", step=0)
        await tracker.log_error(run.run_id, "LLM_RATE_LIMITED", "429", step=1)
        await tracker.log_error(run.run_id, "TIMEOUT", "slow", step=1)
        snapshot = await tracker.snapshot(run.run_id)
        assert snapshot["error_kinds"] == {"LLM_RATE_LIMITED": 2, "TIMEOUT": 1}

    async def test_resume_and_finish(self, tracker: LocalTracker) -> None:
        run = await tracker.start(ExperimentConfig(name="probe", seed=42, config={}))
        await tracker.finish(run.run_id, status=RunStatus.COMPLETED)
        resumed = await tracker.resume(run.run_id)
        assert resumed is not None
        assert resumed.status == RunStatus.COMPLETED
        assert resumed.finished_at is not None

    async def test_resume_unknown_returns_none(self, tracker: LocalTracker) -> None:
        assert await tracker.resume("nope-1-abcdef12") is None

    async def test_snapshot_unknown_raises(self, tracker: LocalTracker) -> None:
        with pytest.raises(TrackingError):
            await tracker.snapshot("nope-1-abcdef12")
