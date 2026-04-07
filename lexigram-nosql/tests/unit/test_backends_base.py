from __future__ import annotations

import pytest

from lexigram.nosql.backends.base import AbstractDocumentStore


class TestAbstractDocumentStore:
    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError, match="abstract"):
            AbstractDocumentStore(database_name="test")  # type: ignore[abstract]

    def test_init_sets_attributes(self) -> None:
        class ConcreteStore(AbstractDocumentStore):
            async def connect(self) -> None:
                pass
            async def disconnect(self) -> None:
                pass
            def session(self) -> None:
                pass
            async def list_collections(self) -> list[str]:
                return []
            async def drop_collection(self, name: str) -> None:
                pass
            async def health_check(self, timeout: float = 5.0) -> None:
                pass
            def _create_collection(self, name: str) -> None:
                pass

        store = ConcreteStore(database_name="mydb")
        assert store.database_name == "mydb"
        assert store.is_connected() is False

    def test_collection_caches_by_name(self) -> None:
        class ConcreteStore(AbstractDocumentStore):
            async def connect(self) -> None:
                self._connected = True
            async def disconnect(self) -> None:
                pass
            def session(self) -> None:
                pass
            async def list_collections(self) -> list[str]:
                return []
            async def drop_collection(self, name: str) -> None:
                pass
            async def health_check(self, timeout: float = 5.0) -> None:
                pass
            def _create_collection(self, name: str) -> None:
                from unittest.mock import MagicMock
                return MagicMock()

        store = ConcreteStore(database_name="mydb")
        col_a = store.collection("items")
        col_b = store.collection("items")
        assert col_a is col_b

    def test_collection_different_names_are_distinct(self) -> None:
        class ConcreteStore(AbstractDocumentStore):
            call_count = 0
            async def connect(self) -> None:
                self._connected = True
            async def disconnect(self) -> None:
                pass
            def session(self) -> None:
                pass
            async def list_collections(self) -> list[str]:
                return []
            async def drop_collection(self, name: str) -> None:
                pass
            async def health_check(self, timeout: float = 5.0) -> None:
                pass
            def _create_collection(self, name: str) -> None:
                from unittest.mock import MagicMock
                self.call_count += 1
                return MagicMock()

        store = ConcreteStore(database_name="mydb")
        col_a = store.collection("a")
        col_b = store.collection("b")
        assert col_a is not col_b
        assert store.call_count == 2

    def test_database_name_property(self) -> None:
        class ConcreteStore(AbstractDocumentStore):
            async def connect(self) -> None:
                pass
            async def disconnect(self) -> None:
                pass
            def session(self) -> None:
                pass
            async def list_collections(self) -> list[str]:
                return []
            async def drop_collection(self, name: str) -> None:
                pass
            async def health_check(self, timeout: float = 5.0) -> None:
                pass
            def _create_collection(self, name: str) -> None:
                pass

        store = ConcreteStore(database_name="test_db")
        assert store.database_name == "test_db"
