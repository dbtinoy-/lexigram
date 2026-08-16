"""GraphQL package CLI contributor."""

from __future__ import annotations

from lexigram.contracts.cli.types import GeneratorDefinition


class GraphQLCliContributor:
    """CLI contributor for the lexigram-graphql package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "graphql"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for GraphQL."""
        return [
            GeneratorDefinition(
                name="dataloader",
                title="Generate Dataloader",
                description="Generate a GraphQL DataLoaderProtocol to solve N+1 problems",
                contributor="graphql",
                generator_path="lexigram.graphql.cli.generators.dataloader:DataLoaderGenerator",
                default_output_dir="src/graphql/dataloaders",
            )
        ]


__all__ = ["GraphQLCliContributor"]
