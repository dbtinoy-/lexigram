"""Hostile-value render tests for RelationManager.render (F1 stored XSS)."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.relations import RelationManager


def _item(id: Any, name: Any = "Rex") -> Any:
    return type("Item", (), {"id": id, "name": name})()


def _col(name: str) -> Any:
    return type("Col", (), {"name": name})()


class _HostileLabelManager(RelationManager):
    relationship_name = "pets"

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return [_col("name")]

    async def get_query(self) -> list[Any]:
        return [_item(1, '<img src=x onerror=alert(1)>')]


class _HostileIdManager(RelationManager):
    relationship_name = "pets"

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return []

    async def get_query(self) -> list[Any]:
        return [_item('x" onmouseover="alert(1)')]


class _BenignManager(RelationManager):
    relationship_name = "pets"

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return []

    async def get_query(self) -> list[Any]:
        return [_item(7, "Rex")]


class TestRelationManagerRenderXss:
    @pytest.mark.asyncio
    async def test_hostile_label_field_escaped_in_cell_text(self) -> None:
        mgr = _HostileLabelManager(parent_id=42)
        html = await mgr.render(request=None, resource_name="users")
        assert "&lt;img" in html
        assert "<img" not in html

    @pytest.mark.asyncio
    async def test_hostile_item_id_escaped_in_attribute_positions(self) -> None:
        mgr = _HostileIdManager(parent_id=42)
        html = await mgr.render(request=None, resource_name="users")
        assert "&quot;" in html
        assert 'onmouseover="' not in html

    @pytest.mark.asyncio
    async def test_benign_render_keeps_root_panel_id_contract(self) -> None:
        mgr = _BenignManager(parent_id=42)
        html = await mgr.render(request=None, resource_name="users")
        assert 'id="relation-panel-pets"' in html