"""Report domain model with status enum.

:class:`Report` is the aggregate root for the report-generation use-case.
Its :class:`ReportStatus` drives the workflow state machine defined in
:mod:`lexigram_example_worker.workflows.report_workflow`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class ReportStatus(StrEnum):
    """Lifecycle states for a generated report.

    The canonical transition sequence is::

        QUEUED → PROCESSING → DONE
                           ↘ FAILED
    """

    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Report:
    """Aggregate root for a background-generated CSV report.

    Attributes:
        id: Unique report identifier (UUID4).
        name: Human-readable report name.
        status: Current lifecycle status.
        row_count: Number of data rows written (populated after completion).
        error_message: Failure description when ``status == FAILED``.
        created_at: UTC timestamp when the report was requested.
        completed_at: UTC timestamp when generation finished (or failed).
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    status: ReportStatus = ReportStatus.QUEUED
    row_count: int = 0
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    # ------------------------------------------------------------------
    # Mutating helpers — each method corresponds to a workflow transition
    # ------------------------------------------------------------------

    def mark_processing(self) -> None:
        """Transition report to the ``PROCESSING`` state.

        Raises:
            ValueError: If the current status is not ``QUEUED``.
        """
        if self.status != ReportStatus.QUEUED:
            raise ValueError(
                f"Cannot start processing from status {self.status!r}."
            )
        self.status = ReportStatus.PROCESSING

    def mark_done(self, row_count: int) -> None:
        """Transition report to the ``DONE`` state.

        Args:
            row_count: Number of rows written to the output file.

        Raises:
            ValueError: If the current status is not ``PROCESSING``.
        """
        if self.status != ReportStatus.PROCESSING:
            raise ValueError(
                f"Cannot complete report from status {self.status!r}."
            )
        self.status = ReportStatus.DONE
        self.row_count = row_count
        self.completed_at = datetime.now(UTC)

    def mark_failed(self, error_message: str) -> None:
        """Transition report to the ``FAILED`` state.

        Args:
            error_message: Human-readable description of the failure.

        Raises:
            ValueError: If the current status is not ``PROCESSING``.
        """
        if self.status != ReportStatus.PROCESSING:
            raise ValueError(
                f"Cannot fail report from status {self.status!r}."
            )
        self.status = ReportStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now(UTC)


__all__ = ["Report", "ReportStatus"]
