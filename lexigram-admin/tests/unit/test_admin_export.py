"""Tests for admin export scheduler types."""

import pytest

from lexigram.admin.services.export.scheduler import (
    ExportFormat,
    ExportSchedule,
    ExportStatus,
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
