"""HTTP package CLI contributor."""

from __future__ import annotations

from lexigram.contracts.cli.types import GeneratorDefinition


class HttpCliContributor:
    """CLI contributor for the lexigram-http package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "http"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for HTTP."""
        return [
            GeneratorDefinition(
                name="api_client",
                title="Generate Api Client",
                description="Generate an external API client",
                contributor="http",
                generator_path="lexigram.http.cli.generators.api_client:APIClientGenerator",
                default_output_dir="src/clients",
            )
        ]


__all__ = ["HttpCliContributor"]
