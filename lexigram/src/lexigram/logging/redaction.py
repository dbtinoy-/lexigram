"""Redaction utilities for sensitive data in logs and error output."""

from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.logging import RedactorProtocol


class NoOpRedactor:
    """Default redactor that passes data through unchanged.

    Replace with a real implementation via the DI container
    or ``set_redactor()`` for sensitive environments.
    """

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        return data

    def redact_value(self, value: Any) -> Any:
        return value


# ContextVar allows per-request redactor override (e.g., stricter
# redaction for certain tenants) while the container holds the default.
_redactor_var: contextvars.ContextVar[RedactorProtocol | None] = contextvars.ContextVar(
    "lexigram_redactor",
    default=None,
)


def get_redactor() -> RedactorProtocol:
    """Get the current redactor.

    Resolution order:
        1. Context-local override (set via ``set_redactor()``)
        2. No-op fallback (inject RedactorProtocol via DI for container resolution)

    This is intentionally synchronous — redaction is called from
    structlog processors which are sync.

    For container-based resolution, inject ``RedactorProtocol`` via DI
    in your providers.
    """
    # 1. Context-local override (per-request or per-tenant)
    context_redactor = _redactor_var.get()
    if context_redactor is not None:
        return context_redactor

    # 2. Fallback to no-op (container resolution requires DI)
    return NoOpRedactor()


def set_redactor(
    redactor: RedactorProtocol,
) -> contextvars.Token[RedactorProtocol | None]:
    """Set a context-local redactor override.

    Returns a token for resetting via ``_redactor_var.reset(token)``.

    Usage::

        token = set_redactor(StrictRedactor())
        try:
            process_sensitive_request()
        finally:
            _redactor_var.reset(token)
    """
    return _redactor_var.set(redactor)


__all__ = [
    "NoOpRedactor",
    "get_redactor",
    "set_redactor",
]
