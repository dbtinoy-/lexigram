"""NoSQL CLI contributor definitions."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.cli.contributions import HealthCheckContribution
from lexigram.contracts.cli.types import GeneratorDefinition

# (name, description, generator_path, output_dir) — titles derive via make()
_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "document_repo",
        "Generate a NoSQL document repository",
        "lexigram.nosql.cli.generators.document_repository:DocumentRepositoryGenerator",
        "src/repositories",
    ),
)

# Titles that make() cannot derive exactly.
_TITLES: dict[str, str] = {"document_repo": "Generate Document Repository"}

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = tuple(
    GeneratorDefinition.make(
        name,
        description=description,
        generator_path=generator_path,
        output_dir=output_dir,
        contributor="nosql",
        category="database",
        title=_TITLES.get(name),
    )
    for name, description, generator_path, output_dir in _SPECS
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
