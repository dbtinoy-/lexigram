"""Export actions backed by the admin ExportService.

Part of the ``lexigram.admin.actions.standard`` package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.actions.base import BulkAction, RowAction
from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.standard.utils import _extract_id, _resolve_data_source
from lexigram.admin.actions.types import (
    ActionColor,
    ActionContext,
)
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.admin.services.export import ExportFormat, ExportService


async def _resolve_export_service(ctx: ActionContext) -> ExportService | None:
    """Resolve an ExportService from the request container.

    Returns None when the request or container is unavailable, or when
    resolution fails (e.g. the service is not registered).
    """
    if ctx.request is None:
        return None
    container = getattr(ctx.request.state, "container", None) or getattr(
        ctx.request.app.state, "container", None
    )
    if container is None:
        return None
    try:
        from lexigram.admin.services.export import ExportService

        return await container.resolve(ExportService)
    except Exception:  # noqa: BLE001 — non-fatal
        return None


async def _run_export(
    ctx: ActionContext,
    service: ExportService,
    data_source: Any,
    filters: dict[str, Any],
    *,
    resource_name: str,
    file_format: ExportFormat,
    message: str,
) -> Result[Any, Any]:
    """Create and execute an export job, returning the job summary."""
    from lexigram.admin.data.adapters.export_adapter import ExportDataSourceAdapter

    job_id = service.create_job(
        resource_name=resource_name,
        file_format=file_format,
        filters=filters,
        user_id=getattr(ctx.user, "id", None),
    )
    result = await service.execute_export(job_id, ExportDataSourceAdapter(data_source))
    if result.is_err():
        return Err(result.unwrap_err())
    job = result.unwrap()
    return Ok(
        {
            "message": message,
            "job_id": job.job_id,
            "total_records": job.total_records,
            "download_url": job.download_url,
            "file_path": job.file_path,
        }
    )


class ExportAction(RowAction):
    """Export a single record through the admin ExportService."""

    def __init__(
        self,
        name: str = "export",
        label: str | None = None,
        export_service: ExportService | None = None,
        data_source: Any | None = None,
        file_format: ExportFormat | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Export",
            icon="download",
            color=ActionColor.GRAY,
        )
        if file_format is None:
            from lexigram.admin.services.export import ExportFormat

            file_format = ExportFormat.CSV
        self._export_service = export_service
        self._data_source = data_source
        self._file_format = file_format

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        record_id = self._get_record_id(record)
        if not record_id:
            return Err(ActionError("Cannot export a record without an id."))
        service = self._export_service
        if service is None:
            service = await _resolve_export_service(ctx)
        if service is None:
            return Err(
                ActionError(
                    "Export requires an ExportService; inject one via the action "
                    "constructor or register it in the request container."
                )
            )
        data_source = _resolve_data_source(ctx, self._data_source)
        if data_source is None:
            return Err(
                ActionError(
                    "Export requires a data source; set ctx.data_source or "
                    "ctx.metadata['data_source']."
                )
            )
        return await _run_export(
            ctx=ctx,
            service=service,
            data_source=data_source,
            filters={"id": record_id},
            resource_name=ctx.resource_name or self.name,
            file_format=self._file_format,
            message=f"Exported record {record_id}",
        )


class ExportBulkAction(BulkAction):
    """Export multiple selected records through the admin ExportService."""

    def __init__(
        self,
        name: str = "export",
        label: str | None = None,
        export_service: ExportService | None = None,
        data_source: Any | None = None,
        file_format: ExportFormat | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Export Selected",
            icon="download",
            color=ActionColor.GRAY,
        )
        if file_format is None:
            from lexigram.admin.services.export import ExportFormat

            file_format = ExportFormat.CSV
        self._export_service = export_service
        self._data_source = data_source
        self._file_format = file_format

    async def execute(self, records: list[Any], ctx: ActionContext) -> Result[Any, Any]:
        record_ids = [
            record_id
            for record_id in (_extract_id(record) for record in records)
            if record_id is not None
        ]
        if not record_ids:
            return Err(ActionError("Cannot export records without ids."))
        service = self._export_service
        if service is None:
            service = await _resolve_export_service(ctx)
        if service is None:
            return Err(
                ActionError(
                    "Export requires an ExportService; inject one via the action "
                    "constructor or register it in the request container."
                )
            )
        data_source = _resolve_data_source(ctx, self._data_source)
        if data_source is None:
            return Err(
                ActionError(
                    "Export requires a data source; set ctx.data_source or "
                    "ctx.metadata['data_source']."
                )
            )
        return await _run_export(
            ctx=ctx,
            service=service,
            data_source=data_source,
            filters={"id__in": record_ids},
            resource_name=ctx.resource_name or self.name,
            file_format=self._file_format,
            message=f"Exported {len(record_ids)} record(s)",
        )
