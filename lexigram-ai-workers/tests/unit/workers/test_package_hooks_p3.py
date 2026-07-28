"""P3 hook surface import verification for lexigram-ai-workers."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest


def test_workers_hooks_root_module_exists() -> None:
    import lexigram.ai.workers
    from lexigram.ai.workers.hooks import (
        WorkerJobCompletedHook,
        WorkerJobStartedHook,
        WorkerMaintenanceRunHook,
    )

    assert lexigram.ai.workers.WorkerJobStartedHook is WorkerJobStartedHook
    assert lexigram.ai.workers.WorkerJobCompletedHook is WorkerJobCompletedHook
    assert (
        lexigram.ai.workers.WorkerMaintenanceRunHook is WorkerMaintenanceRunHook
    )


def test_workers_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.ai.workers.hooks import (
        WorkerJobCompletedHook,
        WorkerJobStartedHook,
        WorkerMaintenanceRunHook,
    )

    started = WorkerJobStartedHook(job_type="document_ingestion")
    completed = WorkerJobCompletedHook(job_type="document_ingestion")
    maintenance = WorkerMaintenanceRunHook(task_type="cleanup")

    assert is_dataclass(started)
    assert is_dataclass(completed)
    assert is_dataclass(maintenance)
    assert [field.name for field in fields(started)] == ["job_type"]
    assert [field.name for field in fields(completed)] == ["job_type"]
    assert [field.name for field in fields(maintenance)] == ["task_type"]

    with pytest.raises(TypeError):
        WorkerJobStartedHook("document_ingestion")  # type: ignore[misc]

    with pytest.raises(TypeError):
        WorkerJobCompletedHook("document_ingestion")  # type: ignore[misc]

    with pytest.raises(TypeError):
        WorkerMaintenanceRunHook("cleanup")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        started.job_type = "batch_embedding"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        completed.job_type = "batch_embedding"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        maintenance.task_type = "reindex"  # type: ignore[misc]
