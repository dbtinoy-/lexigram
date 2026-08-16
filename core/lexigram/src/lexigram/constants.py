"""Package-level constants for the lexigram framework.

Single source of truth for version metadata, stability markers, and
framework-wide configuration settings.
"""

from __future__ import annotations

import importlib.metadata
import sys

try:
    __version__ = importlib.metadata.version("lexigram")
except ImportError:
    __version__ = "0.0.0"


# ---------------------------------------------------------------------------
# Configuration Environment Variable Prefix
# ---------------------------------------------------------------------------

ENV_PREFIX: str = "LEX__"
"""Environment variable prefix for Lexigram framework configuration."""

# ---------------------------------------------------------------------------
# Python version guard
# ---------------------------------------------------------------------------

MIN_PYTHON_VERSION: tuple[int, int] = (3, 11)

if sys.version_info < MIN_PYTHON_VERSION:
    _major, _minor = MIN_PYTHON_VERSION
    raise RuntimeError(
        f"lexigram requires Python {_major}.{_minor}+, "
        f"but running Python {sys.version_info.major}.{sys.version_info.minor}"
    )

# ---------------------------------------------------------------------------
# Feature flags (graceful transitions during 0.x)
# ---------------------------------------------------------------------------

FEATURES: dict[str, bool] = {
    "result_chaining": True,  # Result.map() / and_then() async chaining
    "lazy_imports": True,  # __getattr__ for fast startup
    "strict_injection": True,  # Require explicit DI (no service locator)
    "module_visibility": False,  # Module export visibility enforcement (future)
}

__all__ = ["FEATURES", "MIN_PYTHON_VERSION"]
