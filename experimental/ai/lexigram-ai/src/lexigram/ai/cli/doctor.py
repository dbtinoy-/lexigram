"""CLI doctor checks for lexigram-ai."""

from __future__ import annotations

import os


def check_ai_api_keys() -> dict[str, object]:
    """Check that at least one AI API key is configured.

    Looks for ``OPENAI_API_KEY`` or ``ANTHROPIC_API_KEY`` environment variables.

    Returns:
        A DoctorCheckResult-compatible dict.
    """
    keys_found = [
        key for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") if os.environ.get(key)
    ]
    if keys_found:
        return {"status": "ok", "message": f"Found API keys: {', '.join(keys_found)}"}
    return {
        "status": "warning",
        "message": "No AI API keys found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.",
    }
