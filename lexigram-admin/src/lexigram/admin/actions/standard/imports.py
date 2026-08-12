"""Import actions (import, import bulk) with failed-import reports.

Part of the ``lexigram.admin.actions.standard`` package.
"""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING, Any

from lexigram.admin.actions.base import BulkAction, HeaderAction
from lexigram.admin.actions.standard.utils import _resolve_data_source
from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.types import (
    ActionColor,
    ActionContext,
    ConfirmationConfig,
)
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.admin.services.import_ import AdminImportService
async def _run_import(
    service: AdminImportService,
    content: bytes,
    filename: str,
) -> Result[Any, Any]:
    """Parse and commit an import, returning the result summary."""
    parsed = await service.parse(content, filename)
    if parsed.is_err():
        return Err(parsed.unwrap_err())
    committed = await service.commit(parsed.unwrap())
    if committed.is_err():
        return Err(committed.unwrap_err())
    result = committed.unwrap()
    payload: dict[str, Any] = {
        "message": f"Imported {result.created} of {result.total} record(s)",
        "created": result.created,
        "failed": result.failed,
        "total": result.total,
    }
    if result.failed:
        reports = service.reports()
        if reports:
            report = reports[-1]
            stem = report.source_filename.rpartition(".")[0] or "import"
            payload["report_id"] = report.id
            payload["report_filename"] = f"{stem}-import-errors.csv"
    return Ok(payload)
class _ImportReportMixin:
    """Shared failed-import report download helpers for import actions.

    Depends on ``self._import_service`` (an :class:`AdminImportService`
    with stored reports).
    """

    _import_service: AdminImportService | None = None

    def report_csv(self, report_id: str) -> str | None:
        """Return CSV content of a stored failed-import report.

        Args:
            report_id: Report identifier from the import service.

        Returns:
            CSV content, or None when no service is configured or the
            report id is unknown.
        """
        service = self._import_service
        if service is None:
            return None
        report = service.get_report(report_id)
        if report is None:
            return None
        return report.to_csv()

    def report_filename(self, report_id: str) -> str | None:
        """Derive a download filename for a stored failed-import report.

        Args:
            report_id: Report identifier from the import service.

        Returns:
            ``{source}-import-errors.csv`` filename, or None when no
            service is configured or the report id is unknown.
        """
        service = self._import_service
        if service is None:
            return None
        report = service.get_report(report_id)
        if report is None:
            return None
        stem = report.source_filename.rpartition(".")[0] or "import"
        return f"{stem}-import-errors.csv"
class ImportAction(_ImportReportMixin, HeaderAction):
    """Import records into a resource through the admin import service."""

    def __init__(
        self,
        name: str = "import",
        label: str | None = None,
        import_service: AdminImportService | None = None,
        data_source: Any | None = None,
        file_content: bytes | None = None,
        filename: str | None = None,
        example_columns: list[str] | None = None,
        example_filename: str = "import-example.csv",
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Import",
            icon="upload",
            color=ActionColor.GRAY,
        )
        self._import_service = import_service
        self._data_source = data_source
        self._file_content = file_content
        self._filename = filename
        self._example_columns = example_columns or []
        self._example_filename = example_filename

    def example_csv(self) -> str:
        """Build a header-only example CSV from ``example_columns``.

        Mirrors Filament's ``ImportAction::exampleCsv()``. Returns an empty
        string when no example columns are configured.
        """
        if not self._example_columns:
            return ""
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(self._example_columns)
        return buffer.getvalue()

    @property
    def example_filename(self) -> str:
        """Download filename for the example CSV template."""
        return self._example_filename

    async def execute(self, record: None, ctx: ActionContext) -> Result[Any, Any]:
        content = self._file_content or ctx.metadata.get("file_content")
        if content is None:
            return Err(
                ActionError(
                    "Import requires file content; pass file_content to the action "
                    "or set ctx.metadata['file_content']."
                )
            )
        filename = self._filename or ctx.metadata.get("filename") or "import.csv"
        service = self._import_service
        if service is None:
            data_source = _resolve_data_source(ctx, self._data_source)
            if data_source is None:
                return Err(
                    ActionError(
                        "Import requires an AdminImportService or a data source; "
                        "inject one or set ctx.data_source."
                    )
                )
            from lexigram.admin.services.import_ import AdminImportService

            service = AdminImportService(data_source=data_source)
        return await _run_import(service, content, filename)
class ImportBulkAction(_ImportReportMixin, BulkAction):
    """Import multiple records through the admin import service."""

    def __init__(
        self,
        name: str = "import",
        label: str | None = None,
        import_service: AdminImportService | None = None,
        data_source: Any | None = None,
        file_content: bytes | None = None,
        filename: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Import Selected",
            icon="upload",
            color=ActionColor.GRAY,
        )
        self._import_service = import_service
        self._data_source = data_source
        self._file_content = file_content
        self._filename = filename

    async def execute(self, records: list[Any], ctx: ActionContext) -> Result[Any, Any]:
        content = self._file_content or ctx.metadata.get("file_content")
        if content is None:
            return Err(
                ActionError(
                    "Import requires file content; pass file_content to the action "
                    "or set ctx.metadata['file_content']."
                )
            )
        filename = self._filename or ctx.metadata.get("filename") or "import.csv"
        service = self._import_service
        if service is None:
            data_source = _resolve_data_source(ctx, self._data_source)
            if data_source is None:
                return Err(
                    ActionError(
                        "Import requires an AdminImportService or a data source; "
                        "inject one or set ctx.data_source."
                    )
                )
            from lexigram.admin.services.import_ import AdminImportService

            service = AdminImportService(data_source=data_source)
        return await _run_import(service, content, filename)
