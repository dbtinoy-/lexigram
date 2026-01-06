"""Task and job queue enums for Lexigram Framework."""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    """JobProtocol execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


__all__ = ["JobStatus"]
