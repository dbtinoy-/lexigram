"""DefaultPiiRedactor — field-name and pattern-based PII redaction."""

from __future__ import annotations

from collections.abc import Iterable
import re
from typing import Any

_EMAIL_RE = re.compile(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+")
_PHONE_RE = re.compile(r"\+?\d[\d\-\s().]{7,}\d")
_PATTERN_REGISTRY: dict[str, re.Pattern[str]] = {
    "email": _EMAIL_RE,
    "phone": _PHONE_RE,
}


class DefaultPiiRedactor:
    """Default PII redactor combining field-name denylist and pattern matching.

    Args:
        field_denylist: Set of field names whose values are always
            replaced with ``"<redacted>"`` (checked recursively).
        patterns: Named patterns from ``{"email", "phone"}`` to match
            against string values at any nesting depth.
    """

    def __init__(
        self,
        field_denylist: Iterable[str] = (),
        patterns: Iterable[str] = (),
    ) -> None:
        self._fields = set(field_denylist)
        self._compiled = [
            _PATTERN_REGISTRY[p] for p in patterns if p in _PATTERN_REGISTRY
        ]

    def redact(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a redacted copy of *payload*."""
        return self._redact_value(payload)

    def _redact_value(self, v: Any) -> Any:
        if isinstance(v, dict):
            return {
                k: ("<redacted>" if k in self._fields else self._redact_value(val))
                for k, val in v.items()
            }
        if isinstance(v, list):
            return [self._redact_value(x) for x in v]
        if isinstance(v, str):
            for pat in self._compiled:
                v = pat.sub("<redacted>", v)
            return v
        return v


__all__ = ["DefaultPiiRedactor"]
