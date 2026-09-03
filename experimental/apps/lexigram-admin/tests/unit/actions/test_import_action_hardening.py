"""R19 import-action regression tests (B18, B19).

See docs/09-01-2026/15-import-pipeline-correctness.md.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.actions.standard.imports import (
    ImportAction,
    _safe_filename_stem,
)
from lexigram.admin.actions.types import ActionContext


class RecordingDataSource:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    async def create(self, row: dict[str, Any]) -> None:
        if row.get("boom"):
            raise ValueError("bad row")
        self.created.append(row)


def _ctx(ds: Any, content: bytes, filename: str) -> ActionContext:
    return ActionContext(
        data_source=ds,
        metadata={"file_content": content, "filename": filename},
    )


class TestB19FallbackServiceReports:
    @pytest.mark.asyncio
    async def test_report_downloadable_after_lazy_service_creation(self) -> None:
        # Pre-fix: the fallback AdminImportService was discarded after
        # execute(), so the advertised report_id could never be
        # downloaded (report_csv read the still-None _import_service).
        action = ImportAction()
        ds = RecordingDataSource()
        content = b'[{"a": 1}, {"a": 2, "boom": true}]'
        result = await action.execute(None, _ctx(ds, content, "rows.json"))
        payload = result.unwrap()
        assert payload["failed"] == 1
        report_id = payload["report_id"]
        csv_content = action.report_csv(report_id)
        assert csv_content is not None
        assert "bad row" in csv_content
        assert action.report_filename(report_id) == "rows-import-errors.csv"


class TestB18FilenameSanitization:
    def test_safe_stem_passthrough(self) -> None:
        assert _safe_filename_stem("users.csv") == "users"
        assert _safe_filename_stem("Q3_report-final.json") == "Q3_report-final"

    def test_hostile_characters_are_neutralized(self) -> None:
        hostile = 'evil".csv\r\nSet-Cookie: pwn=1;.csv'
        stem = _safe_filename_stem(hostile)
        assert '"' not in stem
        assert "\r" not in stem and "\n" not in stem
        assert ";" not in stem and ":" not in stem

    def test_path_separators_removed(self) -> None:
        stem = _safe_filename_stem("../../etc/passwd.csv")
        assert "/" not in stem and ".." not in stem

    def test_empty_or_dotfile_falls_back(self) -> None:
        assert _safe_filename_stem("....") == "import"
        assert _safe_filename_stem("") == "import"

    @pytest.mark.asyncio
    async def test_payload_report_filename_is_sanitized(self) -> None:
        action = ImportAction()
        ds = RecordingDataSource()
        content = b'[{"a": 1, "boom": true}]'
        hostile_name = 'evil"\r\nX-Injected: 1;.json'
        result = await action.execute(None, _ctx(ds, content, hostile_name))
        payload = result.unwrap()
        assert payload["failed"] == 1
        fname = payload["report_filename"]
        assert fname.endswith("-import-errors.csv")
        assert all(ch not in fname for ch in ('"', "\r", "\n", ":", ";"))
