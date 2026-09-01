from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from lexigram.di.decorators import inject
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from lexigram.admin.services.export.job_manager import ExportJobManager
    from lexigram.admin.services.session import SessionStateService
    from lexigram.contracts.core import TaskManagerProtocol
    from lexigram.contracts.infra.storage import BlobStoreProtocol
    from lexigram.contracts.mailer.protocols import MailerProtocol


from lexigram.admin.exceptions import AdminError
from lexigram.admin.services.export.base import (
    IExportBackend,
    IExportDataSource,
    JsonExportBackend,
)
from lexigram.admin.services.export.scheduler import (
    ExportFormat,
    ExportJob,
    ExportSchedule,
    ExportStatus,
    ExportTemplate,
)
from lexigram.contracts.audit import AuditEntry, AuditEventSeverity, AuditLoggerProtocol
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


@inject
class ExportService:
    """Advanced export service with modular backends and job management."""

    def __init__(
        self,
        storage: BlobStoreProtocol,
        task_manager: TaskManagerProtocol,
        job_manager: ExportJobManager | None = None,
        messaging: MailerProtocol | None = None,
        session: SessionStateService | None = None,
        export_dir: str = "exports",
        max_file_age_days: int = 7,
        audit: AuditLoggerProtocol | None = None,
    ):
        from lexigram.admin.services.export.adapters.csv import CsvExportBackend
        from lexigram.admin.services.export.adapters.excel import ExcelExportBackend
        from lexigram.admin.services.export.adapters.pdf import PdfExportBackend
        from lexigram.admin.services.export.job_manager import ExportJobManager

        self.storage = storage
        self.task_manager = task_manager
        self.messaging = messaging
        self.session = session
        self.export_dir = export_dir
        self.max_file_age_days = max_file_age_days
        self.audit = audit

        self._job_manager = job_manager or ExportJobManager()
        self._background_tasks: dict[str, asyncio.Task] = {}

        # Register default backends
        self._backends: dict[ExportFormat, IExportBackend] = {
            ExportFormat.CSV: CsvExportBackend(),
            ExportFormat.JSON: JsonExportBackend(),
            ExportFormat.EXCEL: ExcelExportBackend(),
            ExportFormat.PDF: PdfExportBackend(),
        }

    # -------------------------------------------------------------------------
    # Template Management (delegated to job manager)
    # -------------------------------------------------------------------------

    def register_template(self, template: ExportTemplate) -> None:
        """Register an export template."""
        self._job_manager.register_template(template)

    def get_template(self, name: str) -> ExportTemplate | None:
        """Get a registered template."""
        return self._job_manager.get_template(name)

    def list_templates(self) -> list[ExportTemplate]:
        """List all registered templates."""
        return self._job_manager.list_templates()

    # -------------------------------------------------------------------------
    # Export Job Management (delegated to job manager)
    # -------------------------------------------------------------------------

    def create_job(
        self,
        resource_name: str,
        file_format: ExportFormat,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        template_name: str | None = None,
        user_id: Any | None = None,
        scheduled_for: datetime | None = None,
        schedule_type: ExportSchedule = ExportSchedule.IMMEDIATE,
        email_recipients: list[str] | None = None,
    ) -> str:
        """Create a new export job."""
        return self._job_manager.create_job(
            resource_name=resource_name,
            file_format=file_format,
            filters=filters,
            columns=columns,
            template_name=template_name,
            user_id=user_id,
            scheduled_for=scheduled_for,
            schedule_type=schedule_type,
            email_recipients=email_recipients,
        )

    def get_job(self, job_id: str) -> ExportJob | None:
        """Get export job by ID."""
        return self._job_manager.get_job(job_id)

    def list_jobs(
        self,
        user_id: Any | None = None,
        status: ExportStatus | None = None,
        limit: int = 50,
    ) -> list[ExportJob]:
        """List export jobs with optional filtering."""
        return self._job_manager.list_jobs(user_id=user_id, status=status, limit=limit)

    async def _record_export_audit(
        self,
        *,
        job: ExportJob,
        action: str,
        outcome: str,
        severity: AuditEventSeverity,
        **metadata: object,
    ) -> None:
        """Record an audit event for an export operation."""
        if self.audit is None or job.user_id is None:
            return

        await self.audit.log(
            AuditEntry(
                action=action,
                actor_id=str(job.user_id),
                resource_type="export_job",
                resource_id=job.job_id,
                outcome=outcome,
                severity=severity,
                metadata={
                    "resource_name": job.resource_name,
                    "format": job.format.value,
                    **{k: str(v) for k, v in metadata.items()},
                },
                source="admin",
            )
        )

    # -------------------------------------------------------------------------
    # Export Execution
    # -------------------------------------------------------------------------

    async def execute_export(
        self,
        job_id: str,
        data_source: IExportDataSource,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Result[ExportJob, AdminError]:
        """Execute an export job."""
        job = self.get_job(job_id)
        if not job:
            return Err(AdminError(message=f"Export job {job_id} not found"))

        backend = self._backends.get(job.format)
        if not backend:
            job.status = ExportStatus.FAILED
            job.error_message = f"Unsupported export format: {job.format}"
            job.completed_at = datetime.now(UTC)
            await self._record_export_audit(
                job=job,
                action="admin.export.failed",
                outcome="failure",
                severity=AuditEventSeverity.HIGH,
                error_message=job.error_message,
            )
            return Err(AdminError(message=job.error_message))

        try:
            # Update job status
            job.status = ExportStatus.PROCESSING
            job.started_at = datetime.now(UTC)

            # Record export start audit event
            await self._record_export_audit(
                job=job,
                action="admin.export.start",
                outcome="success",
                severity=AuditEventSeverity.MEDIUM,
            )

            # Get total count
            job.total_records = await data_source.get_export_count(job.filters)

            # Get data in chunks
            all_data = []
            offset = 0
            chunk_size = 1000

            while offset < job.total_records:
                # B21: observe manager-level cancellation. Without this
                # check a cancel_job() call was silently clobbered — the
                # loop ran to completion and overwrote CANCELLED with
                # COMPLETED.
                if job.status is ExportStatus.CANCELLED:
                    return await self._finish_cancelled(job)

                chunk = await data_source.get_export_data(
                    filters=job.filters,
                    columns=job.columns,
                    limit=chunk_size,
                    offset=offset,
                )

                if not chunk:
                    break

                all_data.extend(chunk)
                offset += len(chunk)
                job.processed_records = len(all_data)

                # Update progress
                progress = (
                    (len(all_data) / job.total_records) * 100
                    if job.total_records > 0
                    else 100
                )
                job.progress = progress

                if progress_callback:
                    try:
                        progress_callback(progress)
                    except Exception:  # noqa: BLE001 — progress callbacks are user-supplied and may raise anything; failure is non-fatal
                        logger.exception("Progress callback failed for job %s", job_id)

            # B21: a cancel that landed after the last chunk must not be
            # overwritten by the COMPLETED transition below.
            if job.status is ExportStatus.CANCELLED:
                return await self._finish_cancelled(job)

            # Generate file via backend
            file_path = await backend.generate_file(
                job,
                all_data,
                self.storage,
                self.export_dir,
            )

            # Update job with results
            job.status = ExportStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
            job.file_path = file_path
            job.file_size = await self._get_file_size(file_path)
            job.download_url = await self._generate_download_url(file_path)

            # Record export complete audit event
            await self._record_export_audit(
                job=job,
                action="admin.export.complete",
                outcome="success",
                severity=AuditEventSeverity.HIGH,
                total_records=job.total_records,
            )

            return Ok(job)

        except asyncio.CancelledError:
            job.status = ExportStatus.CANCELLED
            job.completed_at = datetime.now(UTC)
            raise
        except (OSError, RuntimeError, ValueError, AttributeError, LookupError) as e:
            # Known failure modes during export (I/O, runtime, validation); log and mark job failed
            logger.exception("Export job %s failed", job_id)
            job.status = ExportStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(UTC)

            # Record export failed audit event
            await self._record_export_audit(
                job=job,
                action="admin.export.failed",
                outcome="failure",
                severity=AuditEventSeverity.HIGH,
                error_message=str(e),
            )

            return Err(AdminError(message=job.error_message or "Export failed"))
        except Exception as e:  # noqa: BLE001 — catch-all safety net; unexpected failures must mark the job as failed
            # Catch-all for unexpected errors — log with traceback so it's visible in monitoring
            logger.exception("Unexpected error in export job %s", job_id)
            job.status = ExportStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(UTC)

            # Record export failed audit event
            await self._record_export_audit(
                job=job,
                action="admin.export.failed",
                outcome="failure",
                severity=AuditEventSeverity.HIGH,
                error_message=str(e),
            )

            return Err(AdminError(message=job.error_message or "Export failed"))

    async def _finish_cancelled(self, job: ExportJob) -> Result[ExportJob, AdminError]:
        """Finalize a job whose CANCELLED status was observed mid-execution.

        B21: keeps the CANCELLED status authoritative (never overwritten by
        COMPLETED), stamps ``completed_at`` if the canceller didn't, and
        records an audit event.

        Args:
            job: The export job marked cancelled while executing.

        Returns:
            ``Err`` describing the cancellation.
        """
        if job.completed_at is None:
            job.completed_at = datetime.now(UTC)
        await self._record_export_audit(
            job=job,
            action="admin.export.cancelled",
            outcome="failure",
            severity=AuditEventSeverity.MEDIUM,
            processed_records=job.processed_records,
        )
        return Err(AdminError(message=f"Export job {job.job_id} was cancelled"))

    async def _get_file_size(self, file_path: str) -> int:
        """Get file size from storage."""
        try:
            # Placeholder: implementation depends on storage provider
            return 0
        except (AttributeError, OSError) as e:
            logger.warning("Failed to determine file size for %s: %s", file_path, e)
            return 0

    async def _generate_download_url(self, file_path: str) -> str:
        """Generate download URL for file."""
        # Placeholder: implementation depends on storage provider / router
        return f"/admin/exports/download/{file_path}"

    async def stream_export(
        self,
        data_source: IExportDataSource,
        export_format: ExportFormat,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        batch_size: int = 1000,
    ) -> AsyncIterator[bytes]:
        """Stream an export as encoded bytes without buffering the dataset.

        B22: this previously yielded literal mock bytes ("encoded batch
        chunk") for every batch. It now produces real output for the
        streamable formats:

        * ``CSV`` — header row once (explicit ``columns`` or the first
          batch's keys), then sanitized rows per batch (same
          formula-injection guard as the file backends).
        * ``JSON`` — a single valid JSON array streamed incrementally.

        Args:
            data_source: Source implementing the export protocol.
            export_format: ``ExportFormat.CSV`` or ``ExportFormat.JSON``;
                other formats need a file layout and must go through
                :meth:`execute_export`.
            filters: Optional filter mapping passed to the data source.
            columns: Optional explicit column list (CSV column order,
                JSON key subset).
            batch_size: Rows fetched per data-source call.

        Yields:
            Encoded UTF-8 chunks, one or two per batch.

        Raises:
            ValueError: For formats without a streaming encoder.
        """
        import csv as csv_module
        import io

        from lexigram.admin.services.export.sanitize import sanitize_cell_value
        from lexigram.serialization import dumps_str

        if export_format not in (ExportFormat.CSV, ExportFormat.JSON):
            raise ValueError(
                f"Streaming is not supported for format {export_format.value!r}; "
                "use execute_export for file-based formats."
            )

        total = await data_source.get_export_count(filters or {})
        offset = 0
        fieldnames: list[str] = list(columns or [])
        header_sent = False
        first_json_row = True

        if export_format == ExportFormat.JSON:
            yield b"["

        while offset < total:
            batch = await data_source.get_export_data(
                filters=filters or {},
                columns=columns or [],
                limit=batch_size,
                offset=offset,
            )
            if not batch:
                break

            if export_format == ExportFormat.CSV:
                if not fieldnames:
                    fieldnames = list(batch[0].keys())
                buffer = io.StringIO()
                writer = csv_module.DictWriter(
                    buffer, fieldnames=fieldnames, extrasaction="ignore"
                )
                if not header_sent:
                    writer.writeheader()
                    header_sent = True
                for row in batch:
                    writer.writerow(
                        {
                            k: sanitize_cell_value(row.get(k))
                            for k in fieldnames
                        }
                    )
                yield buffer.getvalue().encode("utf-8")
            else:  # JSON
                for row in batch:
                    if columns:
                        row = {k: v for k, v in row.items() if k in columns}
                    prefix = b"" if first_json_row else b","
                    first_json_row = False
                    yield prefix + dumps_str(row).encode("utf-8")

            offset += len(batch)

        if export_format == ExportFormat.JSON:
            yield b"]"

    # -------------------------------------------------------------------------
    # Background Processing
    # -------------------------------------------------------------------------

    async def start_background_export(
        self,
        job_id: str,
        data_source: IExportDataSource,
    ) -> None:
        """Start export job in background."""
        task = self.task_manager.create_background_task(
            self._run_background_export(job_id, data_source),
        )
        self._background_tasks[job_id] = task

    async def _run_background_export(
        self,
        job_id: str,
        data_source: IExportDataSource,
    ) -> None:
        """Run export job in background task."""
        try:
            result = await self.execute_export(job_id, data_source)
            if result.is_err():
                logger.warning("Background export failed: %s", result.unwrap_err())
        except asyncio.CancelledError:
            pass
        except (OSError, RuntimeError, ValueError, AttributeError, LookupError):
            logger.exception("Background export job %s failed", job_id)
        except BaseException:
            # Unexpected error; log full traceback
            logger.exception(
                "Background export job %s failed unexpectedly",
                job_id,
                exc_info=True,
            )
        finally:
            self._background_tasks.pop(job_id, None)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running export job."""
        task = self._background_tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            self._job_manager.cancel_job(job_id)
            return True
        # B21b: no live background task (job still PENDING, or executing
        # synchronously via execute_export). Fall back to manager-level
        # cancellation: pending jobs become CANCELLED immediately and
        # in-flight synchronous executions observe the flag at the next
        # chunk boundary.
        return self._job_manager.cancel_job(job_id)

    # -------------------------------------------------------------------------
    # Scheduled Exports
    # -------------------------------------------------------------------------

    async def schedule_export(
        self,
        job_config: dict[str, Any],
        schedule_type: ExportSchedule,
        next_run: datetime,
    ) -> str:
        """Schedule a recurring export job."""
        # B20: this previously passed ``format=`` to create_job (whose
        # parameter is ``file_format``) — every call raised TypeError.
        file_format = job_config["format"]
        if not isinstance(file_format, ExportFormat):
            file_format = ExportFormat(file_format)
        job_id = self.create_job(
            resource_name=job_config["resource_name"],
            file_format=file_format,
            filters=job_config.get("filters", {}),
            columns=job_config.get("columns", []),
            template_name=job_config.get("template_name"),
            scheduled_for=next_run,
            schedule_type=schedule_type,
            email_recipients=job_config.get("email_recipients", []),
        )

        job = self.get_job(job_id)
        if job:
            job.metadata["schedule_config"] = job_config
            job.metadata["schedule_type"] = schedule_type.value

        return job_id

    def get_next_run_time(
        self,
        schedule_type: ExportSchedule,
        base_time: datetime,
    ) -> datetime:
        """Calculate next run time for schedule."""
        if schedule_type == ExportSchedule.HOURLY:
            return base_time + timedelta(hours=1)
        if schedule_type == ExportSchedule.DAILY:
            return base_time + timedelta(days=1)
        if schedule_type == ExportSchedule.WEEKLY:
            return base_time + timedelta(weeks=1)
        if schedule_type == ExportSchedule.MONTHLY:
            return base_time + timedelta(days=30)
        return base_time

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    async def cleanup_old_files(self) -> int:
        """Clean up old export files."""
        # Implementation depends on storage provider
        return 0

    async def cleanup_completed_jobs(self, max_age_days: int = 30) -> int:
        """Clean up old completed jobs from memory."""
        removed = self._job_manager.cleanup_completed_jobs(max_age_days)
        # Also clean up any background task references for removed jobs
        for job_id in list(self._background_tasks.keys()):
            if self._job_manager.get_job(job_id) is None:
                self._background_tasks.pop(job_id, None)
        return removed
