"""Security primitives for the Lexigram Framework.

Transport-agnostic security utilities: guards, encryption, secrets,
and input sanitization.

HTTP-specific middleware (CORS, CSRF, CSP, HSTS, security response headers)
lives in ``lexigram-web`` at ``lexigram.web.security``.
"""

from __future__ import annotations

# -- Exceptions (Task 1) -----------------------------------------------------
from lexigram.contracts.security import SecretNotFoundError as SecretNotFoundError

# -- Hashing (Task 3) --------------------------------------------------------
from lexigram.security.config import HashingConfig as HashingConfig
from lexigram.security.config import SecurityConfig as SecurityConfig

# -- Decorators (Task 2) -----------------------------------------------------
from lexigram.security.decorators import sanitize_input as sanitize_input

# -- Encryption (Task 2) -----------------------------------------------------
from lexigram.security.encryption import EncryptionService as EncryptionService
from lexigram.security.events import CsrfViolationEvent as CsrfViolationEvent
from lexigram.security.events import SecretRotatedEvent as SecretRotatedEvent
from lexigram.security.events import (
    SecurityGuardDeniedEvent as SecurityGuardDeniedEvent,
)

# -- Domain events (Task 2) --------------------------------------------------
from lexigram.security.events import ThreatDetectedEvent as ThreatDetectedEvent
from lexigram.security.exceptions import DecryptionError as DecryptionError
from lexigram.security.exceptions import EncryptionError as EncryptionError
from lexigram.security.exceptions import MiddlewareGuardError as MiddlewareGuardError
from lexigram.security.exceptions import SecretAccessError as SecretAccessError
from lexigram.security.exceptions import SecretError as SecretError
from lexigram.security.exceptions import SecurityError as SecurityError

# -- Guards (Task 2) ---------------------------------------------------------
from lexigram.security.guards import GuardChainImpl as GuardChainImpl
from lexigram.security.guards import use_guards as use_guards
from lexigram.security.hashing import PBKDF2KDF as PBKDF2KDF
from lexigram.security.hashing import Blake2bHasher as Blake2bHasher
from lexigram.security.hashing import Sha256Hasher as Sha256Hasher

# -- Hooks (Task 2) ----------------------------------------------------------
from lexigram.security.hooks import SecurityGuardBlockedHook as SecurityGuardBlockedHook
from lexigram.security.hooks import SecurityGuardPassedHook as SecurityGuardPassedHook
from lexigram.security.hooks import (
    SecurityThreatDetectedHook as SecurityThreatDetectedHook,
)

# -- Provider (Task 2) -------------------------------------------------------
from lexigram.security.provider import SecurityProvider as SecurityProvider

# -- Sanitization (Task 2) ---------------------------------------------------
from lexigram.security.sanitization import InputSanitizer as InputSanitizer
from lexigram.security.secrets import EnvSecretStore as EnvSecretStore
from lexigram.security.secrets import FileSecretStore as FileSecretStore

# -- Secrets (Task 2) --------------------------------------------------------
from lexigram.security.secrets import InMemorySecretStore as InMemorySecretStore
from lexigram.security.secrets import SecretValue as SecretValue

__all__ = [
    "PBKDF2KDF",
    "Blake2bHasher",
    "CsrfViolationEvent",
    "DecryptionError",
    "EncryptionError",
    "EncryptionService",
    "EnvSecretStore",
    "FileSecretStore",
    "GuardChainImpl",
    "HashingConfig",
    "InMemorySecretStore",
    "InputSanitizer",
    "MiddlewareGuardError",
    "SecretAccessError",
    "SecretError",
    "SecretNotFoundError",
    "SecretRotatedEvent",
    "SecretValue",
    "SecurityConfig",
    "SecurityError",
    "SecurityGuardBlockedHook",
    "SecurityGuardDeniedEvent",
    "SecurityGuardPassedHook",
    "SecurityProvider",
    "SecurityThreatDetectedHook",
    "Sha256Hasher",
    "ThreatDetectedEvent",
    "sanitize_input",
    "use_guards",
]
