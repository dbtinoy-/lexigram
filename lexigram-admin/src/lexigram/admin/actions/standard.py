"""Standard action implementations for lexigram-admin.

Provides ready-to-use RowAction, BulkAction, and HeaderAction subclasses
that wrap common data-source operations such as edit, view, delete, create,
and bulk delete. Each action comes with sensible defaults for name, label,
icon, and color.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import csv
import inspect
import io
from typing import TYPE_CHECKING, Any

from lexigram.admin.actions.base import BulkAction, HeaderAction, RowAction
from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.types import ActionColor, ActionContext, ConfirmationConfig
from lexigram.result import Err, Ok, Result
from lexigram.ui import Zones

if TYPE_CHECKING:
    from lexigram.admin.services.export import ExportFormat, ExportService
    from lexigram.admin.services.import_ import AdminImportService


class EditAction(RowAction):
    """Edit a single record."""

    def __init__(
        self,
        name: str = "edit",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Edit",
            icon="pencil",
            color=ActionColor.PRIMARY,
        )

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}/edit"

    def _get_htmx_attrs(
        self, url: str, record: Any, ctx: ActionContext
    ) -> dict[str, str]:
        return {
            "hx-get": url,
            "hx-target": Zones.SLIDE_OVER.selector,
            "hx-swap": Zones.SLIDE_OVER.swap_mode.value,
        }

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Edited {record}"})


class ViewAction(RowAction):
    """View a single record."""

    def __init__(
        self,
        name: str = "view",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "View",
            icon="eye",
            color=ActionColor.GRAY,
        )

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}"

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Viewed {record}"})


class DeleteAction(RowAction):
    """Delete a single record with confirmation."""

    def __init__(
        self,
        name: str = "delete",
        label: str | None = None,
        confirm_title: str = "Delete Record",
        confirm_message: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Delete",
            icon="trash",
            color=ActionColor.DANGER,
        )
        self._confirm_title = confirm_title
        self._confirm_message = confirm_message or (
            "Are you sure you want to delete this record? This action cannot be undone."
        )

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}/delete-confirm"

    def _get_htmx_attrs(
        self, url: str, record: Any, ctx: ActionContext
    ) -> dict[str, str]:
        return {
            "hx-get": url,
            "hx-target": Zones.SLIDE_OVER.selector,
            "hx-swap": Zones.SLIDE_OVER.swap_mode.value,
            "hx-push-url": "false",
        }

    def confirm(self) -> ConfirmationConfig | None:
        return ConfirmationConfig(
            title=self._confirm_title,
            message=self._confirm_message,
            style=ActionColor.DANGER,
        )

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Deleted {record}", "deleted": True})


class PermissionsAction(RowAction):
    """Edit a user's direct permissions (users resource only)."""

    def __init__(
        self,
        name: str = "permissions",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Edit Permissions",
            icon="shield",
            color=ActionColor.GRAY,
        )

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}/permissions"

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Editing permissions for {record}"})


