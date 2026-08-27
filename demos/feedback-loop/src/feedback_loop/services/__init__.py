"""Business-logic services.

Convention: re-exports make imports ergonomic.  Services are wired
via DI providers (``di/provider.py``) and resolved through the container.
"""

from __future__ import annotations

from feedback_loop.services.loop_service import (
    Answer,
    LoopService,
    RunSummary,
    StatsSnapshot,
)

__all__ = [
    "Answer",
    "LoopService",
    "RunSummary",
    "StatsSnapshot",
]
