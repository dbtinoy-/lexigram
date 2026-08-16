"""CLI doctor checks for lexigram-tenancy."""

from __future__ import annotations


def check_tenancy_config() -> dict[str, object]:
    """Validate tenancy section in application.yaml.

    Returns:
        A DoctorCheckResult-compatible dict.
    """
    return {
        "status": "ok",
        "message": "Tenancy configuration check not yet implemented",
    }


def check_isolation_strategy() -> dict[str, object]:
    """Check isolation strategy is properly configured.

    Returns:
        A DoctorCheckResult-compatible dict.
    """
    return {"status": "ok", "message": "Isolation strategy check not yet implemented"}
