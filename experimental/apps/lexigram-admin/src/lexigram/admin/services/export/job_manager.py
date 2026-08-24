"""ExportJobManager — extracted job CRUD and lifecycle management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
import uuid

from lexigram.admin.services.export.scheduler import (
    ExportFormat,
    ExportJob,
    ExportSchedule,
    ExportStatus,
    ExportTemplate,
)


class ExportJobManager:
    """Manages export job lifecycle: creation, retrieval, cancellation, cleanup.

    Extracted from ExportService to separate job state management from
    export execution and backend orchestration.
    """

    def __init__(self) -> None:
        self._templates: dict[str, ExportTemplate] = {}
        self._jobs: dict[str, ExportJob] = {}

    def register_template(self, template: ExportTemplate) -> None:
        """Register an export template."""
        self._templates[template.name] = template

    def get_template(self, name: str) -> ExportTemplate | None:
        """Get a registered template."""
        return self._templates.get(name)

    def list_templates(self) -> list[ExportTemplate]:
        """List all registered templates."""
        return list(self._templates.values())

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
        """Create a new export job and return its ID."""
        job_id = str(uuid.uuid4())
        job = ExportJob(
            job_id=job_id,
            resource_name=resource_name,
            format=file_format,
            filters=filters or {},
            columns=columns or [],
            template_name=template_name,
            user_id=user_id,
            scheduled_for=scheduled_for,
            schedule_type=schedule_type,
            email_recipients=email_recipients or [],
        )
        self._jobs[job_id] = job
        return job_id

    def get_job(self, job_id: str) -> ExportJob | None:
        """Get export job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        user_id: Any | None = None,
        status: ExportStatus | None = None,
        limit: int = 50,
    ) -> list[ExportJob]:
        """List export jobs with optional filtering."""
        jobs = list(self._jobs.values())

        if user_id is not None:
            jobs = [j for j in jobs if j.user_id == user_id]

        if status is not None:
            jobs = [j for j in jobs if j.status == status]

        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running export job by marking it cancelled.

        Returns True if the job was found and cancelled, False otherwise.
        Actual task cancellation is handled by the caller.
        """
        job = self.get_job(job_id)
        if job is None:
            return False
        if job.status not in (ExportStatus.PENDING, ExportStatus.PROCESSING):
            return False
        job.status = ExportStatus.CANCELLED
        job.completed_at = datetime.now(UTC)
        return True

    def cleanup_completed_jobs(self, max_age_days: int = 30) -> int:
        """Remove completed/failed/cancelled jobs older than max_age_days."""
        cutoff_date = datetime.now(UTC) - timedelta(days=max_age_days)
        jobs_to_remove: list[str] = []

        for job_id, job in self._jobs.items():
            if (
                job.status
                in (
                    ExportStatus.COMPLETED,
                    ExportStatus.FAILED,
                    ExportStatus.CANCELLED,
                )
                and job.completed_at
            ):
                job_time = (
                    job.completed_at
                    if job.completed_at.tzinfo is not None
                    else job.completed_at.replace(tzinfo=UTC)
                )
                if job_time < cutoff_date:
                    jobs_to_remove.append(job_id)

        for job_id in jobs_to_remove:
            del self._jobs[job_id]

        return len(jobs_to_remove)
