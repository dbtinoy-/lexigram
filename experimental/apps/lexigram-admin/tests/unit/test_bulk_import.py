"""Tests for AdminImportService (CSV and JSON bulk import)."""

from __future__ import annotations

import csv
import io
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram import serialization as json
from lexigram.admin.services.import_ import (
    AdminImportService,
    ImportJob,
    ImportRowError,
)


def _csv_bytes(*rows: dict[str, Any], fieldnames: list[str] | None = None) -> bytes:
    buf = io.StringIO()
    all_keys = fieldnames or list(rows[0].keys())
    writer = csv.DictWriter(buf, fieldnames=all_keys)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode()


class TestAdminImportServiceCSV:
    """CSV parsing and validation."""

    def _make_ds(self) -> MagicMock:
        ds = MagicMock()
        ds.create = AsyncMock()
        return ds

    @pytest.mark.asyncio
    async def test_parse_valid_csv(self) -> None:
        content = _csv_bytes(
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
        )
        svc = AdminImportService(data_source=self._make_ds())
        result = await svc.parse(content, "users.csv")

        assert result.is_ok()
        job = result.unwrap()
        assert job.total_rows == 2
        assert not job.has_errors
        assert job.rows[0]["name"] == "Alice"
        assert job.rows[1]["email"] == "bob@example.com"

    @pytest.mark.asyncio
    async def test_parse_csv_with_column_map(self) -> None:
        content = _csv_bytes(
            {"First Name": "Alice", "E-Mail": "alice@example.com"},
        )
        svc = AdminImportService(data_source=self._make_ds())
        result = await svc.parse(
            content, "users.csv", column_map={"First Name": "name", "E-Mail": "email"}
        )

        assert result.is_ok()
        job = result.unwrap()
        assert job.rows[0]["name"] == "Alice"
        assert job.rows[0]["email"] == "alice@example.com"

    @pytest.mark.asyncio
    async def test_parse_csv_required_field_missing(self) -> None:
        content = _csv_bytes(
            {"name": "Alice", "email": ""},
        )
        svc = AdminImportService(data_source=self._make_ds(), required_fields=["email"])
        result = await svc.parse(content, "users.csv")

        assert result.is_ok()
        job = result.unwrap()
        assert job.has_errors
        assert job.errors[0].field == "email"
        assert job.errors[0].row == 1

    @pytest.mark.asyncio
    async def test_parse_csv_max_rows_exceeded(self) -> None:
        rows = [{"name": f"User{i}", "email": f"u{i}@x.com"} for i in range(5)]
        content = _csv_bytes(*rows)
        svc = AdminImportService(data_source=self._make_ds(), max_rows=3)
        result = await svc.parse(content, "users.csv")

        assert result.is_err()
        assert "limit" in result.unwrap_err().message.lower()

    @pytest.mark.asyncio
    async def test_parse_unsupported_format(self) -> None:
        svc = AdminImportService(data_source=self._make_ds())
        # R26: .xlsx is now supported — use a genuinely unknown format.
        result = await svc.parse(b"data", "data.parquet")

        assert result.is_err()
        assert "Unsupported" in result.unwrap_err().message


class TestAdminImportServiceJSON:
    """JSON parsing."""

    def _make_ds(self) -> MagicMock:
        ds = MagicMock()
        ds.create = AsyncMock()
        return ds

    @pytest.mark.asyncio
    async def test_parse_valid_json(self) -> None:
        data = [{"name": "Alice", "email": "alice@example.com"}]
        content = json.dumps(data)
        svc = AdminImportService(data_source=self._make_ds())
        result = await svc.parse(content, "users.json")

        assert result.is_ok()
        job = result.unwrap()
        assert job.total_rows == 1
        assert job.rows[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_parse_json_invalid_syntax(self) -> None:
        svc = AdminImportService(data_source=self._make_ds())
        result = await svc.parse(b"{not valid json", "users.json")

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_parse_json_not_array(self) -> None:
        content = json.dumps({"key": "value"})
        svc = AdminImportService(data_source=self._make_ds())
        result = await svc.parse(content, "users.json")

        assert result.is_err()
        assert "array" in result.unwrap_err().message.lower()

    @pytest.mark.asyncio
    async def test_parse_json_with_column_map(self) -> None:
        data = [{"first_name": "Alice", "mail": "alice@x.com"}]
        content = json.dumps(data)
        svc = AdminImportService(data_source=self._make_ds())
        result = await svc.parse(
            content, "users.json", column_map={"first_name": "name", "mail": "email"}
        )

        assert result.is_ok()
        assert result.unwrap().rows[0]["name"] == "Alice"


class TestAdminImportServiceCommit:
    """Commit behaviour."""

    def _make_ds(self) -> MagicMock:
        ds = MagicMock()
        ds.create = AsyncMock()
        return ds

    @pytest.mark.asyncio
    async def test_commit_creates_all_valid_rows(self) -> None:
        ds = self._make_ds()
        svc = AdminImportService(data_source=ds)
        job = ImportJob(
            rows=[{"name": "A"}, {"name": "B"}],
            errors=[],
            column_map={"name": "name"},
            source_filename="u.csv",
            total_rows=2,
        )

        result = await svc.commit(job)

        assert result.is_ok()
        outcome = result.unwrap()
        assert outcome.created == 2
        assert outcome.failed == 0
        assert ds.create.await_count == 2

    @pytest.mark.asyncio
    async def test_commit_skips_error_rows(self) -> None:
        ds = self._make_ds()
        svc = AdminImportService(data_source=ds)
        job = ImportJob(
            rows=[{"name": "A"}, {"name": ""}],
            errors=[ImportRowError(row=2, field="name", message="required")],
            column_map={},
            source_filename="u.csv",
            total_rows=2,
        )

        result = await svc.commit(job)

        assert result.is_ok()
        outcome = result.unwrap()
        assert outcome.created == 1
        assert outcome.failed == 1
        assert ds.create.await_count == 1

    @pytest.mark.asyncio
    async def test_commit_handles_create_failure(self) -> None:
        ds = self._make_ds()
        ds.create = AsyncMock(side_effect=ValueError("DB error"))
        svc = AdminImportService(data_source=ds)
        job = ImportJob(
            rows=[{"name": "A"}],
            errors=[],
            column_map={},
            source_filename="u.csv",
            total_rows=1,
        )

        result = await svc.commit(job)

        assert result.is_ok()
        outcome = result.unwrap()
        assert outcome.created == 0
        assert outcome.failed == 1
        assert len(outcome.errors) == 1
        assert "DB error" in outcome.errors[0].message


class TestImportJob:
    """ImportJob helper properties."""

    def test_has_errors_false_when_empty(self) -> None:
        job = ImportJob(
            rows=[], errors=[], column_map={}, source_filename="f.csv", total_rows=0
        )
        assert not job.has_errors

    def test_valid_rows_excludes_error_rows(self) -> None:
        rows = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        errors = [ImportRowError(row=2, field="name", message="required")]
        job = ImportJob(
            rows=rows,
            errors=errors,
            column_map={},
            source_filename="f.csv",
            total_rows=3,
        )
        valid = job.valid_rows
        assert len(valid) == 2
        assert valid[0]["name"] == "A"
        assert valid[1]["name"] == "C"
