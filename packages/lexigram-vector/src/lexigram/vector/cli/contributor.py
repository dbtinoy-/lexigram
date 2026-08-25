"""Vector CLI contributor definitions."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.cli.contributions import (
    CommandContribution,
    DoctorCheckContribution,
    HealthCheckContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition

# (name, description, generator_path, output_dir) — titles derive via make()
_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "vector_collection",
        "Generate a vector collection definition with backend registration",
        "lexigram.vector.cli.generators.collection:VectorCollectionGenerator",
        "src/collections",
    ),
)

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = tuple(
    GeneratorDefinition.make(
        name,
        description=description,
        generator_path=generator_path,
        output_dir=output_dir,
        contributor="vector",
        category="vector",
    )
    for name, description, generator_path, output_dir in _SPECS
)


class VectorCliContributor:
    """CLI contributor for the lexigram-vector package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "vector"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for vector."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list[CommandContribution]:
        """Return the contributed `vector` command group."""
        return [
            CommandContribution(
                name="vector",
                help="Vector store management commands",
                app_factory_path="lexigram.vector.cli.commands:create_vector_app",
                contributor="vector",
                category="data",
                requires_app_context=True,
            ),
        ]

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return vector store health check."""
        return [
            HealthCheckContribution(
                name="vector_store_connection",
                description="Verify vector store backend connectivity",
                check_path="lexigram.vector.cli.checks:check_vector_store",
                contributor="vector",
                category="data",
                timeout=10.0,
            ),
        ]

    def get_doctor_checks(self) -> list[DoctorCheckContribution]:
        """Return vector backend configuration doctor checks."""
        return [
            DoctorCheckContribution(
                name="vector_backend_configured",
                description="Check vector store backend is configured",
                check_path="lexigram.vector.cli.doctor:check_vector_configured",
                contributor="vector",
                category="data",
            ),
        ]

    def get_shell_context(self) -> list[Any]:
        """Return no shell context contributions."""
        return []

    def get_hooks(self) -> list[Any]:
        """Return no hook contributions."""
        return []


__all__ = ["VectorCliContributor"]
