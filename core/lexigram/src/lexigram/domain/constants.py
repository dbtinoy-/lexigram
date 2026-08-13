"""Constants for the domain subsystem."""

from __future__ import annotations

import importlib.metadata

__version__: str
try:
    __version__ = importlib.metadata.version("lexigram")
except ImportError:
    __version__ = "0.0.0"


# -- Environment Variable Prefix -------------------------------------------

ENV_PREFIX: str = "LEX_DOMAIN__"
ENV_NESTED_DELIMITER: str = "__"
"""Environment variable prefix for domain configuration."""

__all__ = [
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "__version__",
]
