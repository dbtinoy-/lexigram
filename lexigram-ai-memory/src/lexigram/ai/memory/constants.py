"""Constants for lexigram-ai-memory."""

from __future__ import annotations

import importlib.metadata

try:
    __version__: str = importlib.metadata.version("lexigram-ai-memory")
except ImportError:
    __version__ = "0.0.0"


# -- Environment Variable Prefixes -------------------------------------------

ENV_PREFIX: str = "LEX_AI_MEMORY__"
ENV_NESTED_DELIMITER: str = "__"

# -- Working Memory Defaults -------------------------------------------------

DEFAULT_SYSTEM_PROMPT_TOKENS: int = 512
DEFAULT_RECENT_TURNS_FRACTION: float = 0.40
DEFAULT_EPISODIC_FRACTION: float = 0.30
DEFAULT_SEMANTIC_FRACTION: float = 0.20
DEFAULT_TOOL_DESC_FRACTION: float = 0.10
DEFAULT_MAX_RECENT_TURNS: int = 20

# -- Episodic Memory Defaults ------------------------------------------------

DEFAULT_EPISODIC_TOP_K: int = 10
DEFAULT_RECENCY_WEIGHT: float = 0.3
DEFAULT_IMPORTANCE_WEIGHT: float = 0.2
DEFAULT_RELEVANCE_WEIGHT: float = 0.5
DEFAULT_EPISODIC_TTL_SECONDS: int = 0  # 0 = no expiry

# -- Semantic Memory Defaults ------------------------------------------------

DEFAULT_MIN_CONFIDENCE: float = 0.5
DEFAULT_MAX_FACTS_PER_ENTITY: int = 100

# -- Consolidation Defaults --------------------------------------------------

DEFAULT_CONSOLIDATION_INTERVAL_S: float = 3600.0
DEFAULT_CONSOLIDATION_AGE_THRESHOLD_HOURS: float = 24.0
DEFAULT_CONSOLIDATION_IMPORTANCE_PRUNE: float = 0.1
DEFAULT_CONSOLIDATION_BATCH_SIZE: int = 100

# -- Root Config Defaults ----------------------------------------------------

DEFAULT_BACKEND: str = "in_memory"
DEFAULT_TTL_SECONDS: int = 86400 * 30  # 30 days

__all__ = [
    "DEFAULT_BACKEND",
    "DEFAULT_CONSOLIDATION_AGE_THRESHOLD_HOURS",
    "DEFAULT_CONSOLIDATION_BATCH_SIZE",
    "DEFAULT_CONSOLIDATION_IMPORTANCE_PRUNE",
    "DEFAULT_CONSOLIDATION_INTERVAL_S",
    "DEFAULT_EPISODIC_FRACTION",
    "DEFAULT_EPISODIC_TOP_K",
    "DEFAULT_EPISODIC_TTL_SECONDS",
    "DEFAULT_IMPORTANCE_WEIGHT",
    "DEFAULT_MAX_FACTS_PER_ENTITY",
    "DEFAULT_MAX_RECENT_TURNS",
    "DEFAULT_MIN_CONFIDENCE",
    "DEFAULT_RECENCY_WEIGHT",
    "DEFAULT_RECENT_TURNS_FRACTION",
    "DEFAULT_RELEVANCE_WEIGHT",
    "DEFAULT_SEMANTIC_FRACTION",
    "DEFAULT_SYSTEM_PROMPT_TOKENS",
    "DEFAULT_TOOL_DESC_FRACTION",
    "DEFAULT_TTL_SECONDS",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "__version__",
]
