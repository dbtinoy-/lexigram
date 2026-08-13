from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.graphql.dataloader.loader import DataLoaderProtocol
from lexigram.graphql.dataloader.registry import DataLoaderRegistry, dataloader


class TestDataLoaderRegistry:
    def test_init(self) -> None:
        registry = DataLoaderRegistry()
        assert registry.get_names() == []

    def test_register_and_create_loaders(self) -> None:
        registry = DataLoaderRegistry()
        mock_loader = MagicMock(spec=DataLoaderProtocol)
        registry.register("users", lambda: mock_loader)
        loaders = registry.create_loaders()
        assert "users" in loaders
        assert loaders["users"] is mock_loader

    def test_get_names(self) -> None:
        registry = DataLoaderRegistry()
        registry.register("a", lambda: MagicMock())
        registry.register("b", lambda: MagicMock())
        names = registry.get_names()
        assert sorted(names) == ["a", "b"]


class TestDataloaderDecorator:
    def test_sets_dataloader_name(self) -> None:
        @dataloader("my_loader")
        def factory() -> MagicMock:
            return MagicMock()

        assert factory._dataloader_name == "my_loader"  # type: ignore[attr-defined]
