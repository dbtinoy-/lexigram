"""Constants for AI Governance."""

from __future__ import annotations

import importlib.metadata

try:
    __version__: str = importlib.metadata.version("lexigram-ai-governance")
except ImportError:
    __version__ = "0.0.0"


# Environment variable prefix
ENV_PREFIX: str = "LEX_AI_GOVERNANCE__"
ENV_NESTED_DELIMITER: str = "__"

# Budget defaults
DEFAULT_SOFT_LIMIT_PCT: float = 0.8
"""Default soft-limit threshold as a fraction of monthly budget."""

MAX_MONTHLY_BUDGET: float = 100_000.0
"""Safety ceiling for monthly budget configuration."""

# Rate-limit defaults
DEFAULT_RPM_LIMIT: int = 60
"""Default requests-per-minute limit when RPM enforcement is enabled."""

DEFAULT_TPM_LIMIT: int = 100_000
"""Default tokens-per-minute limit when TPM enforcement is enabled."""

RPM_WINDOW_SECONDS: float = 60.0
"""Sliding window size in seconds for RPM tracking."""

# Persistence
SPEND_TTL_SECONDS: int = 32 * 24 * 3600
"""TTL for monthly spend records in persistence backends (~32 days)."""


__all__ = [
    "DEFAULT_RPM_LIMIT",
    "DEFAULT_SOFT_LIMIT_PCT",
    "DEFAULT_TPM_LIMIT",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "MAX_MONTHLY_BUDGET",
    "RPM_WINDOW_SECONDS",
    "SPEND_TTL_SECONDS",
    "__version__",
]
