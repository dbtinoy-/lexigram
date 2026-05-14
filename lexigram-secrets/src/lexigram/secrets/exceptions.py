"""Secret vault exceptions.

Exception Hierarchy::

    LexigramError (from lexigram.exceptions)
    └── SecretsError
        ├── SecretNotFoundError
        ├── SecretAccessError
        ├── SecretRotationError
        ├── SecretBackendError
        └── SecretConfigError
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts.exceptions import InfrastructureError, LexigramError

__all__ = [
    "SecretAccessError",
    "SecretBackendError",
    "SecretBackendUnavailableError",
    "SecretConfigError",
    "SecretNotFoundError",
    "SecretRotationError",
    "SecretsError",
]


class SecretsError(LexigramError):
    """Base exception for all secrets-domain errors."""

    _code: str = "LEX_ERR_SECRET_001"


class SecretNotFoundError(SecretsError):
    """Raised when a requested secret does not exist."""

    _code: str = "LEX_ERR_SECRET_002"

    def __init__(self, key: str, **kwargs: Any) -> None:
        super().__init__(f"Secret not found: {key!r}", **kwargs)
        self.key = key


class SecretAccessError(SecretsError):
    """Raised when access to a secret is denied."""

    _code: str = "LEX_ERR_SECRET_003"


class SecretRotationError(SecretsError):
    """Raised when automatic rotation of a secret fails."""

    _code: str = "LEX_ERR_SECRET_004"

    def __init__(self, key: str, reason: str = "", **kwargs: Any) -> None:
        super().__init__(f"Rotation failed for {key!r}: {reason}", **kwargs)
        self.key = key
        self.reason = reason


class SecretBackendError(SecretsError):
    """Raised when the underlying secret backend (e.g. Vault) fails."""

    _code: str = "LEX_ERR_SECRET_005"


class SecretBackendUnavailableError(InfrastructureError):
    """Backend auth/network/permission failure — distinct from secret-not-found."""

    _code: str = "LEX_ERR_SECRET_007"


class SecretConfigError(SecretsError):
    """Raised when secrets subsystem configuration is invalid."""

    _code: str = "LEX_ERR_SECRET_006"
