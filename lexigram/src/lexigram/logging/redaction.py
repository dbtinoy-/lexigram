"""Redaction utilities for sensitive data in logs and error output."""

from __future__ import annotations

import contextvars
from typing import Any

from lexigram.contracts.core.logging import RedactorProtocol

_DEFAULT_FIELD_DENYLIST: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "session_id",
        "session_token",
        "access_token",
        "refresh_token",
        "private_key",
        "client_secret",
    }
)


class NoOpRedactor:
    """Default redactor that passes data through unchanged.

    Replace with a real implementation via the DI container
    or ``set_redactor()`` for sensitive environments.
    """

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        return data

    def redact_value(self, value: Any) -> Any:
        return value


class DefaultRedactor:
    """Redact log fields whose names match the default field denylist.

    Masking is key-based only (no free-text pattern matching):
    top-level and nested dict keys matching a denylisted field name,
    case-insensitively, are replaced with the ``"<redacted>"`` sentinel.
    Non-denylisted values pass through unchanged, including nested
    containers which are recursed.

    Args:
        field_denylist: Field names to mask, matched case-insensitively.
            Defaults to ``_DEFAULT_FIELD_DENYLIST``.
    """

    def __init__(
        self,
        field_denylist: frozenset[str] | tuple[str, ...] | None = None,
    ) -> None:
        if field_denylist is None:
            field_denylist = _DEFAULT_FIELD_DENYLIST
        self._field_denylist = frozenset(f.lower() for f in field_denylist)

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Return ``data`` with denylisted keys masked, recursing containers.

        Args:
            data: The mapping to redact.

        Returns:
            A new mapping with matching keys set to ``"<redacted>"``.
        """
        return {
            key: (
                "<redacted>"
                if key.lower() in self._field_denylist
                else self.redact_value(value)
            )
            for key, value in data.items()
        }

    def redact_value(self, value: Any) -> Any:
        """Redact a value, recursing nested dicts and lists.

        Args:
            value: The value to redact.

        Returns:
            The value with nested denylisted keys masked; non-container
            values pass through unchanged.
        """
        if isinstance(value, dict):
            return self.redact_dict(value)
        if isinstance(value, list):
            return [self.redact_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.redact_value(item) for item in value)
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
    "DefaultRedactor",
    "NoOpRedactor",
    "get_redactor",
    "set_redactor",
]
