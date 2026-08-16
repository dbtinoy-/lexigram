"""Task models and data structures."""

from __future__ import annotations

from lexigram.contracts.infra.tasks import JobStatus
from lexigram.tasks.models.job import JobProtocol, JobResult

__all__ = ["JobProtocol", "JobResult", "JobStatus"]
