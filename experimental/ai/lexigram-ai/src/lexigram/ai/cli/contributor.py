"""AI CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    CommandContribution,
    DoctorCheckContribution,
    HealthCheckContribution,
    ShellContextContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition


class AICliContributor:
    """CLI contributor for the lexigram-ai package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "ai"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return no generator definitions."""
        return []

    def get_commands(self) -> list[CommandContribution]:
        """Return the contributed `ai` command group."""
        return [
            CommandContribution(
                name="ai",
                help="AI subsystem management commands",
                app_factory_path="lexigram.ai.cli.commands:create_ai_app",
                contributor="ai",
                category="ai",
                requires_app_context=True,
            ),
        ]

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return AI provider and subsystem health checks."""
        return [
            HealthCheckContribution(
                name="ai_llm_provider",
                description="Check that an LLM provider is reachable",
                check_path="lexigram.ai.cli.checks:check_llm_provider",
                contributor="ai",
                category="ai",
                timeout=15.0,
            ),
            HealthCheckContribution(
                name="ai_subsystem_discovery",
                description="Check that AI subsystems are discoverable via entry points",
                check_path="lexigram.ai.cli.checks:check_subsystem_discovery",
                contributor="ai",
                category="ai",
                timeout=5.0,
            ),
        ]

    def get_doctor_checks(self) -> list[DoctorCheckContribution]:
        """Return AI API key doctor checks."""
        return [
            DoctorCheckContribution(
                name="ai_api_keys_configured",
                description="Check that at least one AI API key is configured",
                check_path="lexigram.ai.cli.doctor:check_ai_api_keys",
                contributor="ai",
                category="ai",
            ),
        ]

    def get_shell_context(self) -> list[ShellContextContribution]:
        """Return AI client shell context."""
        return [
            ShellContextContribution(
                name="ai",
                description="AI client for interactive AI exploration",
                factory_path="lexigram.ai.cli.shell:provide_ai_client",
                contributor="ai",
            ),
        ]

    def get_hooks(self) -> list:
        """Return no hook contributions."""
        return []


__all__ = ["AICliContributor"]
