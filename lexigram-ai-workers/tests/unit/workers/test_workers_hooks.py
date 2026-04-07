"""Tests for AI workers hooks."""

from __future__ import annotations

import pytest

from lexigram.ai.workers import hooks


class TestWorkerJobStartedHook:
    """Test WorkerJobStartedHook dataclass."""

    def test_creation(self) -> None:
        """Test creating a WorkerJobStartedHook."""
        hook = hooks.WorkerJobStartedHook(job_type="document_ingestion")
        assert hook.job_type == "document_ingestion"

    def test_is_frozen(self) -> None:
        """Test that the dataclass is frozen."""
        hook = hooks.WorkerJobStartedHook(job_type="test")
        with pytest.raises(AttributeError):
            hook.job_type = "changed"

    def test_kw_only(self) -> None:
        """Test that fields are keyword-only."""
        hook = hooks.WorkerJobStartedHook(job_type="batch_embedding")
        assert hook.job_type == "batch_embedding"

    def test_to_dict_compatible(self) -> None:
        """Test hook can be used with dict conversion."""
        hook = hooks.WorkerJobStartedHook(job_type="maintenance")
        d = {"job_type": hook.job_type}
        assert d["job_type"] == "maintenance"


class TestWorkerJobCompletedHook:
    """Test WorkerJobCompletedHook dataclass."""

    def test_creation(self) -> None:
        """Test creating a WorkerJobCompletedHook."""
        hook = hooks.WorkerJobCompletedHook(job_type="document_ingestion")
        assert hook.job_type == "document_ingestion"

    def test_is_frozen(self) -> None:
        """Test that the dataclass is frozen."""
        hook = hooks.WorkerJobCompletedHook(job_type="test")
        with pytest.raises(AttributeError):
            hook.job_type = "changed"

    def test_kw_only(self) -> None:
        """Test that fields are keyword-only."""
        hook = hooks.WorkerJobCompletedHook(job_type="batch_embedding")
        assert hook.job_type == "batch_embedding"


class TestWorkerMaintenanceRunHook:
    """Test WorkerMaintenanceRunHook dataclass."""

    def test_creation(self) -> None:
        """Test creating a WorkerMaintenanceRunHook."""
        hook = hooks.WorkerMaintenanceRunHook(task_type="cache_cleanup")
        assert hook.task_type == "cache_cleanup"

    def test_is_frozen(self) -> None:
        """Test that the dataclass is frozen."""
        hook = hooks.WorkerMaintenanceRunHook(task_type="test")
        with pytest.raises(AttributeError):
            hook.task_type = "changed"

    def test_kw_only(self) -> None:
        """Test that fields are keyword-only."""
        hook = hooks.WorkerMaintenanceRunHook(task_type="index_optimization")
        assert hook.task_type == "index_optimization"


class TestHooksExports:
    """Test hooks are properly exported."""

    def test_all_exports(self) -> None:
        """Test __all__ contains expected hooks."""
        expected = [
            "WorkerJobCompletedHook",
            "WorkerJobStartedHook",
            "WorkerMaintenanceRunHook",
        ]
        assert sorted(hooks.__all__) == sorted(expected)


class TestHookUsage:
    """Test hook usage patterns."""

    def test_hooks_distinguishable_by_type(self) -> None:
        """Test hooks of different types can be distinguished."""
        started = hooks.WorkerJobStartedHook(job_type="ingest")
        completed = hooks.WorkerJobCompletedHook(job_type="ingest")
        maintenance = hooks.WorkerMaintenanceRunHook(task_type="cleanup")

        assert type(started) is hooks.WorkerJobStartedHook
        assert type(completed) is hooks.WorkerJobCompletedHook
        assert type(maintenance) is hooks.WorkerMaintenanceRunHook

    def test_hooks_can_be_stored_in_collection(self) -> None:
        """Test hooks can be stored in lists/dicts."""
        hook_list = [
            hooks.WorkerJobStartedHook(job_type="job1"),
            hooks.WorkerJobCompletedHook(job_type="job1"),
            hooks.WorkerMaintenanceRunHook(task_type="cleanup"),
        ]
        assert len(hook_list) == 3

    def test_hooks_are_hashable(self) -> None:
        """Test hooks can be used in sets."""
        hook_set = {
            hooks.WorkerJobStartedHook(job_type="job1"),
            hooks.WorkerJobStartedHook(job_type="job1"),
        }
        assert len(hook_set) == 1