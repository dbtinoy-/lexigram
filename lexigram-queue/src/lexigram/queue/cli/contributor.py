"""Queue CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    DoctorCheckContribution,
    HealthCheckContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = (
    GeneratorDefinition(
        name="message_consumer",
        title="Generate Message Consumer",
        description="Generate a message consumer with queue routing",
        contributor="queue",
        generator_path="lexigram.queue.cli.generators.consumer:ConsumerGenerator",
        default_output_dir="src/consumers",
    ),
)


class QueueCliContributor:
    """CLI contributor for the lexigram-queue package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "queue"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for queue."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list[object]:
        """Return no command contributions."""
        return []

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return message broker connectivity health check."""
        return [
            HealthCheckContribution(
                name="message_broker_connection",
                description="Verify message broker connectivity",
                check_path="lexigram.queue.cli.checks:check_broker_connection",
                contributor="queue",
                category="messaging",
                timeout=10.0,
                critical=True,
            ),
        ]

    def get_doctor_checks(self) -> list[DoctorCheckContribution]:
        """Return broker configuration doctor checks."""
        return [
            DoctorCheckContribution(
                name="broker_url_configured",
                description="Check message broker URL is configured",
                check_path="lexigram.queue.cli.doctor:check_broker_configured",
                contributor="queue",
                category="messaging",
            ),
        ]

    def get_shell_context(self) -> list[object]:
        """Return no shell context contributions."""
        return []

    def get_hooks(self) -> list[object]:
        """Return no hook contributions."""
        return []


__all__ = ["QueueCliContributor"]
