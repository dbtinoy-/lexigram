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

try:  # R26: optional dependency shared with the Excel export backend.
    import openpyxl  # type: ignore[import-untyped]

    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

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
        rows: Parsed rows as dicts keyed by mapped field names. Rows that
            failed to parse are empty placeholders so that error ``row``
            numbers always match 1-based positions in this list.
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


@dataclass
class ImportReport:
    """Stored failed-import report for post-hoc download.

    Persisted by :class:`AdminImportService` whenever a commit has
    failed rows, so callers can surface a downloadable error report
    of the failed rows.

    Attributes:
        id: Unique report identifier.
        source_filename: Original uploaded filename.
        created_at: ISO-8601 timestamp of report creation.
        total_rows: Number of data rows attempted.
        failed_rows: Number of rows that failed.
        failures: Per-row validation/commit errors.
    """

    id: str
    source_filename: str
    created_at: str
    total_rows: int
    failed_rows: int
    failures: list[ImportRowError]

    def to_csv(self) -> str:
        """Serialize failed rows as CSV (row number, field, message)."""
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["row", "field", "message"])
        for err in self.failures:
            writer.writerow([err.row, err.field, err.message])
        return buffer.getvalue()


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
            # B15: csv.DictReader fills missing trailing cells with None
            # (restval), so ragged rows must not assume str values.
            raw_val = raw_row.get(src)
            if isinstance(raw_val, str):
                stripped = raw_val.strip()
                mapped[dst] = stripped or None
            else:
                mapped[dst] = raw_val
        rows.append(mapped)

    return rows, effective_map, errors


def _parse_xlsx(
    content: bytes,
    *,
    column_map: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str], list[ImportRowError]]:
    """Parse Excel (.xlsx) bytes into rows (R26).

    Mirrors ``_parse_csv`` semantics: the first row of the active sheet
    is the header row, the effective mapping defaults to identity, string
    cells are stripped (empty → ``None``), and non-string cells (numbers,
    dates, booleans) pass through natively — like JSON values.

    ``openpyxl`` is optional (shared with the Excel export backend); when
    unavailable a file-level error is returned so ``parse()`` surfaces a
    clean ``Err`` instead of a traceback.

    Args:
        content: Raw ``.xlsx`` file bytes.
        column_map: Optional explicit header → field mapping.

    Returns:
        Tuple of (rows, effective_column_map, parse_errors).
    """
    errors: list[ImportRowError] = []
    if not HAS_OPENPYXL:
        errors.append(
            ImportRowError(
                row=0,
                field="__file__",
                message=(
                    "Excel import requires the optional 'openpyxl' dependency — "
                    "install lexigram-admin[export]."
                ),
            )
        )
        return [], {}, errors

    try:
        # data_only=True reads cached formula *results*, never formulas;
        # read_only streams rows without loading the full workbook.
        workbook = openpyxl.load_workbook(
            io.BytesIO(content), read_only=True, data_only=True
        )
    except Exception as exc:  # noqa: BLE001 — any load failure is a bad file
        errors.append(
            ImportRowError(
                row=0, field="__file__", message=f"Invalid Excel file: {exc}"
            )
        )
        return [], {}, errors

    try:
        sheet = workbook.active
        rows_iter = sheet.iter_rows(values_only=True) if sheet is not None else iter(())
        header_cells = next(rows_iter, None)
        # Positional header list; unnamed columns stay as "" and are ignored.
        headers: list[str] = [
            (str(cell).strip() if cell is not None else "")
            for cell in (header_cells or ())
        ]
        named_headers = [h for h in headers if h]
        if not named_headers:
            errors.append(
                ImportRowError(
                    row=0, field="__file__", message="Excel file has no header row"
                )
            )
            return [], {}, errors

        effective_map: dict[str, str] = dict(
            column_map or {h: h for h in named_headers}
        )

        rows: list[dict[str, Any]] = []
        for values in rows_iter:
            cells = tuple(values or ())
            # Skip fully blank spreadsheet rows (common trailing artifact).
            if all(
                cell is None or (isinstance(cell, str) and not cell.strip())
                for cell in cells
            ):
                continue
            raw_row: dict[str, Any] = {}
            for idx, header in enumerate(headers):
                if not header:
                    continue
                # Ragged rows fill with None — same posture as B15 for CSV.
                raw_row[header] = cells[idx] if idx < len(cells) else None
            mapped: dict[str, Any] = {}
            for src, dst in effective_map.items():
                raw_val = raw_row.get(src)
                if isinstance(raw_val, str):
                    stripped = raw_val.strip()
                    mapped[dst] = stripped or None
                else:
                    mapped[dst] = raw_val
            rows.append(mapped)
        return rows, effective_map, errors
    finally:
        workbook.close()


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
            # B16: append a placeholder so error row numbers stay aligned
            # with positions in ``rows`` — commit()/valid_rows skip rows by
            # index, and a compacted list made them skip the WRONG rows
            # (silent data loss for valid neighbours).
            rows.append({})
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


