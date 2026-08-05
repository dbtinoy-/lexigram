"""Tests for the ablation runner."""

from __future__ import annotations

from lexigram.ai.evaluation.ablation import AblationRunner
from lexigram.ai.evaluation.checkpoints import FileCheckpointStore
from lexigram.ai.evaluation.exceptions import AblationError


class TestAblationRunner:
    async def test_deltas_are_after_minus_before(self) -> None:
        assert AblationRunner.deltas({"a": 1.0, "b": 5.0}, {"a": 3.0}) == {
            "a": 2.0,
            "b": -5.0,
        }

    async def test_run_returns_digest_stable_result(self, tmp_path) -> None:
        store = FileCheckpointStore(root=tmp_path)
        await store.save("probe-42-abc", "baseline", {"tokens": 100.0, "cost": 0.001})
        await store.save(
            "probe-42-abc", "no-thinking", {"tokens": 55.0, "cost": 0.0005}
        )
        runner = AblationRunner(store)
        result = await runner.run("probe-42-abc", "thinking", "baseline", "no-thinking")
        assert result.is_ok()
        ablated = result.unwrap()
        assert ablated.knob == "thinking"
        assert ablated.deltas["tokens"] == -45.0
        assert ablated.digest.startswith("ablation-")
        again = await runner.run("probe-42-abc", "thinking", "baseline", "no-thinking")
        assert again.unwrap().digest == ablated.digest

    async def test_run_missing_checkpoint_returns_err(self, tmp_path) -> None:
        store = FileCheckpointStore(root=tmp_path)
        runner = AblationRunner(store)
        result = await runner.run("probe-42-abc", "thinking", "baseline", "no-thinking")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), AblationError)

    async def test_compare_uses_separate_run_ids(self, tmp_path) -> None:
        store = FileCheckpointStore(root=tmp_path)
        await store.save("control-42-a1b2", "baseline", {"tokens": 100.0, "cost": 0.001})
        await store.save(
            "ablated-42-9f8e", "ablated-thinking", {"tokens": 55.0, "cost": 0.0005}
        )
        runner = AblationRunner(store)
        result = await runner.compare(
            "thinking",
            "control-42-a1b2",
            "baseline",
            "ablated-42-9f8e",
            "ablated-thinking",
        )
        assert result.is_ok()
        record = result.unwrap()
        assert record.knob == "thinking"
        assert record.baseline_slug == "baseline"
        assert record.ablated_slug == "ablated-thinking"
        assert record.deltas["tokens"] == -45.0
        assert record.digest.startswith("ablation-")
        again = await runner.compare(
            "thinking",
            "control-42-a1b2",
            "baseline",
            "ablated-42-9f8e",
            "ablated-thinking",
        )
        assert again.unwrap().digest == record.digest

    async def test_compare_missing_ablated_checkpoint_returns_err(self, tmp_path) -> None:
        store = FileCheckpointStore(root=tmp_path)
        await store.save("control-42-a1b2", "baseline", {"tokens": 100.0})
        runner = AblationRunner(store)
        result = await runner.compare(
            "thinking",
            "control-42-a1b2",
            "baseline",
            "ablated-42-9f8e",
            "ablated-thinking",
        )
        assert result.is_err()
        assert isinstance(result.unwrap_err(), AblationError)
