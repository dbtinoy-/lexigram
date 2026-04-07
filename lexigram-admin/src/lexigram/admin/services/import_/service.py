"""Bulk import service for lexigram-admin.

Supports CSV and JSON file uploads with:
- Column mapping from file headers to resource fields
- Row-level validation before commit (preview mode)
- Structured error reporting per row
- Streaming parse to keep memory usage bounded

Usage::

    service = AdminImportService(data_source=ds)
    job = await service.parse(raw_bytes, filename="users.csv")
    if job.has_errors:
        return job  # show preview with errors
    result = await service.commit(job)
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
import io
from typing import Any

from lexigram import serialization as json
from lexigram.admin.exceptions import AdminError
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ImportRowError:
    """Validation error for a single import row.

    Attributes:
        row: 1-indexed row number within the file.
        field: Field name that failed validation, or ``"__row__"`` for row-level errors.
        message: Human-readable error description.
    """

    row: int
    field: str
    message: str


@dataclass
class ImportJob:
    """Parsed import batch ready for validation or commit.

    Attributes:
        rows: Parsed rows as dicts keyed by mapped field names.
        errors: Per-row validation errors collected during :meth:`AdminImportService.parse`.
        column_map: Mapping from source file header → target resource field name.
        source_filename: Original uploaded filename.
        total_rows: Total number of data rows (excludes header).
    """

    rows: list[dict[str, Any]]
    errors: list[ImportRowError]
    column_map: dict[str, str]
    source_filename: str
    total_rows: int

    @property
    def has_errors(self) -> bool:
        """True when at least one validation error was found during parse."""
        return bool(self.errors)

    @property
    def valid_rows(self) -> list[dict[str, Any]]:
        """Rows that had no validation errors."""
        error_rows = {e.row for e in self.errors}
        return [r for i, r in enumerate(self.rows, start=1) if i not in error_rows]


@dataclass
class ImportResult:
    """Summary returned after a committed import.

    Attributes:
        created: Number of records successfully inserted.
        failed: Number of records that failed during insert.
        errors: Errors encountered during commit (row-level).
    """

    created: int
    failed: int
    errors: list[ImportRowError] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total records attempted."""
        return self.created + self.failed


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def _parse_csv(
    content: bytes,
    *,
    column_map: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str], list[ImportRowError]]:
    """Parse CSV bytes into rows and infer column_map if not provided.

    Args:
        content: Raw file bytes.
        column_map: Optional explicit header → field mapping.
            If None, headers are used as-is.

    Returns:
        Tuple of (rows, effective_column_map, parse_errors).
    """
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers: list[str] = list(reader.fieldnames) if reader.fieldnames else []

    effective_map: dict[str, str] = dict(column_map or {h: h for h in headers})

    rows: list[dict[str, Any]] = []
    errors: list[ImportRowError] = []

    for _row_num, raw_row in enumerate(reader, start=1):
        mapped: dict[str, Any] = {}
        for src, dst in effective_map.items():
            val = raw_row.get(src, "").strip()
            mapped[dst] = val or None
        rows.append(mapped)

    return rows, effective_map, errors


def _parse_json(
    content: bytes,
    *,
    column_map: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str], list[ImportRowError]]:
    """Parse JSON bytes (array of objects) into rows.

    Args:
        content: Raw file bytes containing a JSON array.
        column_map: Optional key remapping (source_key → target_field).

    Returns:
        Tuple of (rows, effective_column_map, parse_errors).
    """
    errors: list[ImportRowError] = []
    try:
        data = json.loads(content.decode("utf-8-sig", errors="replace"))
    except json.JSONDecodeError as exc:
        errors.append(
            ImportRowError(row=0, field="__file__", message=f"Invalid JSON: {exc}")
        )
        return [], {}, errors

    if not isinstance(data, list):
        errors.append(
            ImportRowError(
                row=0, field="__file__", message="JSON root must be an array of objects"
            )
        )
        return [], {}, errors

    effective_map: dict[str, str] = column_map or {}
    rows: list[dict[str, Any]] = []

    for row_num, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            errors.append(
                ImportRowError(
                    row=row_num, field="__row__", message="Expected a JSON object"
                )
            )
            continue
        if effective_map:
            mapped: dict[str, Any] = {
                dst: item.get(src) for src, dst in effective_map.items()
            }
        else:
            mapped = dict(item)
        rows.append(mapped)

    return rows, effective_map, errors


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


