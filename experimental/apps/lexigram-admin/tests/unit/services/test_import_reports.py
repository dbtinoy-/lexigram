"""Tests for failed-import report storage in AdminImportService."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.services.import_ import AdminImportService, ImportRowError


class _RejectingDataSource:
    """Data source whose create() always fails (simulates bad rows)."""

    def __init__(self, *, fail_rows: set[int] | None = None) -> None:
        self.fail_rows = fail_rows or {1}
        self.created: list[dict[str, Any]] = []

    async def create(self, row: dict[str, Any]) -> Any:
        row_num = row.get("_row", 0)
        if row_num in self.fail_rows:
            raise ValueError(f"invalid value at row {row_num}")
        self.created.append(row)
        return row


async def _commit(service: AdminImportService, *, rows: list[dict[str, Any]], filename: str = "users.csv") -> Any:
    job = (await service.parse(
        b"name,email\nAlice,a@x.com\nBob,b@x.com",
        filename,
    )).unwrap()
    job.rows = rows
    job.total_rows = len(rows)
    return await service.commit(job)


def _service() -> AdminImportService:
    return AdminImportService(_RejectingDataSource(), required_fields=["name"])


def test_reports_empty_initially() -> None:
    assert _service().reports() == []


@pytest.mark.asyncio
async def test_commit_with_failures_stores_report() -> None:
    service = _service()
    ds = service._data_source
    result = (await _commit(service, rows=[{"_row": 1, "name": "A"}, {"_row": 2, "name": "B"}])).unwrap()

    assert result.failed == 1
    reports = service.reports()
    assert len(reports) == 1
    report = reports[0]
    assert report.source_filename == "users.csv"
    assert report.total_rows == 2
    assert report.failed_rows == 1
    assert any(isinstance(e, ImportRowError) for e in report.failures)
    assert len(ds.created) == 1


@pytest.mark.asyncio
async def test_commit_without_failures_stores_nothing() -> None:
    service = _service()
    ds = service._data_source
    result = (await _commit(service, rows=[{"_row": 2, "name": "B"}])).unwrap()

    assert result.failed == 0
    assert service.reports() == []
    assert len(ds.created) == 1


@pytest.mark.asyncio
async def test_get_report_returns_matching_or_none() -> None:
    service = _service()
    await _commit(service, rows=[{"_row": 1, "name": "A"}])
    report_id = service.reports()[0].id

    assert service.get_report(report_id) is service.reports()[0]
    assert service.get_report("nope") is None


@pytest.mark.asyncio
async def test_delete_report_removes() -> None:
    service = _service()
    await _commit(service, rows=[{"_row": 1, "name": "A"}])
    report_id = service.reports()[0].id

    assert service.delete_report(report_id) is True
    assert service.reports() == []
    assert service.delete_report(report_id) is False


@pytest.mark.asyncio
async def test_report_to_csv_lists_failed_rows() -> None:
    service = _service()
    await _commit(service, rows=[{"_row": 1, "name": "A"}])
    report = service.reports()[0]

    lines = report.to_csv().strip().splitlines()
    assert lines[0] == "row,field,message"
    assert len(lines) == 2
    assert lines[1].startswith("1,__row__,")