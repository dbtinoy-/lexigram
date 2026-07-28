"""Security contracts for Lexigram Framework.

Provides protocols and types for security-related concerns, including
secret management, guards, input sanitization, and response headers.
"""

from __future__ import annotations

from lexigram.contracts.exceptions.components import (
    SecretNotFoundError,
)
from lexigram.contracts.exceptions.security import (
    CORSViolationError,
    GuardDeniedError,
    InputSanitizationError,
    SecretAccessError,
    SecurityError,
)
from lexigram.contracts.security.protocols import (
    CORSProtocol,
    CSPProtocol,
    CSRFProtocol,
    EncryptionProtocol,
    GuardChainProtocol,
    HasherProtocol,
    InputSanitizerProtocol,
    KeyDerivationProtocol,
    SecurityHeadersProtocol,
)
from lexigram.contracts.security.rotation import SecretRotationPolicy
from lexigram.contracts.security.secrets import (
    SecretStoreProtocol,
)
from lexigram.contracts.security.stores import AsyncSecretStoreProtocol

__all__ = [
    "AsyncSecretStoreProtocol",
    "CORSProtocol",
    "CORSViolationError",
    "CSPProtocol",
    "CSRFProtocol",
    "EncryptionProtocol",
    "GuardChainProtocol",
    "GuardDeniedError",
    "HasherProtocol",
    "InputSanitizationError",
    "InputSanitizerProtocol",
    "KeyDerivationProtocol",
    "SecretAccessError",
    "SecretNotFoundError",
    "SecretRotationPolicy",
    "SecretStoreProtocol",
    "SecurityError",
    "SecurityHeadersProtocol",
]
