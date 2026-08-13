from __future__ import annotations

from lexigram.contracts.cli.types import GeneratorDefinition
from lexigram.graphql.cli.contributor import GraphQLCliContributor


class TestGraphQLCliContributor:
    def test_contributor_id(self) -> None:
        contributor = GraphQLCliContributor()
        assert contributor.contributor_id == "graphql"

    def test_get_generators(self) -> None:
        contributor = GraphQLCliContributor()
        generators = contributor.get_generators()
        assert len(generators) == 1
        gen = generators[0]
        assert isinstance(gen, GeneratorDefinition)
        assert gen.name == "dataloader"
        assert gen.title == "Generate Dataloader"
        assert gen.contributor == "graphql"
        assert gen.default_output_dir == "src/graphql/dataloaders"
        assert (
            gen.generator_path
            == "lexigram.graphql.cli.generators.dataloader:DataLoaderGenerator"
        )
