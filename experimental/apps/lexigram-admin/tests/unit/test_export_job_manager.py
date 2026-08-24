"""Tests for ExportJobManager — extracted collaborator from ExportService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lexigram.admin.services.export.job_manager import ExportJobManager
from lexigram.admin.services.export.scheduler import (
    ExportFormat,
    ExportStatus,
)


@pytest.fixture
def manager() -> ExportJobManager:
    return ExportJobManager()


class TestCreateJob:
    def test_create_job_returns_id(self, manager: ExportJobManager) -> None:
        job_id = manager.create_job(
            resource_name="users",
            file_format=ExportFormat.CSV,
        )
        assert isinstance(job_id, str)
        assert len(job_id) > 0

    def test_create_job_stores_job(self, manager: ExportJobManager) -> None:
        job_id = manager.create_job(
            resource_name="users",
            file_format=ExportFormat.JSON,
        )
        job = manager.get_job(job_id)
        assert job is not None
        assert job.resource_name == "users"
        assert job.format == ExportFormat.JSON

    def test_create_job_with_filters(self, manager: ExportJobManager) -> None:
        job_id = manager.create_job(
            resource_name="orders",
            file_format=ExportFormat.CSV,
            filters={"status": "active"},
            columns=["id", "name"],
        )
        job = manager.get_job(job_id)
        assert job is not None
        assert job.filters == {"status": "active"}
        assert job.columns == ["id", "name"]

    def test_create_job_defaults(self, manager: ExportJobManager) -> None:
        job_id = manager.create_job(
            resource_name="items",
            file_format=ExportFormat.EXCEL,
        )
        job = manager.get_job(job_id)
        assert job is not None
        assert job.filters == {}
        assert job.columns == []
        assert job.status == ExportStatus.PENDING


class TestGetJob:
    def test_get_existing_job(self, manager: ExportJobManager) -> None:
        job_id = manager.create_job(
            resource_name="users",
            file_format=ExportFormat.CSV,
        )
        job = manager.get_job(job_id)
        assert job is not None
        assert job.job_id == job_id

    def test_get_nonexistent_job_returns_none(self, manager: ExportJobManager) -> None:
        assert manager.get_job("nonexistent") is None


class TestListJobs:
    def test_list_jobs_empty(self, manager: ExportJobManager) -> None:
        assert manager.list_jobs() == []

    def test_list_jobs_returns_all(self, manager: ExportJobManager) -> None:
        manager.create_job(resource_name="a", file_format=ExportFormat.CSV)
        manager.create_job(resource_name="b", file_format=ExportFormat.JSON)
        jobs = manager.list_jobs()
        assert len(jobs) == 2

    def test_list_jobs_filter_by_status(self, manager: ExportJobManager) -> None:
        job_id = manager.create_job(resource_name="a", file_format=ExportFormat.CSV)
        job = manager.get_job(job_id)
        job.status = ExportStatus.COMPLETED
        manager.create_job(resource_name="b", file_format=ExportFormat.JSON)
        completed = manager.list_jobs(status=ExportStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].resource_name == "a"

    def test_list_jobs_limit(self, manager: ExportJobManager) -> None:
        for i in range(5):
            manager.create_job(resource_name=f"r{i}", file_format=ExportFormat.CSV)
        assert len(manager.list_jobs(limit=3)) == 3


class TestCancelJob:
    def test_cancel_nonexistent_returns_false(self, manager: ExportJobManager) -> None:
        assert manager.cancel_job("nonexistent") is False

    def test_cancel_completed_job_returns_false(
        self, manager: ExportJobManager
    ) -> None:
        job_id = manager.create_job(resource_name="a", file_format=ExportFormat.CSV)
        job = manager.get_job(job_id)
        job.status = ExportStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        assert manager.cancel_job(job_id) is False


class TestCleanupCompletedJobs:
    def test_cleanup_removes_old_jobs(self, manager: ExportJobManager) -> None:
        job_id = manager.create_job(resource_name="a", file_format=ExportFormat.CSV)
        job = manager.get_job(job_id)
        job.status = ExportStatus.COMPLETED
        job.completed_at = datetime.now(UTC) - timedelta(days=60)
        removed = manager.cleanup_completed_jobs(max_age_days=30)
        assert removed == 1
        assert manager.get_job(job_id) is None

    def test_cleanup_keeps_recent_jobs(self, manager: ExportJobManager) -> None:
        job_id = manager.create_job(resource_name="a", file_format=ExportFormat.CSV)
        job = manager.get_job(job_id)
        job.status = ExportStatus.COMPLETED
        job.completed_at = datetime.now(UTC) - timedelta(days=5)
        removed = manager.cleanup_completed_jobs(max_age_days=30)
        assert removed == 0
        assert manager.get_job(job_id) is not None
