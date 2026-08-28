"""Queue worker demo — one Lexigram topic with an automatic consumer.

The public surface is intentionally small: a standalone application factory,
its typed config, and the lifecycle provider that starts the consumer.
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
