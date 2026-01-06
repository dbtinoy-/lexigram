"""Background job queue for admin import/export operations.

Wraps import and export services to run large operations asynchronously with
real-time progress tracking via :class:`ProgressTrackerProtocol`.

Usage::

    from lexigram.admin.services.background_jobs import BackgroundJobService
    from lexigram.tasks.progress import InMemoryProgressTracker

    tracker = InMemoryProgressTracker()
    job_svc = BackgroundJobService(
        progress_tracker=tracker,
        import_service=importer,
        export_service=exporter,
    )

    # Enqueue a CSV import — returns immediately with a job_id
    job_id = await job_svc.enqueue_import(
        resource_type="user",
        file_content=csv_bytes,
        file_format="csv",
        actor_id="admin-user",
    )

    # Poll progress
    status = await job_svc.get_status(job_id)
    # → {"job_id": "...", "percent": 42, "status": "running", ...}

    # Enqueue CSV/JSON export
    job_id = await job_svc.enqueue_export(
        resource_type="user",
        export_format="csv",
        filters={"active": True},
        actor_id="admin-user",
    )
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from lexigram.contracts.infra.tasks.progress import ProgressTrackerProtocol
from lexigram.logging import get_logger
from lexigram.serialization import dumps_str

logger = get_logger(__name__)


class JobNotFoundError(KeyError):
    """Raised when a job_id is not found in the queue."""

    _code: str = "LEX_ERR_ADMIN_028"


@dataclass
class BackgroundJob:
    """Runtime record of a background operation.

    Attributes:
        job_id: Unique identifier.
        job_type: ``"import"`` or ``"export"``.
        resource_type: Admin resource name.
        actor_id: Who triggered the job.
        status: ``"pending"``, ``"running"``, ``"completed"``, or ``"failed"``.
        percent: 0-100 completion percentage.
        created_at: UTC timestamp.
        completed_at: UTC timestamp (when finished).
        result: Final result data (on completion).
        error: Error message (on failure).
        metadata: Extra context (format, filename, etc.).
    """

    job_id: str
    job_type: str
    resource_type: str
    actor_id: str
    status: str = "pending"
    percent: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dict for SSE/polling endpoints."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "resource_type": self.resource_type,
            "actor_id": self.actor_id,
            "status": self.status,
            "percent": self.percent,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


class BackgroundJobService:
    """Manages background import/export jobs with progress tracking.

    All heavy work runs in a background :func:`asyncio.Task`.  Progress is
    broadcast via :class:`ProgressTrackerProtocol` so subscribers can receive
    live updates and callers can poll :meth:`get_status` without blocking.

    Args:
        progress_tracker: Optional :class:`ProgressTrackerProtocol` instance.
            When provided, jobs broadcast live updates so the admin progress
            UI works automatically.
        import_service: Optional ``AdminImportService`` instance.
        export_service: Optional ``ExportService`` instance.
        max_retained_jobs: Maximum number of completed/failed jobs to keep
            in memory before oldest are evicted.
    """

    def __init__(
        self,
        progress_tracker: ProgressTrackerProtocol | None = None,
        import_service: Any = None,
        export_service: Any = None,
        max_retained_jobs: int = 200,
    ) -> None:
        self._progress = progress_tracker
        self._importer = import_service
        self._exporter = export_service
        self._max_retained = max_retained_jobs
        self._jobs: dict[str, BackgroundJob] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._counter = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _new_id(self, prefix: str) -> str:
        self._counter += 1
        ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        return f"{prefix}-{ts}-{self._counter}"

    def _register(self, job: BackgroundJob) -> None:
        self._jobs[job.job_id] = job
        self._evict_old()

    def _evict_old(self) -> None:
        done = [j for j in self._jobs.values() if j.status in ("completed", "failed")]
        if len(done) > self._max_retained:
            for old in sorted(done, key=lambda j: j.created_at)[
                : len(done) - self._max_retained
            ]:
                del self._jobs[old.job_id]

    async def _update(
        self, job: BackgroundJob, percent: int, status: str = "running"
    ) -> None:
        job.percent = percent
        job.status = status
        if self._progress:
            try:
                await self._progress.update(
                    job.job_id, percent, 100, f"{status} ({percent}%)"
                )
            except (TimeoutError, OSError, RuntimeError):
                pass

    async def _finish(self, job: BackgroundJob, result: dict[str, Any]) -> None:
        job.status = "completed"
        job.percent = 100
        job.result = result
        job.completed_at = datetime.now(UTC)
        if self._progress:
            try:
                await self._progress.complete(job.job_id, dumps_str(result))
            except (TimeoutError, OSError, RuntimeError):
                pass

    async def _fail(self, job: BackgroundJob, error: str) -> None:
        job.status = "failed"
        job.error = error
        job.completed_at = datetime.now(UTC)
        if self._progress:
            try:
                await self._progress.fail(job.job_id, error)
            except (TimeoutError, OSError, RuntimeError):
                pass

    # ------------------------------------------------------------------
    # Enqueue import
    # ------------------------------------------------------------------

    async def enqueue_import(
        self,
        resource_type: str,
        file_content: bytes,
        *,
        file_format: str = "csv",
        actor_id: str = "system",
        filename: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        """Enqueue a background import job.

        Args:
            resource_type: Resource name (e.g. ``"user"``).
            file_content: Raw file bytes.
            file_format: ``"csv"`` or ``"json"``.
            actor_id: Principal who triggered the import.
            filename: Optional original filename (stored in metadata).
            options: Extra options forwarded to the import service.

        Returns:
            JobProtocol ID for polling via :meth:`get_status`.
        """
        job_id = self._new_id("import")
        job = BackgroundJob(
            job_id=job_id,
            job_type="import",
            resource_type=resource_type,
            actor_id=actor_id,
            metadata={"file_format": file_format, "filename": filename},
        )
        self._register(job)

        task = asyncio.create_task(
            self._run_import(job, file_content, file_format, options or {})
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        self._tasks[job_id] = task
        task.add_done_callback(lambda _t: self._tasks.pop(job_id, None))
        logger.info("Enqueued import job %s for resource '%s'", job_id, resource_type)
        return job_id

    async def _run_import(
        self,
        job: BackgroundJob,
        file_content: bytes,
        file_format: str,
        options: dict[str, Any],
    ) -> None:
        try:
            await self._update(job, 5)

            if self._importer is None:
                # Simulate when no service wired (useful for testing)
                await asyncio.sleep(0)
                await self._finish(
                    job, {"rows_imported": 0, "note": "no import service configured"}
                )
                return

            await self._update(job, 20)
            import_job = await self._importer.parse(
                file_content, file_format=file_format, **options
            )
            await self._update(job, 60)

            result = await self._importer.commit(import_job)
            await self._update(job, 95)

            if result.is_ok():
                r = result.unwrap()
                await self._finish(
                    job,
                    {
                        "rows_imported": getattr(r, "imported", 0),
                        "rows_skipped": getattr(r, "skipped", 0),
                        "rows_failed": getattr(r, "failed", 0),
                    },
                )
            else:
                err = result.unwrap_err()
                await self._fail(job, str(err))

        except Exception as exc:  # noqa: BLE001 — top-level task runner must capture all failures to mark job as failed
            logger.exception("Import job %s failed: %s", job.job_id, exc)
            await self._fail(job, str(exc))

    # ------------------------------------------------------------------
    # Enqueue export
    # ------------------------------------------------------------------

    async def enqueue_export(
        self,
        resource_type: str,
        *,
        export_format: str = "csv",
        actor_id: str = "system",
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
    ) -> str:
        """Enqueue a background export job.

        Args:
            resource_type: Resource name.
            export_format: ``"csv"``, ``"json"``, or ``"xlsx"``.
            actor_id: Principal who triggered the export.
            filters: Optional filters to apply to the query.
            columns: Optional list of columns to include.

        Returns:
            JobProtocol ID for polling via :meth:`get_status`.
        """
        job_id = self._new_id("export")
        job = BackgroundJob(
            job_id=job_id,
            job_type="export",
            resource_type=resource_type,
            actor_id=actor_id,
            metadata={"export_format": export_format, "columns": columns or []},
        )
        self._register(job)

        task = asyncio.create_task(
            self._run_export(job, export_format, filters or {}, columns or [])
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        self._tasks[job_id] = task
        task.add_done_callback(lambda _t: self._tasks.pop(job_id, None))
        logger.info("Enqueued export job %s for resource '%s'", job_id, resource_type)
        return job_id

    async def _run_export(
        self,
        job: BackgroundJob,
        export_format: str,
        filters: dict[str, Any],
        columns: list[str],
    ) -> None:
        try:
            await self._update(job, 10)

            if self._exporter is None:
                await asyncio.sleep(0)
                await self._finish(
                    job, {"rows_exported": 0, "note": "no export service configured"}
                )
                return

            await self._update(job, 30)
            output = await self._exporter.export(
                job.resource_type,
                format=export_format,
                filters=filters,
                columns=columns,
            )
            await self._update(job, 90)
            await self._finish(
                job,
                {
                    "rows_exported": getattr(output, "row_count", 0),
                    "download_url": getattr(output, "download_url", ""),
                    "export_format": export_format,
                },
            )

        except Exception as exc:  # noqa: BLE001 — top-level task runner must capture all failures to mark job as failed
            logger.exception("Export job %s failed: %s", job.job_id, exc)
            await self._fail(job, str(exc))

    # ------------------------------------------------------------------
    # Status / query
    # ------------------------------------------------------------------

    async def get_status(self, job_id: str) -> dict[str, Any] | None:
        """Return current job status as a JSON-safe dict.

        Args:
            job_id: JobProtocol identifier returned by :meth:`enqueue_import` /
                :meth:`enqueue_export`.

        Returns:
            Status dict or ``None`` if job_id not found.
        """
        job = self._jobs.get(job_id)
        return job.to_dict() if job else None

    async def get_job(self, job_id: str) -> BackgroundJob | None:
        """Return the :class:`BackgroundJob` for *job_id*, or ``None``."""
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        *,
        resource_type: str | None = None,
        job_type: str | None = None,
        status: str | None = None,
    ) -> list[BackgroundJob]:
        """Return jobs matching the given filters.

        Args:
            resource_type: Filter by resource type.
            job_type: ``"import"`` or ``"export"``.
            status: Filter by status string.
        """
        jobs = list(self._jobs.values())
        if resource_type:
            jobs = [j for j in jobs if j.resource_type == resource_type]
        if job_type:
            jobs = [j for j in jobs if j.job_type == job_type]
        if status:
            jobs = [j for j in jobs if j.status == status]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    async def cancel(self, job_id: str) -> bool:
        """Cancel a pending or running job.

        Args:
            job_id: JobProtocol to cancel.

        Returns:
            ``True`` if the job was cancelled, ``False`` if not found or
            already finished.
        """
        job = self._jobs.get(job_id)
        if job is None or job.status in ("completed", "failed"):
            return False

        task = self._tasks.get(job_id)
        if task and not task.done():
            task.cancel()

        job.status = "failed"
        job.error = "Cancelled by user"
        job.completed_at = datetime.now(UTC)
        return True


__all__ = [
    "BackgroundJob",
    "BackgroundJobService",
    "JobNotFoundError",
]