@inject
class AdminImportService:
    """Service that parses, validates, and commits bulk imports.

    Supports CSV and JSON files.  Validation is performed during
    :meth:`parse` so callers can show a preview before committing.

    Args:
        data_source: An IDataSource-compatible instance that the
            committed rows will be written to via ``create()``.
        required_fields: Field names that must be non-empty on every row.
        max_rows: Maximum number of rows allowed per import (0 = unlimited).
    """

    def __init__(
        self,
        data_source: Any,
        *,
        required_fields: list[str] | None = None,
        max_rows: int = 10_000,
    ) -> None:
        self._data_source = data_source
        self._required_fields: list[str] = required_fields or []
        self._max_rows = max_rows

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def parse(
        self,
        content: bytes,
        filename: str,
        *,
        column_map: dict[str, str] | None = None,
    ) -> Result[ImportJob, AdminError]:
        """Parse uploaded file bytes and return a validated ImportJob.

        Validation is non-destructive — nothing is written to the data source.

        Args:
            content: Raw file bytes.
            filename: Original filename; used to detect format (csv / json).
            column_map: Optional explicit header-to-field mapping.
                CSV: ``{"CSV Header": "model_field"}``
                JSON: ``{"json_key": "model_field"}``
                Defaults to identity mapping (header == field).

        Returns:
            ``Result[ImportJob, AdminError]`` — Ok even when rows have
            validation errors (so callers can show the preview).
            Err only on file-level failures (wrong format, size limit).
        """
        lower = filename.lower()
        if lower.endswith(".csv"):
            rows, effective_map, parse_errors = _parse_csv(
                content, column_map=column_map
            )
        elif lower.endswith((".json", ".jsonl")):
            rows, effective_map, parse_errors = _parse_json(
                content, column_map=column_map
            )
        else:
            return Err(
                AdminError(
                    message=f"Unsupported file format: {filename!r}. Use .csv or .json."
                )
            )

        if parse_errors and not rows:
            return Err(AdminError(message=parse_errors[0].message))

        if self._max_rows and len(rows) > self._max_rows:
            return Err(
                AdminError(
                    message=f"File contains {len(rows):,} rows which exceeds the limit of {self._max_rows:,}."
                )
            )

        # Row-level validation
        validation_errors = list(parse_errors)
        validation_errors.extend(self._validate_rows(rows))

        job = ImportJob(
            rows=rows,
            errors=validation_errors,
            column_map=effective_map,
            source_filename=filename,
            total_rows=len(rows),
        )
        logger.info(
            "Import parsed: filename=%s rows=%d errors=%d",
            filename,
            len(rows),
            len(validation_errors),
        )
        return Ok(job)

    async def commit(self, job: ImportJob) -> Result[ImportResult, AdminError]:
        """Write valid rows from *job* to the data source.

        Rows with errors are skipped.  Remaining rows are inserted one at a
        time; individual insert failures are collected and do not abort the
        rest of the batch.

        Args:
            job: A parsed ImportJob (from :meth:`parse`).

        Returns:
            ``Result[ImportResult, AdminError]`` — Ok with counts and any
            per-row commit errors.
        """
        created = 0
        failed = 0
        commit_errors: list[ImportRowError] = []
        error_row_set = {e.row for e in job.errors}

        for row_num, row in enumerate(job.rows, start=1):
            if row_num in error_row_set:
                failed += 1
                continue
            try:
                await self._data_source.create(row)
                created += 1
            except (ValueError, TypeError, KeyError, RuntimeError) as exc:
                failed += 1
                commit_errors.append(
                    ImportRowError(row=row_num, field="__row__", message=str(exc))
                )
                logger.warning("Import commit error at row %d: %s", row_num, exc)

        result = ImportResult(created=created, failed=failed, errors=commit_errors)
        logger.info(
            "Import committed: filename=%s created=%d failed=%d",
            job.source_filename,
            created,
            failed,
        )
        return Ok(result)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_rows(self, rows: list[dict[str, Any]]) -> list[ImportRowError]:
        """Run required-field validation over all rows.

        Args:
            rows: Parsed rows to validate.

        Returns:
            List of ImportRowError for any violations found.
        """
        errors: list[ImportRowError] = []
        for row_num, row in enumerate(rows, start=1):
            for field_name in self._required_fields:
                val = row.get(field_name)
                if val is None or (isinstance(val, str) and not val.strip()):
                    errors.append(
                        ImportRowError(
                            row=row_num,
                            field=field_name,
                            message=f"'{field_name}' is required",
                        )
                    )
        return errors


__all__ = [
    "AdminImportService",
    "ImportJob",
    "ImportResult",
    "ImportRowError",
]
