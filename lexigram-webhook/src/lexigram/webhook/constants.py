"""Package-level constants for lexigram-webhook."""

from __future__ import annotations

from enum import StrEnum
import importlib.metadata

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

try:
    __version__: str = importlib.metadata.version("lexigram-webhook")
except ImportError:
    __version__ = "0.0.0"

# ---------------------------------------------------------------------------
# Environment variable constants
# ---------------------------------------------------------------------------

ENV_PREFIX: str = "LEX_WEBHOOK__"
ENV_NESTED_DELIMITER: str = "__"

# ---------------------------------------------------------------------------
# Default config values
# ---------------------------------------------------------------------------

DEFAULT_STORE_BACKEND: str = "memory"
DEFAULT_RETRY_MAX_ATTEMPTS: int = 5
DEFAULT_RETRY_BASE_DELAY: float = 1.0
DEFAULT_RETRY_MAX_DELAY: float = 60.0
DEFAULT_RETRY_BACKOFF_FACTOR: float = 2.0
DEFAULT_SECRET_LENGTH: int = 32
DEFAULT_SECRET_ROTATION_GRACE_HOURS: int = 24
DEFAULT_DELIVERY_TIMEOUT_SECONDS: float = 30.0
DEFAULT_DISABLE_AFTER_CONSECUTIVE_FAILURES: int = 50
DEFAULT_FAILURE_WINDOW_HOURS: int = 24
DEFAULT_SIGNATURE_ALGORITHM: str = "sha256"
DEFAULT_DELIVERY_LOG_RETENTION_DAYS: int = 30
DEFAULT_SIGNATURE_HEADER: str = "X-Webhook-Signature"
DEFAULT_EVENT_TYPE_HEADER: str = "X-Webhook-Event-Type"
DEFAULT_EVENT_ID_HEADER: str = "X-Webhook-Event-ID"
DEFAULT_TIMESTAMP_HEADER: str = "X-Webhook-Timestamp"

# ---------------------------------------------------------------------------
# StrEnum namespaces
# ---------------------------------------------------------------------------


class StoreBackend(StrEnum):
    """Supported webhook store backend identifiers."""

    SQL = "sql"
    MEMORY = "memory"


class DeliveryStatus(StrEnum):
    """Delivery lifecycle statuses for webhook dispatch attempts."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class SignatureAlgorithm(StrEnum):
    """HMAC signature algorithms supported for webhook signing."""

    SHA256 = "sha256"
    SHA512 = "sha512"


# ---------------------------------------------------------------------------
# __all__
# ---------------------------------------------------------------------------

__all__ = [
    "DEFAULT_DELIVERY_LOG_RETENTION_DAYS",
    "DEFAULT_DELIVERY_TIMEOUT_SECONDS",
    "DEFAULT_DISABLE_AFTER_CONSECUTIVE_FAILURES",
    "DEFAULT_EVENT_ID_HEADER",
    "DEFAULT_EVENT_TYPE_HEADER",
    "DEFAULT_FAILURE_WINDOW_HOURS",
    "DEFAULT_RETRY_BACKOFF_FACTOR",
    "DEFAULT_RETRY_BASE_DELAY",
    "DEFAULT_RETRY_MAX_ATTEMPTS",
    "DEFAULT_RETRY_MAX_DELAY",
    "DEFAULT_SECRET_LENGTH",
    "DEFAULT_SECRET_ROTATION_GRACE_HOURS",
    "DEFAULT_SIGNATURE_ALGORITHM",
    "DEFAULT_SIGNATURE_HEADER",
    "DEFAULT_STORE_BACKEND",
    "DEFAULT_TIMESTAMP_HEADER",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "DeliveryStatus",
    "SignatureAlgorithm",
    "StoreBackend",
    "__version__",
]