class CreateAction(HeaderAction):
    """Create a new record."""

    def __init__(
        self,
        name: str = "create",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Create",
            icon="plus",
            color=ActionColor.PRIMARY,
        )

    def _get_htmx_attrs(
        self, url: str, record: None, ctx: ActionContext
    ) -> dict[str, str]:
        return {
            "hx-get": url,
            "hx-target": Zones.SLIDE_OVER.selector,
            "hx-swap": Zones.SLIDE_OVER.swap_mode.value,
        }

    async def execute(self, record: None, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": "Created new record"})


class DeleteBulkAction(BulkAction):
    """Delete multiple selected records."""

    def __init__(
        self,
        name: str = "delete",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Delete Selected",
            icon="trash",
            color=ActionColor.DANGER,
        )

    def _get_htmx_attrs(
        self, url: str, records: list[Any], ctx: ActionContext
    ) -> dict[str, str]:
        # Open bulk delete confirmation slide-over instead of native hx-confirm
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        confirm_url = f"{prefix}/bulk-delete-confirm"
        return {
            "hx-get": confirm_url,
            "hx-target": "#slide-over-container",
            "hx-swap": "innerHTML",
            "hx-push-url": "false",
            "hx-include": "#lexigram-table [name='ids']:checked",
        }

    def confirm(self) -> ConfirmationConfig | None:
        return ConfirmationConfig(
            title="Delete Selected Records",
            message="Are you sure you want to delete the selected records? "
            "This action cannot be undone.",
            style=ActionColor.DANGER,
        )

    async def execute(self, records: list[Any], ctx: ActionContext) -> Result[Any, Any]:
        count = len(records)
        return Ok({"message": f"Deleted {count} record(s)", "deleted_count": count})


class PurgeBulkAction(BulkAction):
    """Permanently delete multiple selected records.

    Deletes are issued in chunks via the data source's ``bulk_delete``,
    mirroring Filament's ``chunkSelectedRecords`` behaviour for large
    selections.
    """

    def __init__(
        self,
        name: str = "purge",
        label: str | None = None,
        data_source: Any | None = None,
        chunk_size: int = 200,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Purge Selected",
            icon="trash-2",
            color=ActionColor.DANGER,
        )
        self._data_source = data_source
        self._chunk_size = chunk_size

    def _get_htmx_attrs(
        self, url: str, records: list[Any], ctx: ActionContext
    ) -> dict[str, str]:
        # Open bulk purge confirmation slide-over instead of native hx-confirm
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        confirm_url = f"{prefix}/bulk-purge-confirm"
        return {
            "hx-get": confirm_url,
            "hx-target": "#slide-over-container",
            "hx-swap": "innerHTML",
            "hx-push-url": "false",
            "hx-include": "#lexigram-table [name='ids']:checked",
        }

    def confirm(self) -> ConfirmationConfig | None:
        return ConfirmationConfig(
            title="Purge Selected Records",
            message="Are you sure you want to permanently purge the selected "
            "records? This action cannot be undone.",
            style=ActionColor.DANGER,
        )

    async def execute(self, records: list[Any], ctx: ActionContext) -> Result[Any, Any]:
        data_source = _resolve_data_source(ctx, self._data_source)
        if data_source is None:
            return Err(
                ActionError(
                    "Purge requires a data source; inject one or set ctx.data_source."
                )
            )
        ids = [
            item_id
            for record in records
            if (item_id := _extract_id(record)) is not None
        ]
        chunk_size = self._chunk_size or len(ids) or 1
        purged = 0
        for start in range(0, len(ids), chunk_size):
            purged += await data_source.bulk_delete(ids[start : start + chunk_size])
        return Ok({"message": f"Purged {purged} record(s)", "purged_count": purged})


class RestoreBulkAction(BulkAction):
    """Restore multiple soft-deleted records."""

    def __init__(
        self,
        name: str = "restore",
        label: str | None = None,
        data_source: Any | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Restore Selected",
            icon="rotate-ccw",
            color=ActionColor.SUCCESS,
        )
        self._data_source = data_source

    def _get_htmx_attrs(
        self, url: str, records: list[Any], ctx: ActionContext
    ) -> dict[str, str]:
        # Open bulk restore confirmation slide-over instead of native hx-confirm
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        confirm_url = f"{prefix}/bulk-restore-confirm"
        return {
            "hx-get": confirm_url,
            "hx-target": "#slide-over-container",
            "hx-swap": "innerHTML",
            "hx-push-url": "false",
            "hx-include": "#lexigram-table [name='ids']:checked",
        }

    def confirm(self) -> ConfirmationConfig | None:
        return ConfirmationConfig(
            title="Restore Selected Records",
            message="Are you sure you want to restore the selected records?",
            style=ActionColor.SUCCESS,
        )

    async def execute(self, records: list[Any], ctx: ActionContext) -> Result[Any, Any]:
        data_source = _resolve_data_source(ctx, self._data_source)
        if data_source is None:
            return Err(
                ActionError(
                    "Restore requires a data source; inject one or set ctx.data_source."
                )
            )
        ids = [
            item_id
            for record in records
            if (item_id := _extract_id(record)) is not None
        ]
        restored = 0
        for item_id in ids:
            updated = await data_source.update(item_id, {"deleted_at": None})
            if updated is not None:
                restored += 1
        return Ok(
            {"message": f"Restored {restored} record(s)", "restored_count": restored}
        )


class CloneAction(RowAction):
    """Clone a single record through the data source.

    Mirrors Filament's ``Replicate`` action: ``exclude_attributes`` drops
    fields from the copy (``excludeAttributes``), ``mutate_record_data``
    transforms the record data before creation (``mutateRecordDataUsing``),
    and ``before_replica_saved`` runs just before the new record is
    persisted (``beforeReplicaSaved``). The ``id`` field is always stripped
    so a fresh identifier is assigned.
    """

    def __init__(
        self,
        name: str = "clone",
        label: str | None = None,
        data_source: Any | None = None,
        exclude_attributes: list[str] | None = None,
        mutate_record_data: Callable[
            [dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]
        ]
        | None = None,
        before_replica_saved: Callable[[dict[str, Any]], None | Awaitable[None]]
        | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Clone",
            icon="copy",
            color=ActionColor.SECONDARY,
        )
        self._data_source = data_source
        self._exclude_attributes = exclude_attributes or []
        self._mutate_record_data = mutate_record_data
        self._before_replica_saved = before_replica_saved

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}/clone"

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        record_id = _extract_id(record)
        if record_id is None:
            return Err(ActionError("Clone requires a record with an id."))
        data_source = _resolve_data_source(ctx, self._data_source)
        if data_source is None:
            return Err(
                ActionError(
                    "Clone requires a data source; inject one or set ctx.data_source."
                )
            )
        original = await data_source.find_one(record_id)
        if original is None:
            return Err(ActionError(f"Record {record_id} not found."))
        data: dict[str, Any] = dict(original) if isinstance(original, dict) else {}
        if not data and hasattr(original, "__dict__"):
            data = dict(vars(original))
        data.pop("id", None)
        for attribute in self._exclude_attributes:
            data.pop(attribute, None)
        if self._mutate_record_data is not None:
            mutated = self._mutate_record_data(data)
            data = await mutated if inspect.isawaitable(mutated) else mutated
        if self._before_replica_saved is not None:
            hook = self._before_replica_saved(data)
            if inspect.isawaitable(hook):
                await hook
        created = await data_source.create(data)
        if created is None:
            return Err(ActionError(f"Failed to clone record {record_id}."))
        return Ok(
            {
                "message": "Cloned record",
                "record": created,
                "cloned_id": _extract_id(created),
            }
        )


