"""Constants for the logging subsystem."""

from __future__ import annotations

import importlib.metadata

__version__: str
try:
    __version__ = importlib.metadata.version("lexigram")
except ImportError:
    __version__ = "0.0.0"


# -- Log Level Names ---------------------------------------------------------

CRITICAL: str = "critical"
DEBUG: str = "debug"
ERROR: str = "error"
INFO: str = "info"
WARNING: str = "warning"

__all__ = [
    "CRITICAL",
    "DEBUG",
    "ERROR",
    "INFO",
    "WARNING",
    "__version__",
]
