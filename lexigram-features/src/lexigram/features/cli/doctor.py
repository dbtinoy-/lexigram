"""CLI doctor checks for lexigram-features."""

from __future__ import annotations


def check_features_config() -> dict[str, object]:
    """Validate features section in application.yaml.

    Returns:
        A DoctorCheckResult-compatible dict.
    """
    return {
        "status": "ok",
        "message": "Features configuration check not yet implemented",
    }
