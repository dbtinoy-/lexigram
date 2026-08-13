from __future__ import annotations

from pathlib import Path

from lexigram.graphql.cli.generators.dataloader import DataLoaderGenerator


class TestDataLoaderGenerator:
    def test_name_property(self) -> None:
        gen = DataLoaderGenerator()
        assert gen.name == "dataloader"

    def test_description_property(self) -> None:
        gen = DataLoaderGenerator()
        assert "DataLoader" in gen.description

    def test_default_output_dir(self) -> None:
        gen = DataLoaderGenerator()
        assert gen.default_output_dir == "src/graphql/dataloaders"

    def test_get_name_method(self) -> None:
        gen = DataLoaderGenerator()
        assert gen.get_name() == "dataloader"

    def test_get_description_method(self) -> None:
        gen = DataLoaderGenerator()
        assert gen.get_description() == gen.description
