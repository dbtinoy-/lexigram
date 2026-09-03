"""User-facing error humanization.

Single place that turns framework error strings into text safe to show a
person. Framework errors are chained and machine-annotated::

    [LEX_ERR_ADMIN_010] Verification email could not be delivered:
    [LEX_ERR_ADMIN_009] All 1 recipient(s) failed: ...
      → Fix: Configure a mailer backend ...
      → See: https://docs.lexigram.dev/reference/errors/LEX_ERR_ADMIN_010

None of that belongs in a query string, flash message, or rendered page:
error codes and docs links are for logs (where the full chain is always
recorded before humanizing). This module strips every ``[LEX_ERR_*]``
token and every ``→ Fix:`` / ``→ See:`` annotation — anywhere in the
string, not just at the start — and collapses the remainder to a single
line.

Policy (docs/09-01-2026/02-improvement-roadmap.md, R4): controllers must
route ALL user-facing error text through :func:`humanize_error` (or use a
fixed message), and must log the raw error first.
"""

from __future__ import annotations

import re

# Error-code tokens, wherever they appear (chains embed them mid-string).
_LEX_ERR_TOKEN_RE = re.compile(r"\[LEX_ERR_[A-Z0-9_]+\]\s*")

# "→ Fix: ..." / "→ See: ..." annotations. They run to the end of their
# line; chained messages may contain several.
_ANNOTATION_RE = re.compile(r"→\s*(?:Fix|See):[^\n]*")

_WHITESPACE_RE = re.compile(r"\s+")


def humanize_error(message: str, *, fallback: str = "") -> str:
    """Strip framework annotations from an error message for user display.

    Args:
        message: Raw error text, possibly a chained framework error with
            ``[LEX_ERR_*]`` codes and ``→ Fix:`` / ``→ See:`` lines.
        fallback: Returned when the cleaned message ends up empty (e.g. the
            original consisted only of annotations).

    Returns:
        A single-line message with all framework annotations removed, or
        ``fallback`` if nothing human-readable remains.
    """
    if not message:
        return fallback
    cleaned = _LEX_ERR_TOKEN_RE.sub("", message)
    cleaned = _ANNOTATION_RE.sub("", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned or fallback


__all__ = ["humanize_error"]
