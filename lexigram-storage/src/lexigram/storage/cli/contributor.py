"""Storage CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    DoctorCheckContribution,
    HealthCheckContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = (
    GeneratorDefinition(
        name="storage_driver",
        title="Generate Storage Driver",
        description="Generate a file storage backend driver",
        contributor="storage",
        generator_path="lexigram.storage.cli.generators.storage_driver:StorageDriverGenerator",
        default_output_dir="src/storage/backends",
    ),
)


class StorageCliContributor:
    """CLI contributor for the lexigram-storage package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "storage"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for storage."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list:
        """Return no command contributions."""
        return []

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return storage backend connectivity health check."""
        return [
            HealthCheckContribution(
                name="storage_backend_connection",
                description="Verify file storage backend connectivity",
                check_path="lexigram.storage.cli.checks:check_storage_backend",
                contributor="storage",
                category="storage",
                timeout=10.0,
            ),
        ]

    def get_doctor_checks(self) -> list[DoctorCheckContribution]:
        """Return storage configuration doctor checks."""
        return [
            DoctorCheckContribution(
                name="storage_configured",
                description="Check storage backend is configured in application.yaml",
                check_path="lexigram.storage.cli.doctor:check_storage_configured",
                contributor="storage",
                category="storage",
            ),
        ]

    def get_shell_context(self) -> list:
        """Return no shell context contributions."""
        return []

    def get_hooks(self) -> list:
        """Return no hook contributions."""
        return []


__all__ = ["StorageCliContributor"]
