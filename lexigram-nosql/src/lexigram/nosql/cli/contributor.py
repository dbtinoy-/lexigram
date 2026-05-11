"""NoSQL CLI contributor definitions."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.cli.contributions import HealthCheckContribution
from lexigram.contracts.cli.types import GeneratorDefinition

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = (
    GeneratorDefinition(
        name="document_repo",
        title="Generate Document Repository",
        description="Generate a NoSQL document repository",
        contributor="nosql",
        generator_path="lexigram.nosql.cli.generators.document_repository:DocumentRepositoryGenerator",
        default_output_dir="src/repositories",
        category="database",
    ),
)


class NoSqlCliContributor:
    """CLI contributor for the lexigram-nosql package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "nosql"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for NoSQL."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list[Any]:
        """Return no command contributions."""
        return []

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return NoSQL connectivity health check."""
        return [
            HealthCheckContribution(
                name="nosql_connection",
                description="Verify NoSQL/document store connectivity",
                check_path="lexigram.nosql.cli.checks:check_nosql_connection",
                contributor="nosql",
                category="database",
                timeout=10.0,
            ),
        ]

    def get_doctor_checks(self) -> list[Any]:
        """Return no doctor checks."""
        return []

    def get_shell_context(self) -> list[Any]:
        """Return no shell context contributions."""
        return []

    def get_hooks(self) -> list[Any]:
        """Return no hook contributions."""
        return []


__all__ = ["NoSqlCliContributor"]
