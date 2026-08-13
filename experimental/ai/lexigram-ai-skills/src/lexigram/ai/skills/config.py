"""Configuration for the lexigram-ai-skills package."""

from __future__ import annotations

from typing import ClassVar, cast

from lexigram.ai.skills import constants as const
from lexigram.config.base import BaseConfig
from lexigram.validation import ConfigDict, Field

ENV_PREFIX: str = const.ENV_PREFIX


class SkillsConfig(BaseConfig):
    """Configuration for the skills subsystem.

    Controls execution defaults, caching behaviour, permission enforcement,
    auto-discovery settings, and which built-in skills are enabled.

    Attributes:
        name: Logical name used for DI registration keys.
        default_timeout_seconds: Default execution timeout per skill.
        max_retries: Default maximum retry attempts for skill execution.
        max_concurrent_executions: Semaphore cap on concurrent executions.
        cache_enabled: Whether result caching is globally enabled.
        cache_ttl_seconds: Default TTL for cached skill results.
        cache_backend: Which cache backend to use (``in_memory``, ``cache``).
        enforce_permissions: Whether permission checks are enforced.
        auto_discover: Whether to auto-scan packages on boot.
        scan_packages: Fully-qualified package names to scan for skills.
        enable_builtin: Whether built-in skills are registered on boot.
        builtin_skills: Names of built-in skills to register.
    """

    config_section: ClassVar[str] = "ai_skills"

    model_config: ClassVar[ConfigDict] = cast(
        "ConfigDict",
        {
            "env_prefix": const.ENV_PREFIX,
            "env_nested_delimiter": const.ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    name: str = Field(
        default="ai-skills", description="Logical name used for DI registration keys"
    )

    # Execution
    default_timeout_seconds: float = Field(
        default=const.DEFAULT_TIMEOUT_S,
        gt=0.0,
        description="Default execution timeout per skill (seconds)",
    )
    max_retries: int = Field(
        default=const.DEFAULT_MAX_RETRIES,
        ge=0,
        description="Default maximum retry attempts for skill execution",
    )
    max_concurrent_executions: int = Field(
        default=const.DEFAULT_MAX_CONCURRENT,
        ge=1,
        description="Semaphore cap on concurrent skill executions",
    )

    # Caching
    cache_enabled: bool = Field(
        default=const.DEFAULT_CACHE_ENABLED,
        description="Whether result caching is globally enabled",
    )
    cache_ttl_seconds: int = Field(
        default=const.DEFAULT_CACHE_TTL_S,
        ge=1,
        description="Default TTL for cached skill results (seconds)",
    )
    cache_backend: str = Field(
        default=const.DEFAULT_CACHE_BACKEND,
        description="Which cache backend to use (in_memory, cache)",
    )

    # Permissions
    enforce_permissions: bool = Field(
        default=const.DEFAULT_ENFORCE_PERMISSIONS,
        description="Whether permission checks are enforced",
    )

    # Discovery
    auto_discover: bool = Field(
        default=const.DEFAULT_AUTO_DISCOVER,
        description="Whether to auto-scan packages for skills on boot",
    )
    scan_packages: list[str] = Field(
        default_factory=list,
        description="Fully-qualified package names to scan for skills",
    )

    # Built-in skills
    enable_builtin: bool = Field(
        default=const.DEFAULT_ENABLE_BUILTIN,
        description="Whether built-in skills are registered on boot",
    )
    builtin_skills: list[str] = Field(
        default_factory=lambda: list(const.DEFAULT_BUILTIN_SKILLS),
        description="Names of built-in skills to register",
    )

    # --- Skill Sources (SKILL.md, .mdc, etc.) ---
    enable_skill_sources: bool = Field(
        default=True,
        description="Whether to scan for external skill sources on boot",
    )
    skill_paths: list[str] = Field(
        default_factory=lambda: list(const.DEFAULT_SKILL_PATHS),
        description="Paths to scan for skills (SKILL.md folders)",
    )
    enabled_directories: list[str] = Field(
        default_factory=lambda: list(const.DEFAULT_SKILL_DIRECTORIES.keys()),
        description="Which skill directories to enable (claude_code, opencode, cursor, etc.)",
    )

    # --- Script Execution ---
    script_timeout_seconds: int = Field(
        default=const.DEFAULT_SCRIPT_TIMEOUT_SECONDS,
        gt=0,
        description="Timeout for skill script execution (seconds)",
    )
    allowed_script_types: list[str] = Field(
        default_factory=lambda: list(const.DEFAULT_ALLOWED_SCRIPT_TYPES),
        description="Allowed script types (py, sh, js)",
    )

    # --- Progressive Disclosure ---
    lazy_load_context: bool = Field(
        default=const.DEFAULT_LAZY_LOAD_CONTEXT,
        description="Whether to lazily load skill context files",
    )


__all__ = ["ENV_PREFIX", "SkillsConfig"]
