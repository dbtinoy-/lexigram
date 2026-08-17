"""AI core constants — shared defaults and limits for the AI subsystem."""

from __future__ import annotations

import importlib.metadata

# -- Version -------------------------------------------------------------------

try:
    __version__: str = importlib.metadata.version("lexigram-ai")
except ImportError:
    __version__ = "0.0.0"

# -- Environment Variable Prefixes -------------------------------------------

ENV_PREFIX: str = "LEX_AI__"
ENV_NESTED_DELIMITER: str = "__"

# Default maximum number of tokens to generate in a single completion.
DEFAULT_MAX_TOKENS: int = 4096

# Default temperature used when no per-request override is provided.
DEFAULT_TEMPERATURE: float = 0.7

# Default timeout (seconds) for a single AI inference request.
DEFAULT_REQUEST_TIMEOUT_S: int = 60

# Maximum number of messages retained in a conversation context window.
DEFAULT_CONTEXT_WINDOW_MESSAGES: int = 50

__all__ = [
    "DEFAULT_CONTEXT_WINDOW_MESSAGES",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_REQUEST_TIMEOUT_S",
    "DEFAULT_TEMPERATURE",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
]
