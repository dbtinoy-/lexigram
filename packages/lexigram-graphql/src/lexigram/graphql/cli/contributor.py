"""GraphQL package CLI contributor."""

from __future__ import annotations

from lexigram.contracts.cli.types import GeneratorDefinition

# (name, description, generator_path, output_dir) — titles derive via make()
_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "dataloader",
        "Generate a GraphQL DataLoaderProtocol to solve N+1 problems",
        "lexigram.graphql.cli.generators.dataloader:DataLoaderGenerator",
        "src/schema/dataloaders",
    ),
)

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = tuple(
    GeneratorDefinition.make(
        name,
        description=description,
        generator_path=generator_path,
        output_dir=output_dir,
        contributor="graphql",
    )
    for name, description, generator_path, output_dir in _SPECS
)


class GraphQLCliContributor:
    """CLI contributor for the lexigram-graphql package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "graphql"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for GraphQL."""
        return list(_GENERATOR_DEFINITIONS)


__all__ = ["GraphQLCliContributor"]
