"""Configuration for the lexigram-ai-session package."""

from __future__ import annotations

from typing import ClassVar, cast

from lexigram.ai.session import constants as const
from lexigram.config import (
    BaseConfig,
)
from lexigram.contracts.core.config import ConfigIssue, Environment
from lexigram.validation import ConfigDict, Field


class SessionConfig(BaseConfig):
    """Configuration for the session management subsystem.

    Controls lifecycle timeouts, checkpointing thresholds, multi-agent
    settings, backend selection, and web middleware behaviour.
    """

    config_section: ClassVar[str] = "ai_session"

    model_config: ClassVar[ConfigDict] = cast(
        "ConfigDict",
        {
            "env_prefix": const.ENV_PREFIX,
            "env_nested_delimiter": const.ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    enabled: bool = Field(default=True, description="Enable the AI session subsystem")

    name: str = Field(
        default="ai-session", description="Logical name used for DI registration keys"
    )
    env: Environment | None = Field(None, description="Deployment environment")

    # Lifecycle
    default_system_prompt: str | None = Field(
        default=None,
        description="System prompt injected into every new session",
    )
    session_ttl: int = Field(
        default=const.DEFAULT_SESSION_TTL_S,
        ge=0,
        description="Maximum age of a session in seconds (0 to disable)",
    )
    cleanup_interval_s: int = Field(
        default=const.DEFAULT_CLEANUP_INTERVAL_S,
        ge=1,
        description="How often the cleanup scheduler sweeps for expired sessions",
    )
    max_turns_per_session: int = Field(
        default=const.DEFAULT_MAX_TURNS,
        ge=1,
        description="Hard cap on turns before the session is closed",
    )
    max_sessions_per_user: int = Field(
        default=const.DEFAULT_MAX_SESSIONS_PER_USER,
        ge=1,
        description="Maximum concurrent sessions per user",
    )

    # Checkpointing
    auto_checkpoint_interval: int | None = Field(
        default=const.DEFAULT_AUTO_CHECKPOINT_INTERVAL,
        description="Checkpoint every N turns; None to disable",
    )
    max_checkpoints_per_session: int = Field(
        default=const.DEFAULT_MAX_CHECKPOINTS,
        ge=1,
        description="Maximum retained checkpoints per session",
    )

    # Branching
    max_branches_per_session: int = Field(
        default=const.DEFAULT_MAX_BRANCHES,
        ge=1,
        description="Maximum forked branches per session",
    )

    # Multi-agent
    max_agents_per_group: int = Field(
        default=const.DEFAULT_MAX_AGENTS,
        ge=1,
        description="Maximum agents in a multi-agent group session",
    )
    default_turn_strategy: str = Field(
        default=const.DEFAULT_TURN_STRATEGY,
        description="Default turn-selection strategy (round_robin, priority, llm_directed)",
    )

    # Persistence
    backend: str = Field(
        default=const.DEFAULT_BACKEND,
        description="Persistence backend (in_memory, cache, database)",
    )

    # Web middleware
    cookie_name: str | None = Field(
        default=const.DEFAULT_COOKIE_NAME,
        description="Cookie name for web session ID; None disables cookies",
    )
    header_name: str = Field(
        default=const.DEFAULT_HEADER_NAME,
        description="HTTP header name for session ID pass-through",
    )

    # Integration
    consolidate_on_close: bool = Field(
        default=const.DEFAULT_CONSOLIDATE_ON_CLOSE,
        description="Whether to trigger memory consolidation on session close",
    )

    def validate_for_environment(
        self, env: Environment | None = None
    ) -> list[ConfigIssue]:
        """Check config is safe for the target environment."""
        issues: list[ConfigIssue] = []
        if env == Environment.PRODUCTION:
            if self.backend == "in_memory":
                issues.append(
                    ConfigIssue(
                        severity="error",
                        field="backend",
                        message="In-memory session backend used in production",
                        suggestion="Use 'cache' or 'database' for persistent sessions",
                    )
                )
        return issues


__all__ = ["SessionConfig"]
