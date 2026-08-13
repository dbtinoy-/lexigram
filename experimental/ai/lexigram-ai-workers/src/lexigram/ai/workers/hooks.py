"""Root hook payload surface for lexigram-ai-workers."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "WorkerJobCompletedHook",
    "WorkerJobStartedHook",
    "WorkerMaintenanceRunHook",
]


@dataclass(frozen=True, kw_only=True)
class WorkerJobStartedHook:
    """Payload fired when a worker starts a job."""

    job_type: str


@dataclass(frozen=True, kw_only=True)
class WorkerJobCompletedHook:
    """Payload fired when a worker finishes a job."""

    job_type: str


@dataclass(frozen=True, kw_only=True)
class WorkerMaintenanceRunHook:
    """Payload fired when a maintenance worker runs a maintenance task."""

    task_type: str
