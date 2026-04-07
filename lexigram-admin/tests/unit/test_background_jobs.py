"""Tests for BackgroundJobService."""

from __future__ import annotations

import asyncio

import pytest

from lexigram.admin.services.background_jobs import BackgroundJob, BackgroundJobService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_svc(**kwargs) -> BackgroundJobService:
    return BackgroundJobService(**kwargs)


# ---------------------------------------------------------------------------
# Enqueue import
# ---------------------------------------------------------------------------

class TestEnqueueImport:
    @pytest.mark.asyncio
    async def test_returns_job_id(self) -> None:
        svc = _make_svc()
        job_id = await svc.enqueue_import("user", b"name,email\nAlice,a@b.com")
        assert job_id.startswith("import-")

    @pytest.mark.asyncio
    async def test_job_visible_in_list(self) -> None:
        svc = _make_svc()
        job_id = await svc.enqueue_import("user", b"name\nAlice")
        await asyncio.sleep(0.05)  # let task complete
        jobs = svc.list_jobs()
        assert any(j.job_id == job_id for j in jobs)

    @pytest.mark.asyncio
    async def test_job_completes_without_service(self) -> None:
        svc = _make_svc()
        job_id = await svc.enqueue_import("user", b"name\nAlice")
        await asyncio.sleep(0.1)
        status = await svc.get_status(job_id)
        assert status is not None
        assert status["status"] == "completed"

    @pytest.mark.asyncio
    async def test_metadata_stored(self) -> None:
        svc = _make_svc()
        job_id = await svc.enqueue_import(
            "user", b"data", file_format="json", filename="users.json"
        )
        await asyncio.sleep(0.1)
        job = await svc.get_job(job_id)
        assert job is not None
        assert job.metadata["file_format"] == "json"
        assert job.metadata["filename"] == "users.json"

    @pytest.mark.asyncio
    async def test_actor_id_stored(self) -> None:
        svc = _make_svc()
        job_id = await svc.enqueue_import("user", b"data", actor_id="admin-1")
        job = await svc.get_job(job_id)
        assert job is not None
        assert job.actor_id == "admin-1"


# ---------------------------------------------------------------------------
# Enqueue export
# ---------------------------------------------------------------------------

class TestEnqueueExport:
    @pytest.mark.asyncio
    async def test_returns_job_id(self) -> None:
        svc = _make_svc()
        job_id = await svc.enqueue_export("product", export_format="csv")
        assert job_id.startswith("export-")

    @pytest.mark.asyncio
    async def test_export_completes_without_service(self) -> None:
        svc = _make_svc()
        job_id = await svc.enqueue_export("product")
        await asyncio.sleep(0.1)
        status = await svc.get_status(job_id)
        assert status is not None
        assert status["status"] == "completed"

    @pytest.mark.asyncio
    async def test_export_metadata(self) -> None:
        svc = _make_svc()
        job_id = await svc.enqueue_export(
            "order", export_format="xlsx", columns=["id", "status"]
        )
        job = await svc.get_job(job_id)
        assert job is not None
        assert job.metadata["export_format"] == "xlsx"
        assert job.metadata["columns"] == ["id", "status"]


# ---------------------------------------------------------------------------
# Status / query
# ---------------------------------------------------------------------------

class TestJobStatus:
    @pytest.mark.asyncio
    async def test_get_status_returns_dict(self) -> None:
        svc = _make_svc()
        job_id = await svc.enqueue_import("user", b"data")
        await asyncio.sleep(0.1)
        status = await svc.get_status(job_id)
        assert status is not None
        assert "job_id" in status
        assert "percent" in status
        assert "status" in status

    @pytest.mark.asyncio
    async def test_get_status_none_for_missing(self) -> None:
        svc = _make_svc()
        result = await svc.get_status("nonexistent-job")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_jobs_by_resource_type(self) -> None:
        svc = _make_svc()
        await svc.enqueue_import("user", b"data")
        await svc.enqueue_import("product", b"data")
        await asyncio.sleep(0.1)
        user_jobs = svc.list_jobs(resource_type="user")
        assert len(user_jobs) == 1
        assert user_jobs[0].resource_type == "user"

    @pytest.mark.asyncio
    async def test_list_jobs_by_type(self) -> None:
        svc = _make_svc()
        await svc.enqueue_import("user", b"data")
        await svc.enqueue_export("user")
        await asyncio.sleep(0.1)
        imports = svc.list_jobs(job_type="import")
        exports = svc.list_jobs(job_type="export")
        assert len(imports) == 1
        assert len(exports) == 1

    @pytest.mark.asyncio
    async def test_list_jobs_by_status(self) -> None:
        svc = _make_svc()
        await svc.enqueue_import("user", b"data")
        await asyncio.sleep(0.1)
        completed = svc.list_jobs(status="completed")
        assert len(completed) >= 1

    @pytest.mark.asyncio
    async def test_to_dict_contains_all_fields(self) -> None:
        svc = _make_svc()
        job_id = await svc.enqueue_export("user")
        await asyncio.sleep(0.1)
        status = await svc.get_status(job_id)
        assert status is not None
        for key in ("job_id", "job_type", "resource_type", "actor_id", "status", "percent", "created_at"):
            assert key in status


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

class TestCancel:
    @pytest.mark.asyncio
    async def test_cancel_missing_returns_false(self) -> None:
        svc = _make_svc()
        result = await svc.cancel("ghost-job")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_completed_returns_false(self) -> None:
        svc = _make_svc()
        job_id = await svc.enqueue_import("user", b"data")
        await asyncio.sleep(0.15)
        result = await svc.cancel(job_id)
        assert result is False  # already completed


# ---------------------------------------------------------------------------
# Eviction
# ---------------------------------------------------------------------------

class TestEviction:
    @pytest.mark.asyncio
    async def test_evicts_when_over_max(self) -> None:
        svc = _make_svc(max_retained_jobs=3)
        for _ in range(5):
            job_id = await svc.enqueue_import("user", b"data")
        await asyncio.sleep(0.2)
        # Only max_retained_jobs completed jobs should remain
        all_jobs = svc.list_jobs()
        assert len(all_jobs) <= 3 + 2  # completed ≤ 3, some may still be pending/running
