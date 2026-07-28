"""Constants for lexigram-ai-session."""

from __future__ import annotations

import importlib.metadata

try:
    __version__: str = importlib.metadata.version("lexigram-ai-session")
except ImportError:
    __version__ = "0.0.0"


# -- Environment Variable Prefixes -------------------------------------------

ENV_PREFIX: str = "LEX_AI_SESSION__"
ENV_NESTED_DELIMITER: str = "__"

# -- Session Defaults --------------------------------------------------------

DEFAULT_SESSION_TTL_S: int = 86400  # 24 hours
DEFAULT_CLEANUP_INTERVAL_S: int = 600  # 10 minutes
DEFAULT_MAX_TURNS: int = 1000
DEFAULT_MAX_SESSIONS_PER_USER: int = 100
DEFAULT_AUTO_CHECKPOINT_INTERVAL: int = 10
DEFAULT_MAX_CHECKPOINTS: int = 50
DEFAULT_MAX_BRANCHES: int = 10
DEFAULT_MAX_AGENTS: int = 10
DEFAULT_TURN_STRATEGY: str = "round_robin"
DEFAULT_BACKEND: str = "in_memory"

# -- HTTP Defaults -----------------------------------------------------------

DEFAULT_COOKIE_NAME: str = "lexigram_session"
DEFAULT_HEADER_NAME: str = "X-Session-ID"

# -- Behaviour Defaults ------------------------------------------------------

DEFAULT_CONSOLIDATE_ON_CLOSE: bool = True

__all__ = [
    "DEFAULT_AUTO_CHECKPOINT_INTERVAL",
    "DEFAULT_BACKEND",
    "DEFAULT_CLEANUP_INTERVAL_S",
    "DEFAULT_CONSOLIDATE_ON_CLOSE",
    "DEFAULT_COOKIE_NAME",
    "DEFAULT_HEADER_NAME",
    "DEFAULT_MAX_AGENTS",
    "DEFAULT_MAX_BRANCHES",
    "DEFAULT_MAX_CHECKPOINTS",
    "DEFAULT_MAX_SESSIONS_PER_USER",
    "DEFAULT_MAX_TURNS",
    "DEFAULT_SESSION_TTL_S",
    "DEFAULT_TURN_STRATEGY",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "__version__",
]
