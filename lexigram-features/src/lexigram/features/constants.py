"""Constants for the feature-flag subsystem.

Defines typed defaults and environment variable prefixes used across the
feature-flag system.  Configuration models reference these to avoid
hard-coding values in multiple places.
"""

from __future__ import annotations

import importlib.metadata

# -- Version -------------------------------------------------------------------

try:
    __version__: str = importlib.metadata.version("lexigram-features")
except ImportError:
    __version__ = "0.0.0"

# -- Environment Variable Prefixes -------------------------------------------

ENV_PREFIX: str = "LEX_FLAG_"
"""Default prefix for environment variable flag definitions."""

ENV_NESTED_DELIMITER: str = "__"
"""Nested delimiter for environment variable configuration."""


# -- Default Configuration Values --------------------------------------------

DEFAULT_CACHE_TTL: int = 300
"""Default TTL in seconds for cached flag evaluations (5 minutes)."""

DEFAULT_ENABLED: bool = False
"""Default evaluation result when a flag is not found in the provider."""

__all__ = [
    "DEFAULT_CACHE_TTL",
    "DEFAULT_ENABLED",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
]
