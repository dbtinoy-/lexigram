"""Export job models and scheduling types for Lexigram Admin."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ExportFormat(StrEnum):
    """Supported export formats."""

    CSV = "csv"
    EXCEL = "xlsx"
    JSON = "json"
    PDF = "pdf"


class ExportStatus(StrEnum):
    """Export job status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportSchedule(StrEnum):
    """Export scheduling options."""

    IMMEDIATE = "immediate"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class ExportTemplate:
    """Export template configuration."""

    name: str
    format: ExportFormat
    columns: list[Any]  # ExportColumn - defined elsewhere
    description: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    sort_by: str | None = None
    sort_order: str = "asc"
    include_charts: bool = False
    chart_configs: list[dict[str, Any]] = field(default_factory=list)
    styling: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportJob:
    """Export job configuration and status."""

    job_id: str
    resource_name: str
    format: ExportFormat
    filters: dict[str, Any] = field(default_factory=dict)
    columns: list[str] = field(default_factory=list)
    template_name: str | None = None
    status: ExportStatus = ExportStatus.PENDING
    progress: float = 0.0
    total_records: int = 0
    processed_records: int = 0
    file_path: str | None = None
    file_size: int = 0
    download_url: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    user_id: Any | None = None
    scheduled_for: datetime | None = None
    schedule_type: ExportSchedule = ExportSchedule.IMMEDIATE
    email_recipients: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "ExportFormat",
    "ExportJob",
    "ExportSchedule",
    "ExportStatus",
    "ExportTemplate",
]
