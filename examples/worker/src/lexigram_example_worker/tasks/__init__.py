"""Task handler exports."""

from __future__ import annotations

from lexigram_example_worker.tasks.cleanup_old_records import CleanupOldRecordsHandler
from lexigram_example_worker.tasks.generate_report import GenerateReportHandler
from lexigram_example_worker.tasks.send_email_batch import (
    BatchResult,
    EmailBatchPayload,
    SendEmailBatchHandler,
)

__all__ = [
    "BatchResult",
    "CleanupOldRecordsHandler",
    "EmailBatchPayload",
    "GenerateReportHandler",
    "SendEmailBatchHandler",
]
