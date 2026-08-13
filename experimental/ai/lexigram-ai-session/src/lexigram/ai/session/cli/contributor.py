"""CLI contributions for lexigram-ai-session."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    CommandContribution,
    HealthCheckContribution,
    HookContribution,
    SchemaSetupContribution,
    ShellContextContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition

_SCHEMA_SETUP_CONTRIBUTIONS: tuple[SchemaSetupContribution, ...] = (
    SchemaSetupContribution(
        name="ai_session.session_tables",
        description="AI session and checkpoint storage",
        setup_fn_path="lexigram.ai.session.cli.schema_setup:ensure_session_tables",
        contributor="ai-session",
    ),
)


class AiSessionCliContributor:
    """CLI contributions for lexigram-ai-session."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "ai-session"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return no generator definitions."""
        return []

    def get_commands(self) -> list[CommandContribution]:
        """Return no command contributions."""
        return []

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return no health checks."""
        return []

    def get_doctor_checks(self) -> list:
        """Return no doctor checks."""
        return []

    def get_shell_context(self) -> list[ShellContextContribution]:
        """Return no shell context contributions."""
        return []

    def get_hooks(self) -> list[HookContribution]:
        """Return no hook contributions."""
        return []

    def get_schema_setup(self) -> list[SchemaSetupContribution]:
        """Return schema setup contributions for ai-session."""
        return list(_SCHEMA_SETUP_CONTRIBUTIONS)


__all__ = ["AiSessionCliContributor"]
