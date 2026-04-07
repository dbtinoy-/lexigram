"""CLI doctor checks for lexigram-audit."""

from __future__ import annotations

import os


def check_hmac_key() -> dict[str, object]:
    """Check AUDIT_HMAC_KEY env var is set.

    Returns:
        A DoctorCheckResult-compatible dict.
    """
    if os.getenv("AUDIT_HMAC_KEY"):
        return {"status": "ok", "message": "AUDIT_HMAC_KEY is configured"}
    return {
        "status": "error",
        "message": "AUDIT_HMAC_KEY not set — audit log integrity cannot be verified",
    }