class RestoreAction(RowAction):
    """Restore a single soft-deleted record."""

    def __init__(
        self,
        name: str = "restore",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Restore",
            icon="rotate-ccw",
            color=ActionColor.SUCCESS,
        )

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}/restore"

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Restored {record}"})


class PurgeAction(RowAction):
    """Permanently delete a soft-deleted record."""

    def __init__(
        self,
        name: str = "purge",
        label: str | None = None,
        confirm_title: str = "Permanently Delete Record",
        confirm_message: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Purge",
            icon="trash-2",
            color=ActionColor.DANGER,
        )
        self._confirm_title = confirm_title
        self._confirm_message = confirm_message or (
            "Are you sure you want to permanently delete this record? "
            "This action cannot be undone."
        )

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}/purge"

    def _get_htmx_attrs(
        self, url: str, record: Any, ctx: ActionContext
    ) -> dict[str, str]:
        attrs: dict[str, str] = {
            "hx-delete": url,
            "hx-target": "#table-data",
            "hx-swap": "innerHTML",
        }
        confirmation = self.confirm()
        if confirmation and confirmation.message:
            attrs["hx-confirm"] = confirmation.message
        return attrs

    def confirm(self) -> ConfirmationConfig | None:
        return ConfirmationConfig(
            title=self._confirm_title,
            message=self._confirm_message,
            style=ActionColor.DANGER,
        )

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Purged {record}", "purged": True})


def _extract_id(record: Any) -> Any | None:
    """Extract the ``id`` field from a record dict or object."""
    if isinstance(record, dict):
        return record.get("id")
    return getattr(record, "id", None)


def _resolve_data_source(ctx: ActionContext, injected: Any | None = None) -> Any | None:
    """Resolve the data source for an action execution.

    Precedence: constructor-injected value, ``ctx.data_source``, then
    ``ctx.metadata["data_source"]``.
    """
    if injected is not None:
        return injected
    if ctx.data_source is not None:
        return ctx.data_source
    return ctx.metadata.get("data_source")


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


__all__ = [
    "CloneAction",
    "CreateAction",
    "DeleteAction",
    "DeleteBulkAction",
    "EditAction",
    "ExportAction",
    "ExportBulkAction",
    "ImportAction",
    "ImportBulkAction",
    "PurgeAction",
    "PurgeBulkAction",
    "RestoreAction",
    "RestoreBulkAction",
    "ViewAction",
]
