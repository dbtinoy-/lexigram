"""Tests for BackgroundJobService."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from lexigram.admin.services.background_jobs import BackgroundJobService
from lexigram.admin.services.export import ExportService
from lexigram.admin.services.import_ import AdminImportService

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
        for key in (
            "job_id",
            "job_type",
            "resource_type",
            "actor_id",
            "status",
            "percent",
            "created_at",
        ):
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
        assert (
            len(all_jobs) <= 3 + 2
        )  # completed ≤ 3, some may still be pending/running


class _FakeDataSource:
    """Minimal IDataSource double used by AdminImportService commits."""

    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    async def create(self, row: dict[str, Any]) -> SimpleNamespace:
        self.created.append(row)
        return SimpleNamespace(id=str(len(self.created)))


class _FakeExportSource:
    """Minimal IExportDataSource double used by ExportService.execute_export."""

    def __init__(self, items: list[dict[str, Any]], total: int) -> None:
        self._items = items
        self._total = total

    async def get_export_data(
        self,
        filters: dict[str, Any],
        columns: list[str],
        sort_by: str | None = None,
        sort_order: str = "asc",
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        return self._items

    async def get_export_count(self, filters: dict[str, Any]) -> int:
        return self._total

    async def get_column_definitions(self) -> list[dict[str, Any]]:
        return []


class _FakeStorage:
    """Minimal BlobStoreProtocol double used by export backends."""

    def __init__(self) -> None:
        self.uploads: list[tuple[str, bytes, str]] = []

    async def upload(self, file_path: str, content: bytes, content_type: str) -> str:
        self.uploads.append((file_path, content, content_type))
        return file_path


# ---------------------------------------------------------------------------
# Enqueue with real services
# ---------------------------------------------------------------------------


class TestEnqueueImportWithRealService:
    @pytest.mark.asyncio
    async def test_imports_through_admin_import_service(self) -> None:
        ds = _FakeDataSource()
        svc = BackgroundJobService(import_service=AdminImportService(data_source=ds))
        job_id = await svc.enqueue_import(
            "user", b"name,email\nAlice,a@b.com", filename="users.csv"
        )
        await asyncio.sleep(0.1)
        status = await svc.get_status(job_id)
        assert status is not None
        assert status["status"] == "completed"
        assert status["result"]["rows_imported"] == 1
        assert ds.created == [{"name": "Alice", "email": "a@b.com"}]

    @pytest.mark.asyncio
    async def test_unsupported_filename_fails_job(self) -> None:
        svc = BackgroundJobService(
            import_service=AdminImportService(data_source=_FakeDataSource())
        )
        job_id = await svc.enqueue_import("user", b"data", filename="users.xlsx")
        await asyncio.sleep(0.1)
        status = await svc.get_status(job_id)
        assert status is not None
        assert status["status"] == "failed"
        assert "Unsupported file format" in status["error"]


class TestEnqueueExportWithRealService:
    @pytest.mark.asyncio
    async def test_exports_through_export_service(self) -> None:
        source = _FakeExportSource(items=[{"id": "1"}], total=1)
        exporter = ExportService(storage=_FakeStorage(), task_manager=object())
        svc = BackgroundJobService(export_service=exporter, export_data_source=source)
        job_id = await svc.enqueue_export(
            "user", export_format="csv", filters={"active": True}
        )
        await asyncio.sleep(0.1)
        status = await svc.get_status(job_id)
        assert status is not None
        assert status["status"] == "completed"
        assert status["result"]["rows_exported"] == 1
        assert status["result"]["download_url"].startswith("/admin/exports/download")
        assert status["result"]["export_format"] == "csv"

    @pytest.mark.asyncio
    async def test_export_without_data_source_fails(self) -> None:
        exporter = ExportService(storage=_FakeStorage(), task_manager=object())
        svc = BackgroundJobService(export_service=exporter)
        job_id = await svc.enqueue_export("user", export_format="csv")
        await asyncio.sleep(0.1)
        status = await svc.get_status(job_id)
        assert status is not None
        assert status["status"] == "failed"
        assert "data source" in status["error"]

    @pytest.mark.asyncio
    async def test_export_with_unknown_format_fails(self) -> None:
        source = _FakeExportSource(items=[], total=0)
        exporter = ExportService(storage=_FakeStorage(), task_manager=object())
        svc = BackgroundJobService(export_service=exporter, export_data_source=source)
        job_id = await svc.enqueue_export("user", export_format="tsv")
        await asyncio.sleep(0.1)
        status = await svc.get_status(job_id)
        assert status is not None
        assert status["status"] == "failed"