def _parse_jsonl(
    content: bytes,
    *,
    column_map: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str], list[ImportRowError]]:
    """Parse JSON Lines bytes (one JSON object per line) into rows.

    B15b: ``.jsonl`` uploads were previously routed to the JSON-array
    parser and always failed with "Invalid JSON". Real JSONL is one
    object per non-empty line.

    Error ``row`` numbers refer to 1-based positions in the returned
    ``rows`` list (unparseable lines append an empty placeholder row so
    positions stay aligned).

    Args:
        content: Raw file bytes in JSON Lines format.
        column_map: Optional key remapping (source_key → target_field).

    Returns:
        Tuple of (rows, effective_column_map, parse_errors).
    """
    errors: list[ImportRowError] = []
    effective_map: dict[str, str] = column_map or {}
    rows: list[dict[str, Any]] = []
    text = content.decode("utf-8-sig", errors="replace")

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        row_num = len(rows) + 1
        try:
            item = json.loads(stripped)
        except json.JSONDecodeError as exc:
            rows.append({})
            errors.append(
                ImportRowError(
                    row=row_num, field="__row__", message=f"Invalid JSON: {exc}"
                )
            )
            continue
        if not isinstance(item, dict):
            rows.append({})
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
        allowed_fields: set[str] | None = None,
    ) -> None:
        self._data_source = data_source
        self._required_fields: list[str] = required_fields or []
        self._max_rows = max_rows
        # Mass-assignment guard: when set, rows carrying keys outside this
        # allowlist are rejected during validation.
        self._allowed_fields = allowed_fields
        self._reports: list[ImportReport] = []

    # ------------------------------------------------------------------
    # Failed-import reports
    # ------------------------------------------------------------------

    def reports(self) -> list[ImportReport]:
        """Return all stored failed-import reports (most recent last).

        Returns:
            Copy of the in-memory report list; empty when no imports
            have failed.
        """
        return list(self._reports)

    def get_report(self, report_id: str) -> ImportReport | None:
        """Look up a stored failed-import report by id.

        Args:
            report_id: Report identifier from :meth:`reports`.

        Returns:
            The matching report, or None when unknown.
        """
        for report in self._reports:
            if report.id == report_id:
                return report
        return None

    def delete_report(self, report_id: str) -> bool:
        """Remove a stored failed-import report.

        Args:
            report_id: Report identifier from :meth:`reports`.

        Returns:
            True when the report was removed, False when unknown.
        """
        for index, report in enumerate(self._reports):
            if report.id == report_id:
                del self._reports[index]
                return True
        return False

    def _store_report(self, job: ImportJob, result: ImportResult) -> None:
        """Persist a failed-import report for the given commit result."""
        from lexigram.identity import ambient as identity
        from lexigram.primitives import clock

        self._reports.append(
            ImportReport(
                id=identity.new_uuid(),
                source_filename=job.source_filename,
                created_at=clock.now().isoformat(),
                total_rows=len(job.rows),
                failed_rows=result.failed,
                failures=[*job.errors, *result.errors],
            )
        )

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
        elif lower.endswith(".jsonl"):
            rows, effective_map, parse_errors = _parse_jsonl(
                content, column_map=column_map
            )
        elif lower.endswith(".json"):
            rows, effective_map, parse_errors = _parse_json(
                content, column_map=column_map
            )
        elif lower.endswith(".xlsx"):
            rows, effective_map, parse_errors = _parse_xlsx(
                content, column_map=column_map
            )
        else:
            return Err(
                AdminError(
                    message=(
                        f"Unsupported file format: {filename!r}. "
                        "Use .csv, .json, .jsonl, or .xlsx."
                    )
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

        # Row-level validation. Rows that already failed at parse time are
        # placeholders — skip them so operators don't see cascading
        # "field required" noise on top of the parse error.
        validation_errors = list(parse_errors)
        parse_error_rows = {e.row for e in parse_errors}
        validation_errors.extend(self._validate_rows(rows, skip_rows=parse_error_rows))

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
            except Exception as exc:  # noqa: BLE001 — B17: the documented contract is that a single bad row never aborts the batch; DB drivers raise arbitrary exception types (CancelledError still propagates: it derives from BaseException).
                failed += 1
                commit_errors.append(
                    ImportRowError(row=row_num, field="__row__", message=str(exc))
                )
                logger.warning("Import commit error at row %d: %s", row_num, exc)

        result = ImportResult(created=created, failed=failed, errors=commit_errors)
        if result.failed:
            self._store_report(job, result)
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

    def _validate_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        skip_rows: set[int] | None = None,
    ) -> list[ImportRowError]:
        """Run required-field validation over all rows.

        Args:
            rows: Parsed rows to validate.
            skip_rows: 1-based row numbers to skip (rows that already
                failed during parse and only hold placeholder data).

        Returns:
            List of ImportRowError for any violations found.
        """
        errors: list[ImportRowError] = []
        skip = skip_rows or set()
        for row_num, row in enumerate(rows, start=1):
            if row_num in skip:
                continue
            if self._allowed_fields is not None:
                for key in row:
                    if key not in self._allowed_fields:
                        errors.append(
                            ImportRowError(
                                row=row_num,
                                field=key,
                                message=f"Unknown field '{key}' (not importable)",
                            )
                        )
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
