"""Resilience CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    DoctorCheckContribution,
    HealthCheckContribution,
    SchemaSetupContribution,
    ShellContextContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition


class ResilienceCliContributor:
    """CLI contributor for the lexigram-resilience package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "resilience"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return no generator definitions."""
        return []

    def get_commands(self) -> list:
        """Return no command contributions."""
        return []

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return circuit breaker health checks."""
        return [
            HealthCheckContribution(
                name="circuit_breakers_status",
                description="Check the state of all registered circuit breakers",
                check_path="lexigram.resilience.cli.checks:check_circuit_breakers",
                contributor="resilience",
                category="resilience",
                timeout=5.0,
            ),
        ]

    def get_doctor_checks(self) -> list[DoctorCheckContribution]:
        """Return resilience configuration doctor checks."""
        return [
            DoctorCheckContribution(
                name="resilience_config_valid",
                description="Validate resilience section in application.yaml",
                check_path="lexigram.resilience.cli.doctor:check_resilience_config",
                contributor="resilience",
                category="resilience",
            ),
        ]

    def get_shell_context(self) -> list[ShellContextContribution]:
        """Return resilience pipeline shell context."""
        return [
            ShellContextContribution(
                name="resilience",
                description="Resilience pipeline for interactive circuit breaker inspection",
                factory_path="lexigram.resilience.cli.shell:provide_resilience_pipeline",
                contributor="resilience",
            ),
        ]

    def get_hooks(self) -> list:
        """Return no hook contributions."""
        return []

    def get_schema_setup(self) -> list[SchemaSetupContribution]:
        """Return schema setup contributions for resilience."""
        return [
            SchemaSetupContribution(
                name="resilience.idempotency_keys",
                description="Idempotency key storage",
                setup_fn_path="lexigram.resilience.cli.schema_setup:ensure_idempotency_keys",
                contributor=self.contributor_id,
            ),
        ]


__all__ = ["ResilienceCliContributor"]
