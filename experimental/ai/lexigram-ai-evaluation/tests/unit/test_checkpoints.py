"""Tests for the file checkpoint store."""

from __future__ import annotations

import pytest

from lexigram.ai.evaluation.checkpoints import FileCheckpointStore
from lexigram.ai.evaluation.exceptions import CheckpointError


class TestFileCheckpointStore:
    @pytest.fixture
    def store(self, tmp_path) -> FileCheckpointStore:
        return FileCheckpointStore(root=tmp_path)

    async def test_save_and_load_roundtrip(self, store: FileCheckpointStore) -> None:
        saved = await store.save("run-42", "baseline", {"tokens": 100.0, "score": 0.8})
        assert saved.digest
        loaded = await store.load("run-42", "baseline")
        assert loaded is not None
        assert loaded.payload == {"tokens": 100.0, "score": 0.8}
        assert loaded.digest == saved.digest

    async def test_load_missing_returns_none(self, store: FileCheckpointStore) -> None:
        assert await store.load("run-42", "missing") is None

    async def test_tampered_payload_is_rejected(
        self, store: FileCheckpointStore
    ) -> None:
        path = store._root / "runs" / "run-42" / "checkpoints" / "baseline.json"
        await store.save("run-42", "baseline", {"tokens": 100.0})
        path.write_text(path.read_text().replace("100.0", "999.0"))
        assert await store.load("run-42", "baseline") is None

    async def test_list_returns_creation_order(
        self, store: FileCheckpointStore
    ) -> None:
        await store.save("run-42", "b", {"x": 1.0})
        await store.save("run-42", "a", {"x": 2.0})
        checkpoints = await store.list("run-42")
        assert [c.slug for c in checkpoints] == ["a", "b"]

    async def test_list_missing_run_is_empty(self, store: FileCheckpointStore) -> None:
        assert await store.list("nope") == []

    async def test_corrupt_file_raises(self, store: FileCheckpointStore) -> None:
        path = store._root / "runs" / "run-42" / "checkpoints" / "c.json"
        path.parent.mkdir(parents=True)
        path.write_text("not json")
        with pytest.raises(CheckpointError):
            await store.load("run-42", "c")
