"""Shared constants and wire models for the env-var catalog generator."""

from __future__ import annotations

from pathlib import Path
import re

REPO_ROOT = Path.cwd()

EXCLUDED_DIRS = {
    "__pycache__",
    ".egg-info",
    ".git",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "templates",
}

# Regex for direct env var access
DIRECT_ENV_RE = re.compile(
    r'(?:os\.environ\.get|os\.getenv|environ\.get|getenv)\s*\(\s*["\'](LEX_[A-Z0-9_]+)["\']'
)

# ENV_PREFIX or env_prefix constant
ENV_PREFIX_RE = re.compile(
    r'(?:ENV_PREFIX|env_prefix)\s*[=:]\s*["\'](LEX_[A-Z0-9_]+)["\']'
)

# Classes considered "config roots" — base classes for config models
CONFIG_BASE_CLASSES = {"BaseConfig", "BaseDomainConfig"}

# Documented fields that are empirically verified NOT to bind via env vars.
# Each is excluded from REF_ENV_VARS.md and .env.example; the YAML key keeps
# working, only the env override is dead.
#
# - LEX_LEXIGRAM__HEALTH__STARTUP__TIMEOUT: HealthConfig/StartupProbeConfig
#   are plain dataclasses; pydantic coerces the direct ``health`` field but
#   leaves the nested ``startup`` dict unconverted, so no env value reaches
#   StartupProbeConfig.timeout (and no runtime consumer reads the raw dict).
# - LEX_WEB__SECURITY__CSP__DIRECTIVES: CSPConfig.directives expects a dict;
#   EnvironmentConfigSource delivers a string, CSPConfig construction raises,
#   and the coercion fallback replaces the whole csp node with a raw dict.
# - LEX_AI_MCP__CONNECTORS__*: ConnectorsConfig is a plain dataclass nested
#   inside pydantic MCPConfig. The first level coerces, but each connector
#   child (slack/github/sql/...) flips to a raw dict when an env var targets
#   it — the value never reaches the typed connector config fields.
YAML_ONLY_FIELDS: set[str] = {
    "LEX_LEXIGRAM__HEALTH__STARTUP__TIMEOUT",
    "LEX_WEB__SECURITY__CSP__DIRECTIVES",
} | {
    f"LEX_AI_MCP__CONNECTORS__{leaf}"
    for leaf in (
        "FILESYSTEM__READ_ONLY",
        "FILESYSTEM__ROOT_DIR",
        "GITHUB__API_URL",
        "GITHUB__TOKEN",
        "GOOGLE_DRIVE__IMPERSONATED_EMAIL",
        "GOOGLE_DRIVE__SERVICE_ACCOUNT_JSON",
        "SLACK__BOT_TOKEN",
        "SLACK__MAX_MESSAGES",
        "SQL__ALLOWED_TABLES",
        "SQL__DSN",
        "SQL__READ_ONLY",
        "WEB_FETCH__ENABLED",
        "WEB_FETCH__MAX_CONTENT_BYTES",
        "WEB_FETCH__USER_AGENT",
        "WEB_SEARCH__API_KEY",
        "WEB_SEARCH__MAX_RESULTS",
        "WEB_SEARCH__PROVIDER",
    )
}


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
    def __init__(
        self,
        name: str,
        file_path: Path,
        bases: list[str],
        fields: list[ConfigField],
        config_section: str | None = None,
    ):
        self.name = name
        self.file_path = file_path
        self.bases = bases
        self.fields = fields
        #: Literal ``config_section`` ClassVar value, when declared.
        #: Only section-carrying roots receive env vars directly; other
        #: classes bind solely as children of such roots.
        self.config_section = config_section
