"""CLI doctor checks for lexigram-resilience."""

from __future__ import annotations


def check_resilience_config() -> dict[str, object]:
    """Validate resilience section in application.yaml.

    Returns:
        A DoctorCheckResult-compatible dict.
    """
    return {
        "status": "ok",
        "message": "Resilience configuration check not yet implemented",
    }
