"""Tests for admin export types."""

from datetime import datetime, timezone

import pytest

from lexigram.admin.services.export.scheduler import (
    ExportFormat,
    ExportJob,
    ExportSchedule,
    ExportStatus,
    ExportTemplate,
)


class TestExportFormat:
    """Tests for ExportFormat enum."""

    def test_export_format_values(self) -> None:
        """Test ExportFormat enum values."""
        assert ExportFormat.CSV.value == "csv"
        assert ExportFormat.EXCEL.value == "xlsx"
        assert ExportFormat.JSON.value == "json"
        assert ExportFormat.PDF.value == "pdf"

    def test_export_format_members(self) -> None:
        """Test ExportFormat has expected members."""
        members = list(ExportFormat)
        assert len(members) == 4


class TestExportStatus:
    """Tests for ExportStatus enum."""

    def test_export_status_values(self) -> None:
        """Test ExportStatus enum values."""
        assert ExportStatus.PENDING.value == "pending"
        assert ExportStatus.PROCESSING.value == "processing"
        assert ExportStatus.COMPLETED.value == "completed"
        assert ExportStatus.FAILED.value == "failed"
        assert ExportStatus.CANCELLED.value == "cancelled"

    def test_export_status_members(self) -> None:
        """Test ExportStatus has expected members."""
        members = list(ExportStatus)
        assert len(members) == 5


class TestExportSchedule:
    """Tests for ExportSchedule enum."""

    def test_export_schedule_values(self) -> None:
        """Test ExportSchedule enum values."""
        assert ExportSchedule.IMMEDIATE.value == "immediate"
        assert ExportSchedule.HOURLY.value == "hourly"
        assert ExportSchedule.DAILY.value == "daily"
        assert ExportSchedule.WEEKLY.value == "weekly"
        assert ExportSchedule.MONTHLY.value == "monthly"

    def test_export_schedule_members(self) -> None:
        """Test ExportSchedule has expected members."""
        members = list(ExportSchedule)
        assert len(members) == 5


class TestExportTemplate:
    """Tests for ExportTemplate dataclass."""

    def test_export_template_creation(self) -> None:
        """Test creating ExportTemplate."""
        template = ExportTemplate(
            name="User Export",
            format=ExportFormat.CSV,
            columns=[],
        )
        assert template.name == "User Export"
        assert template.format == ExportFormat.CSV
        assert template.columns == []
        assert template.filters == {}
        assert template.sort_order == "asc"
        assert template.include_charts is False

    def test_export_template_with_values(self) -> None:
        """Test ExportTemplate with values."""
        template = ExportTemplate(
            name="Sales Report",
            format=ExportFormat.EXCEL,
            columns=[],
            description="Monthly sales report",
            filters={"status": "completed"},
            sort_by="date",
            sort_order="desc",
            include_charts=True,
        )
        assert template.description == "Monthly sales report"
        assert template.filters == {"status": "completed"}
        assert template.sort_by == "date"
        assert template.sort_order == "desc"
        assert template.include_charts is True


class TestExportJob:
    """Tests for ExportJob dataclass."""

    def test_export_job_defaults(self) -> None:
        """Test ExportJob default values."""
        job = ExportJob(
            job_id="job-123",
            resource_name="users",
            format=ExportFormat.CSV,
        )
        assert job.job_id == "job-123"
        assert job.resource_name == "users"
        assert job.format == ExportFormat.CSV
        assert job.status == ExportStatus.PENDING
        assert job.progress == 0.0
        assert job.total_records == 0
        assert job.filters == {}
        assert job.columns == []

    def test_export_job_with_progress(self) -> None:
        """Test ExportJob with progress."""
        job = ExportJob(
            job_id="job-123",
            resource_name="users",
            format=ExportFormat.CSV,
            status=ExportStatus.PROCESSING,
            progress=50.0,
            total_records=1000,
            processed_records=500,
        )
        assert job.status == ExportStatus.PROCESSING
        assert job.progress == 50.0
        assert job.total_records == 1000
        assert job.processed_records == 500

    def test_export_job_with_schedule(self) -> None:
        """Test ExportJob with schedule."""
        scheduled = datetime.now(timezone.utc)
        job = ExportJob(
            job_id="job-123",
            resource_name="users",
            format=ExportFormat.CSV,
            schedule_type=ExportSchedule.DAILY,
            scheduled_for=scheduled,
            email_recipients=["admin@example.com"],
        )
        assert job.schedule_type == ExportSchedule.DAILY
        assert job.scheduled_for == scheduled
        assert job.email_recipients == ["admin@example.com"]
