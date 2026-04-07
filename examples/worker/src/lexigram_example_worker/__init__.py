"""lexigram-example-worker — background job platform reference application.

Demonstrates:
- Queue-driven campaign email sender (lexigram-queue + lexigram-tasks)
- Report generator with workflow state machine (lexigram-workflow)
- Scheduled periodic cleanup (lexigram-tasks cron scheduler)
- Dead letter queue handling for failed messages

See README.md for the full architecture walkthrough.
"""

from __future__ import annotations

from lexigram_example_worker.config import WorkerConfig
from lexigram_example_worker.module import WorkerModule

__all__ = [
    "WorkerConfig",
    "WorkerModule",
]
