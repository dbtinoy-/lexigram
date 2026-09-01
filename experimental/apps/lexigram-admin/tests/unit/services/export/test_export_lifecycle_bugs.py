"""R20 export-service lifecycle regression tests (B20–B22).

See docs/09-01-2026/16-export-lifecycle-correctness.md. Each bug test
fails on the pre-R20 code.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

import pytest

from lexigram.admin.services.export.scheduler import (
    ExportFormat,
    ExportSchedule,
    ExportStatus,
)
from lexigram.admin.services.export.service import ExportService


class FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, bytes]] = []

    async def upload(self, path: str, content: bytes, **kwargs: Any) -> None:
        self.uploads.append((path, content))


class FakeTaskManager:
    def create_background_task(self, coro: Any) -> Any:
        import asyncio

        return asyncio.get_event_loop().create_task(coro)


class ListDataSource:
    """Data source over a fixed row list with optional mid-flight hook."""

    def __init__(
        self,
        rows: list[dict[str, Any]],
        on_offset: dict[int, Any] | None = None,
    ) -> None:
        self._rows = rows
        self._on_offset = on_offset or {}

    async def get_export_count(self, filters: dict[str, Any]) -> int:
        return len(self._rows)

    async def get_export_data(
        self,
        filters: dict[str, Any],
        columns: list[str],
        limit: int | None = None,
        offset: int | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        offset = offset or 0
        hook = self._on_offset.get(offset)
        if hook is not None:
            hook()
        return self._rows[offset : offset + (limit or len(self._rows))]

    async def get_column_definitions(self) -> list[Any]:
        return []


def _service() -> tuple[ExportService, FakeStorage]:
    storage = FakeStorage()
    return (
        ExportService(storage=storage, task_manager=FakeTaskManager()),
        storage,
    )


class TestB20ScheduleExport:
    @pytest.mark.asyncio
    async def test_schedule_export_does_not_raise(self) -> None:
        # Pre-fix: create_job() was called with `format=` (parameter is
        # `file_format`) -> TypeError on every call, hidden by a
        # `# type: ignore[call-arg]`.
        svc, _ = _service()
        job_id = await svc.schedule_export(
            {"resource_name": "products", "format": ExportFormat.CSV},
            ExportSchedule.DAILY,
            datetime.now(UTC),
        )
        job = svc.get_job(job_id)
        assert job is not None
        assert job.format is ExportFormat.CSV
        assert job.schedule_type is ExportSchedule.DAILY
        assert job.metadata["schedule_type"] == "daily"

    @pytest.mark.asyncio
    async def test_schedule_export_coerces_string_format(self) -> None:
        svc, _ = _service()
        job_id = await svc.schedule_export(
            {"resource_name": "products", "format": "csv"},
            ExportSchedule.HOURLY,
            datetime.now(UTC),
        )
        job = svc.get_job(job_id)
        assert job is not None and job.format is ExportFormat.CSV


class TestB21CancellationObserved:
    @pytest.mark.asyncio
    async def test_manager_cancel_mid_flight_stops_export(self) -> None:
        # Pre-fix: the chunk loop ignored job.status — the export ran to
        # completion and overwrote CANCELLED with COMPLETED.
        svc, storage = _service()
        rows = [{"a": i} for i in range(3000)]
        job_id = svc.create_job("products", ExportFormat.JSON)
        ds = ListDataSource(
            rows, on_offset={1000: lambda: svc.cancel_job(job_id)}
        )
        result = await svc.execute_export(job_id, ds)
        job = svc.get_job(job_id)
        assert job is not None
        assert job.status is ExportStatus.CANCELLED
        assert result.is_err()
        assert storage.uploads == []  # no file for a cancelled job

    @pytest.mark.asyncio
    async def test_pending_job_without_task_is_cancellable(self) -> None:
        # Pre-fix (B21b): cancel_job returned False when no background
        # task existed, so queued jobs could never be cancelled.
        svc, _ = _service()
        job_id = svc.create_job("products", ExportFormat.CSV)
        assert svc.cancel_job(job_id) is True
        job = svc.get_job(job_id)
        assert job is not None and job.status is ExportStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_completed_job_cancel_still_returns_false(self) -> None:
        svc, _ = _service()
        job_id = svc.create_job("products", ExportFormat.JSON)
        result = await svc.execute_export(job_id, ListDataSource([{"a": 1}]))
        assert result.is_ok()
        assert svc.cancel_job(job_id) is False
        job = svc.get_job(job_id)
        assert job is not None and job.status is ExportStatus.COMPLETED


class TestB22RealStreaming:
    @pytest.mark.asyncio
    async def test_csv_stream_is_real_csv(self) -> None:
        svc, _ = _service()
        ds = ListDataSource([{"name": "Widget", "sku": "W-1"}, {"name": "Gadget", "sku": "G-2"}])
        chunks = [c async for c in svc.stream_export(ds, ExportFormat.CSV, batch_size=1)]
        text = b"".join(chunks).decode("utf-8")
        assert b"encoded batch chunk" not in b"".join(chunks)
        lines = [line for line in text.splitlines() if line]
        assert lines[0] == "name,sku"
        assert lines[1:] == ["Widget,W-1", "Gadget,G-2"]

    @pytest.mark.asyncio
    async def test_csv_stream_sanitizes_formula_injection(self) -> None:
        svc, _ = _service()
        ds = ListDataSource([{"name": "=cmd|calc"}])
        chunks = [c async for c in svc.stream_export(ds, ExportFormat.CSV)]
        text = b"".join(chunks).decode("utf-8")
        assert "'=cmd|calc" in text

    @pytest.mark.asyncio
    async def test_csv_stream_respects_explicit_columns(self) -> None:
        svc, _ = _service()
        ds = ListDataSource([{"name": "Widget", "sku": "W-1", "secret": "x"}])
        chunks = [
            c
            async for c in svc.stream_export(
                ds, ExportFormat.CSV, columns=["sku", "name"]
            )
        ]
        text = b"".join(chunks).decode("utf-8")
        lines = [line for line in text.splitlines() if line]
        assert lines[0] == "sku,name"
        assert "secret" not in text and lines[1] == "W-1,Widget"

    @pytest.mark.asyncio
    async def test_json_stream_is_valid_json_array(self) -> None:
        svc, _ = _service()
        rows = [{"a": 1}, {"a": 2}, {"a": 3}]
        ds = ListDataSource(rows)
        chunks = [
            c async for c in svc.stream_export(ds, ExportFormat.JSON, batch_size=2)
        ]
        parsed = json.loads(b"".join(chunks))
        assert parsed == rows

    @pytest.mark.asyncio
    async def test_json_stream_empty_dataset_is_empty_array(self) -> None:
        svc, _ = _service()
        chunks = [
            c async for c in svc.stream_export(ListDataSource([]), ExportFormat.JSON)
        ]
        assert json.loads(b"".join(chunks)) == []

    @pytest.mark.asyncio
    async def test_non_streamable_formats_raise(self) -> None:
        svc, _ = _service()
        with pytest.raises(ValueError, match="Streaming is not supported"):
            async for _ in svc.stream_export(ListDataSource([]), ExportFormat.EXCEL):
                pass
