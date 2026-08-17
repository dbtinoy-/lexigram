"""Tests for miscellaneous low-coverage files.

Covers:
- relations/manager.py (AbstractRelationManager)
- data/data_source.py (_quote_identifier)
- actions/row_manager.py (compatibility imports)
- relations/__init__.py (imports)
- data/data_source.py (DataSourceBase, SqlDataSource)
"""

from __future__ import annotations

from typing import Any

import pytest


# ---------------------------------------------------------------------------
# _quote_identifier (interfaces/data_source.py)
# ---------------------------------------------------------------------------


class TestQuoteIdentifier:
    """Tests for _quote_identifier helper."""

    def test_valid_identifier(self) -> None:
        from lexigram.admin.data.data_source import _quote_identifier

        result = _quote_identifier("my_table")
        assert result == '"my_table"'

    def test_valid_alphanumeric(self) -> None:
        from lexigram.admin.data.data_source import _quote_identifier

        result = _quote_identifier("column1")
        assert result == '"column1"'

    def test_valid_all_alpha(self) -> None:
        from lexigram.admin.data.data_source import _quote_identifier

        result = _quote_identifier("users")
        assert result == '"users"'

    def test_invalid_with_hyphen_raises(self) -> None:
        from lexigram.admin.data.data_source import _quote_identifier

        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _quote_identifier("my-table")

    def test_invalid_with_space_raises(self) -> None:
        from lexigram.admin.data.data_source import _quote_identifier

        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _quote_identifier("my table")

    def test_invalid_empty_raises(self) -> None:
        from lexigram.admin.data.data_source import _quote_identifier

        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _quote_identifier("")

    def test_invalid_with_dot_raises(self) -> None:
        from lexigram.admin.data.data_source import _quote_identifier

        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _quote_identifier("schema.table")


# ---------------------------------------------------------------------------
# AbstractRelationManager
# ---------------------------------------------------------------------------


class ConcreteRelationManager:
    """Concrete implementation of AbstractRelationManager for testing."""

    from lexigram.admin.relations.manager import AbstractRelationManager

    class _Impl(AbstractRelationManager):
        relationship_name = "pets"

        @classmethod
        def table(cls, table_config: Any = None) -> list:
            return []

        async def get_query(self) -> list[Any]:
            return ["item1", "item2", "item3", "item4", "item5"]


class TestAbstractRelationManager:
    """Tests for AbstractRelationManager."""

    def test_init_defaults(self) -> None:
        from lexigram.admin.relations.manager import AbstractRelationManager

        class TestRM(AbstractRelationManager):
            relationship_name = "items"

            @classmethod
            def table(cls, table_config=None) -> list:
                return []

            async def get_query(self) -> list[Any]:
                return []

        rm = TestRM()
        assert rm.parent_id is None
        assert rm.parent is None

    def test_init_with_parent_id(self) -> None:
        from lexigram.admin.relations.manager import AbstractRelationManager

        class TestRM(AbstractRelationManager):
            @classmethod
            def table(cls, table_config=None) -> list:
                return []

            async def get_query(self) -> list[Any]:
                return []

        rm = TestRM(parent_id="parent-1", parent=object())
        assert rm.parent_id == "parent-1"

    @pytest.mark.asyncio
    async def test_count(self) -> None:
        from lexigram.admin.relations.manager import AbstractRelationManager

        class TestRM(AbstractRelationManager):
            @classmethod
            def table(cls, table_config=None) -> list:
                return []

            async def get_query(self) -> list[Any]:
                return ["a", "b", "c"]

        rm = TestRM()
        count = await rm.count()
        assert count == 3

    @pytest.mark.asyncio
    async def test_count_empty(self) -> None:
        from lexigram.admin.relations.manager import AbstractRelationManager

        class TestRM(AbstractRelationManager):
            @classmethod
            def table(cls, table_config=None) -> list:
                return []

            async def get_query(self) -> list[Any]:
                return []

        rm = TestRM()
        count = await rm.count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_items_paginated(self) -> None:
        from lexigram.admin.relations.manager import AbstractRelationManager

        class TestRM(AbstractRelationManager):
            @classmethod
            def table(cls, table_config=None) -> list:
                return []

            async def get_query(self) -> list[Any]:
                return list(range(10))

        rm = TestRM()
        page1 = await rm.get_items(page=1, per_page=3)
        assert page1 == [0, 1, 2]

        page2 = await rm.get_items(page=2, per_page=3)
        assert page2 == [3, 4, 5]

    @pytest.mark.asyncio
    async def test_get_items_empty(self) -> None:
        from lexigram.admin.relations.manager import AbstractRelationManager

        class TestRM(AbstractRelationManager):
            @classmethod
            def table(cls, table_config=None) -> list:
                return []

            async def get_query(self) -> list[Any]:
                return []

        rm = TestRM()
        items = await rm.get_items()
        assert items == []

    def test_get_relationship_name_from_class_var(self) -> None:
        from lexigram.admin.relations.manager import AbstractRelationManager

        class PetsRelationManager(AbstractRelationManager):
            relationship_name = "pets"

            @classmethod
            def table(cls, table_config=None) -> list:
                return []

            async def get_query(self) -> list[Any]:
                return []

        assert PetsRelationManager.get_relationship_name() == "pets"

    def test_get_relationship_name_derived_from_class_name(self) -> None:
        from lexigram.admin.relations.manager import AbstractRelationManager

        class CommentsRelationManager(AbstractRelationManager):
            relationship_name = ""  # Empty — should derive from class name

            @classmethod
            def table(cls, table_config=None) -> list:
                return []

            async def get_query(self) -> list[Any]:
                return []

        name = CommentsRelationManager.get_relationship_name()
        assert "comments" in name.lower()


# ---------------------------------------------------------------------------
# compatibility imports
# ---------------------------------------------------------------------------


class TestCompatibilityImports:
    """Tests that compatibility re-exports work correctly."""

    def test_interfaces_init_exports(self) -> None:
        from lexigram.admin.data.data_source import DataSourceBase, SqlDataSource
        assert DataSourceBase is not None
        assert SqlDataSource is not None

    def test_relations_init_exports(self) -> None:
        from lexigram.admin.relations import AbstractRelationManager
        assert AbstractRelationManager is not None

    def test_row_manager_compat_imports(self) -> None:
        from lexigram.admin.actions.row_manager import (
            ActionGroup,
            ActionPosition,
            ActionStyle,
            RowAction,
            RowActionManager,
        )
        assert ActionGroup is not None
        assert ActionPosition is not None
        assert ActionStyle is not None
        assert RowAction is not None
        assert RowActionManager is not None
