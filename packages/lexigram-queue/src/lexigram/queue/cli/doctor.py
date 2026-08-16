"""CLI doctor checks for lexigram-queue."""

from __future__ import annotations

import os


def check_broker_configured() -> dict[str, object]:
    """Check message broker URL is configured.

    Returns:
        A DoctorCheckResult-compatible dict.
    """
    if os.getenv("BROKER_URL") or os.getenv("REDIS_URL") or os.getenv("RABBITMQ_URL"):
        return {"status": "ok", "message": "Message broker URL is configured"}
    return {
        "status": "warning",
        "message": "No message broker URL environment variable found",
    }
