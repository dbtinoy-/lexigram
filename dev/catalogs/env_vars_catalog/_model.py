"""Shared constants and wire models for the env-var catalog generator."""

from __future__ import annotations

from pathlib import Path
import re

REPO_ROOT = Path.cwd()

EXCLUDED_DIRS = {"__pycache__", ".egg-info", ".git", "node_modules", ".mypy_cache", ".ruff_cache", ".pytest_cache", "templates"}

# Regex for direct env var access
DIRECT_ENV_RE = re.compile(
    r'(?:os\.environ\.get|os\.getenv|environ\.get|getenv)\s*\(\s*["\'](LEX_[A-Z0-9_]+)["\']'
)

# ENV_PREFIX or env_prefix constant
ENV_PREFIX_RE = re.compile(r'(?:ENV_PREFIX|env_prefix)\s*[=:]\s*["\'](LEX_[A-Z0-9_]+)["\']')

# Classes considered "config roots" — base classes for config models
CONFIG_BASE_CLASSES = {"BaseConfig", "BaseDomainConfig"}


def _md(val: str) -> str:
    """Escape pipe characters that would break markdown table columns."""
    return val.replace("|", "\\|")


class ConfigField:
    def __init__(
        self,
        name: str,
        type_str: str,
        default: str = "—",
        is_config: bool = False,
        config_class: str | None = None,
        description: str = "",
    ):
        self.name = name
        self.type_str = type_str
        self.default = default
        self.is_config = is_config
        self.config_class = config_class
        self.description = description


class ConfigClass:
    def __init__(self, name: str, file_path: Path, bases: list[str], fields: list[ConfigField]):
        self.name = name
        self.file_path = file_path
        self.bases = bases
        self.fields = fields
