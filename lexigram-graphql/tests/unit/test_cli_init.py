from __future__ import annotations

from lexigram.graphql.cli import DataLoaderGenerator, GraphQLCliContributor


class TestCLIInit:
    def test_exports_contributor(self) -> None:
        assert GraphQLCliContributor is not None

    def test_exports_dataloader_generator(self) -> None:
        assert DataLoaderGenerator is not None
