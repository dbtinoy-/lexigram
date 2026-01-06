"""Search CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import HealthCheckContribution
from lexigram.contracts.cli.types import GeneratorDefinition

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = (
    GeneratorDefinition(
        name="search_index",
        title="Generate Search Index",
        description="Generate a search index with backend registration",
        contributor="search",
        generator_path="lexigram.search.cli.generators.search_index:SearchIndexGenerator",
        default_output_dir="src/search",
    ),
)


class SearchCliContributor:
    """CLI contributor for the lexigram-search package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "search"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for search."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list:
        """Return no command contributions."""
        return []

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return search backend connectivity health check."""
        return [
            HealthCheckContribution(
                name="search_backend_connection",
                description="Verify search backend connectivity",
                check_path="lexigram.search.cli.checks:check_search_backend",
                contributor="search",
                category="search",
                timeout=10.0,
            ),
        ]

    def get_doctor_checks(self) -> list:
        """Return no doctor checks."""
        return []

    def get_shell_context(self) -> list:
        """Return no shell context contributions."""
        return []

    def get_hooks(self) -> list:
        """Return no hook contributions."""
        return []


__all__ = ["SearchCliContributor"]
