"""Package-level constants for lexigram-audit."""

from __future__ import annotations

from enum import StrEnum
import importlib.metadata

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

try:
    __version__: str = importlib.metadata.version("lexigram-audit")
except ImportError:
    __version__ = "0.0.0"

# ---------------------------------------------------------------------------
# Environment variable constants
# ---------------------------------------------------------------------------

ENV_PREFIX: str = "LEX_AUDIT__"
ENV_NESTED_DELIMITER: str = "__"

# ---------------------------------------------------------------------------
# Default config values
# ---------------------------------------------------------------------------

DEFAULT_STORE_BACKEND: str = "sql"
DEFAULT_TABLE_NAME: str = "audit_log"
DEFAULT_VERIFICATION_SCHEDULE: str = "0 * * * *"
DEFAULT_VERIFICATION_BATCH_SIZE: int = 100

# ---------------------------------------------------------------------------
# StrEnum namespaces
# ---------------------------------------------------------------------------


class StoreBackend(StrEnum):
    """Supported audit store backend identifiers."""

    SQL = "sql"
    MEMORY = "memory"


class AuditSeverity(StrEnum):
    """Severity levels for audit log entries."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditOutcome(StrEnum):
    """Outcome values for audit log entries."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# __all__
# ---------------------------------------------------------------------------

__all__ = [
    "DEFAULT_STORE_BACKEND",
    "DEFAULT_TABLE_NAME",
    "DEFAULT_VERIFICATION_BATCH_SIZE",
    "DEFAULT_VERIFICATION_SCHEDULE",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "AuditOutcome",
    "AuditSeverity",
    "StoreBackend",
    "__version__",
]
