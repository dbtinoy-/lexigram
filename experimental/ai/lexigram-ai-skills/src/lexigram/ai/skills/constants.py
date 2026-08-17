"""Constants for lexigram-ai-skills."""

from __future__ import annotations

import importlib.metadata

try:
    __version__: str = importlib.metadata.version("lexigram-ai-skills")
except ImportError:
    __version__ = "0.0.0"


# -- Environment Variable Prefixes -------------------------------------------

ENV_PREFIX: str = "LEX_AI_SKILLS__"
ENV_NESTED_DELIMITER: str = "__"

# -- Execution Defaults ------------------------------------------------------

DEFAULT_TIMEOUT_S: float = 30.0
DEFAULT_MAX_RETRIES: int = 2
DEFAULT_MAX_CONCURRENT: int = 10

# -- Cache Defaults ----------------------------------------------------------

DEFAULT_CACHE_ENABLED: bool = True
DEFAULT_CACHE_TTL_S: int = 3600
DEFAULT_CACHE_BACKEND: str = "in_memory"

# -- Discovery Defaults ------------------------------------------------------

DEFAULT_ENFORCE_PERMISSIONS: bool = True
DEFAULT_AUTO_DISCOVER: bool = False
DEFAULT_ENABLE_BUILTIN: bool = True
DEFAULT_BUILTIN_SKILLS: tuple[str, ...] = (
    "current_datetime",
    "math_calculate",
    "text_summarize",
)

# -- Skill Path Defaults -------------------------------------------------------

DEFAULT_SKILL_DIRECTORIES: dict[str, str] = {
    "claude_code": "~/.claude/skills",
    "opencode": "~/.opencode/skills",
    "codex": "~/.codex/skills",
    "gemini_cli": "~/.gemini/skills",
    "aider": "~/.aider/skills",
    "cursor": "~/.cursor/skills",
    "copilot": "~/.github/skills",
    "windsurf": "~/.windsurf/skills",
    "custom": "./skills",
}

DEFAULT_SKILL_PATHS: tuple[str, ...] = (
    "~/.claude/skills",
    "~/.opencode/skills",
    "./skills",
)

# -- Script Execution Defaults -------------------------------------------------

DEFAULT_SCRIPT_TIMEOUT_SECONDS: int = 30
DEFAULT_ALLOWED_SCRIPT_TYPES: tuple[str, ...] = ("py", "sh", "js")
DEFAULT_MAX_FILE_SIZE_BYTES: int = 1024 * 1024  # 1MB

# -- Progressive Disclosure -----------------------------------------------------

DEFAULT_LAZY_LOAD_CONTEXT: bool = True

__all__ = [
    "DEFAULT_ALLOWED_SCRIPT_TYPES",
    "DEFAULT_AUTO_DISCOVER",
    "DEFAULT_BUILTIN_SKILLS",
    "DEFAULT_CACHE_BACKEND",
    "DEFAULT_CACHE_ENABLED",
    "DEFAULT_CACHE_TTL_S",
    "DEFAULT_ENABLE_BUILTIN",
    "DEFAULT_ENFORCE_PERMISSIONS",
    "DEFAULT_LAZY_LOAD_CONTEXT",
    "DEFAULT_MAX_CONCURRENT",
    "DEFAULT_MAX_FILE_SIZE_BYTES",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_SCRIPT_TIMEOUT_SECONDS",
    "DEFAULT_SKILL_DIRECTORIES",
    "DEFAULT_SKILL_PATHS",
    "DEFAULT_TIMEOUT_S",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "__version__",
]
