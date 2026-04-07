"""Prompt constants — rendering formats, limits, and error codes."""

from __future__ import annotations

import importlib.metadata

from lexigram.ai.prompt.rendering.engine import RenderFormat

try:
    __version__: str = importlib.metadata.version("lexigram-ai-prompt")
except ImportError:
    __version__ = "0.0.0"


# -- Environment Variable Prefixes -------------------------------------------
ENV_PREFIX: str = "LEX_AI_PROMPT__"
"""Environment variable prefix for Prompt configuration."""

ENV_NESTED_DELIMITER: str = "__"
"""Delimiter for nested env var keys."""


# ---------------------------------------------------------------------------
# Rendering formats
# ---------------------------------------------------------------------------

DEFAULT_RENDER_FORMAT: RenderFormat = RenderFormat.JINJA2

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

MAX_PROMPT_VERSIONS: int = 100

MAX_RENDERED_PROMPT_LENGTH: int = 64_000

# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------

ERROR_TEMPLATE_NOT_FOUND: str = "LEX_PROMPT_001"
ERROR_VARIABLE_MISSING: str = "LEX_PROMPT_002"
ERROR_RENDER_FAILED: str = "LEX_PROMPT_003"

__all__ = [
    "DEFAULT_RENDER_FORMAT",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "ERROR_RENDER_FAILED",
    "ERROR_TEMPLATE_NOT_FOUND",
    "ERROR_VARIABLE_MISSING",
    "MAX_PROMPT_VERSIONS",
    "MAX_RENDERED_PROMPT_LENGTH",
    "__version__",
]
