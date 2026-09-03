"""R19 import-pipeline regression tests (B15–B19).

See docs/09-01-2026/15-import-pipeline-correctness.md. Each test here
fails on the pre-R19 code.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.services.import_.service import (
    AdminImportService,
    _parse_csv,
    _parse_json,
    _parse_jsonl,
)


class RecordingDataSource:
    """Data source stub that records created rows."""

    def __init__(self, fail_on: Any = None, exc: Exception | None = None) -> None:
        self.created: list[dict[str, Any]] = []
        self._fail_on = fail_on
        self._exc = exc or Exception("driver blew up")

    async def create(self, row: dict[str, Any]) -> None:
        if self._fail_on is not None and row == self._fail_on:
            raise self._exc
        self.created.append(row)


class TestB15RaggedCsv:
    def test_short_row_does_not_crash(self) -> None:
        # DictReader fills the missing 'sku' cell with None (restval);
        # the old code called .strip() on it and raised AttributeError.
        rows, _map, errors = _parse_csv(b"name,sku\nWidget")
        assert rows == [{"name": "Widget", "sku": None}]
        assert errors == []

    def test_normal_rows_still_stripped(self) -> None:
        rows, _map, _errors = _parse_csv(b"name,sku\n  Widget  ,  W-1 \n")
        assert rows == [{"name": "Widget", "sku": "W-1"}]


class TestB15bJsonl:
    def test_jsonl_objects_parse_per_line(self) -> None:
        rows, _map, errors = _parse_jsonl(b'{"a": 1}\n\n{"a": 2}\n')
        assert rows == [{"a": 1}, {"a": 2}]
        assert errors == []

    def test_jsonl_bad_line_is_row_scoped_and_aligned(self) -> None:
        rows, _map, errors = _parse_jsonl(b'{"a": 1}\nnot json\n{"a": 3}\n')
        assert len(rows) == 3
        assert rows[0] == {"a": 1}
        assert rows[1] == {}  # placeholder keeps positions aligned
        assert rows[2] == {"a": 3}
        assert [e.row for e in errors] == [2]

    @pytest.mark.asyncio
    async def test_service_routes_jsonl_extension(self) -> None:
        ds = RecordingDataSource()
        svc = AdminImportService(data_source=ds)
        job = (await svc.parse(b'{"a": 1}\n{"a": 2}\n', "rows.jsonl")).unwrap()
        assert job.total_rows == 2
        assert not job.has_errors


class TestB16JsonRowAlignment:
    def test_non_dict_items_keep_positions_aligned(self) -> None:
        rows, _map, errors = _parse_json(b'[1, {"a": 2}, {"a": 3}]')
        assert len(rows) == 3
        assert rows[0] == {}
        assert rows[1] == {"a": 2}
        assert rows[2] == {"a": 3}
        assert [e.row for e in errors] == [1]

    @pytest.mark.asyncio
    async def test_commit_imports_the_valid_neighbours(self) -> None:
        # Pre-fix: the compacted rows list made commit() skip the valid
        # {"a": 2} row and import only {"a": 3} — silent data loss.
        ds = RecordingDataSource()
        svc = AdminImportService(data_source=ds)
        job = (await svc.parse(b'[1, {"a": 2}, {"a": 3}]', "x.json")).unwrap()
        result = (await svc.commit(job)).unwrap()
        assert ds.created == [{"a": 2}, {"a": 3}]
        assert result.created == 2
        assert result.failed == 1  # the non-dict placeholder

    @pytest.mark.asyncio
    async def test_placeholder_rows_skip_required_field_noise(self) -> None:
        svc = AdminImportService(
            data_source=RecordingDataSource(), required_fields=["a"]
        )
        job = (await svc.parse(b'[1, {"a": 2}]', "x.json")).unwrap()
        # Exactly one error (the parse error) — no cascading
        # "'a' is required" on the placeholder row.
        assert [(e.row, e.field) for e in job.errors] == [(1, "__row__")]


class TestB17CommitBatchIsolation:
    @pytest.mark.asyncio
    async def test_arbitrary_exception_does_not_abort_batch(self) -> None:
        # DB drivers raise types outside the old (ValueError, TypeError,
        # KeyError, RuntimeError) tuple; the documented contract is that a
        # bad row never aborts the rest of the batch.
        class DriverError(Exception):
            pass

        ds = RecordingDataSource(fail_on={"a": 2}, exc=DriverError("boom"))
        svc = AdminImportService(data_source=ds)
        job = (await svc.parse(b'[{"a": 1}, {"a": 2}, {"a": 3}]', "x.json")).unwrap()
        result = (await svc.commit(job)).unwrap()
        assert ds.created == [{"a": 1}, {"a": 3}]
        assert result.created == 2
        assert result.failed == 1
        assert [e.row for e in result.errors] == [2]
