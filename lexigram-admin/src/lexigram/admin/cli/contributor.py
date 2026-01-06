"""Admin package CLI contributor."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import CommandContribution
from lexigram.contracts.cli.types import GeneratorDefinition


class AdminCliContributor:
    """CLI contributor for the lexigram-admin package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "admin"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for admin."""
        return [
            GeneratorDefinition(
                name="admin_action",
                title="Generate Admin Action",
                description="Generate a custom admin action",
                contributor="admin",
                generator_path="lexigram.admin.cli.generators.admin_action:AdminActionGenerator",
                default_output_dir="src/admin/actions",
            ),
            GeneratorDefinition(
                name="admin_resource",
                title="Generate Admin Resource",
                description="Generate an admin resource for the admin panel",
                contributor="admin",
                generator_path="lexigram.admin.cli.generators.admin_resource:AdminResourceGenerator",
                default_output_dir="src/admin/resources",
            ),
        ]

    def get_commands(self) -> list[CommandContribution]:
        """Return CLI command contributions for admin."""
        return [
            CommandContribution(
                name="search",
                help="Search index management commands (reindex, etc.)",
                app_factory_path="lexigram.admin.cli.commands.search:create_app",
                contributor="admin",
                category="admin",
            ),
        ]


__all__ = ["AdminCliContributor"]
