"""CLI doctor checks for lexigram-vector."""

from __future__ import annotations

import os


def check_vector_configured() -> dict[str, object]:
    """Check vector store backend is configured.

    Returns:
        A DoctorCheckResult-compatible dict.
    """
    backend = os.getenv("VECTOR_BACKEND") or os.getenv("VECTOR_STORE_BACKEND")
    if not backend:
        return {
            "status": "warning",
            "message": "VECTOR_BACKEND not set — vector store may use defaults",
        }
    return {"status": "ok", "message": f"Vector backend configured: {backend}"}
