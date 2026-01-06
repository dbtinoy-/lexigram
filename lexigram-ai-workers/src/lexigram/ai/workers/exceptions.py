"""Exception hierarchy for AI Workers."""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import AIError


class WorkerError(AIError):
    """Base exception for all worker-related errors."""

    _code: str = "LEX_ERR_AIWORK_001"


class DLQError(WorkerError):
    """Raised when a Dead Letter Queue operation fails."""

    _code: str = "LEX_ERR_AIWORK_002"


class MaintenanceError(WorkerError):
    """Raised when a maintenance task operation fails."""

    _code: str = "LEX_ERR_AIWORK_003"


__all__ = [
    "DLQError",
    "MaintenanceError",
    "WorkerError",
]
