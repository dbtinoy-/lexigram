"""Exceptions for the security subsystem.

Re-exports ``MiddlewareGuardError`` from contracts so that callers can import
it from either ``lexigram.security`` or ``lexigram.contracts.exceptions``.
"""

from __future__ import annotations

from lexigram.contracts.exceptions import LexigramError
from lexigram.contracts.exceptions.middleware import (
    MiddlewareGuardError as MiddlewareGuardError,  # re-export
)


class SecurityError(LexigramError):
    """Base exception for all security-module errors."""

    _code: str = "LEX_ERR_SEC_006"


class SecretError(SecurityError):
    """Base exception for secret store errors."""

    _code: str = "LEX_ERR_SEC_011"


class SecretNotFoundError(SecretError):
    """Raised when a requested secret does not exist."""

    _code: str = "LEX_ERR_SEC_007"


class SecretAccessError(SecretError):
    """Raised when access to a secret is denied."""

    _code: str = "LEX_ERR_SEC_008"


class EncryptionError(SecurityError):
    """Raised when field-level encryption fails."""

    _code: str = "LEX_ERR_SEC_009"


class DecryptionError(SecurityError):
    """Raised when field-level decryption fails."""

    _code: str = "LEX_ERR_SEC_010"


__all__ = [
    "DecryptionError",
    "EncryptionError",
    "MiddlewareGuardError",
    "SecretAccessError",
    "SecretError",
    "SecretNotFoundError",
    "SecurityError",
]
