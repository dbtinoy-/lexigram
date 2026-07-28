"""Vector CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    CommandContribution,
    DoctorCheckContribution,
    HealthCheckContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = (
    GeneratorDefinition(
        name="vector_collection",
        title="Generate Vector Collection",
        description="Generate a vector collection definition with backend registration",
        contributor="vector",
        generator_path="lexigram.vector.cli.generators.collection:VectorCollectionGenerator",
        default_output_dir="src/collections",
        category="vector",
    ),
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

    def get_shell_context(self) -> list:
        """Return no shell context contributions."""
        return []

    def get_hooks(self) -> list:
        """Return no hook contributions."""
        return []


__all__ = ["VectorCliContributor"]
