"""Queue worker demo — message queue with in-memory backend.

Convention followed: **Package exports** — ``__init__.py`` re-exports
the public API surface without defining logic.

Exports:

- ``create_app`` — composition root for the application
- ``QueueWorkerConfig`` — demo configuration model
- ``QueueWorkerProvider`` — DI provider for queue worker services
"""

from __future__ import annotations

from queueworker.app import create_app
from queueworker.config import QueueWorkerConfig
from queueworker.di.provider import QueueWorkerProvider

__all__ = [
    "QueueWorkerConfig",
    "QueueWorkerProvider",
    "create_app",
]
