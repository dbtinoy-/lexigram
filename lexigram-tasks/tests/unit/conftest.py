"""Unit-test fixtures for lexigram-tasks compute pool tests (no real spawns)."""

from __future__ import annotations

from typing import Any

import pytest

from compute_fakes import (
    ExecutorHolder,
    FakeExecutor,
    FakeMultiprocessing,
    noop_start_monitoring,
)

import lexigram.tasks.concurrency.compute as compute_mod


@pytest.fixture
def fake_executor(monkeypatch: pytest.MonkeyPatch) -> ExecutorHolder:
    """Patch compute module: fake executor, cpu_count=4, no psutil, no monitor."""
    holder = ExecutorHolder()

    def factory(**kwargs: Any) -> FakeExecutor:
        holder.executor = FakeExecutor()
        return holder.executor

    monkeypatch.setattr(compute_mod, "ProcessPoolExecutor", factory)
    monkeypatch.setattr(compute_mod, "multiprocessing", FakeMultiprocessing())
    monkeypatch.setattr(compute_mod, "HAS_PSUTIL", False)
    monkeypatch.setattr(compute_mod, "psutil", None)
    monkeypatch.setattr(
        compute_mod.ComputePool, "_start_monitoring", noop_start_monitoring
    )
    return holder