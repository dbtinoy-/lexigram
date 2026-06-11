"""Hostile-value rendering tests for MorphManyRelationManager (F1 stored XSS)."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.relations import MorphManyRelationManager


def _item(id: Any, name: Any = "Rex") -> Any:
    return type("Item", (), {"id": id, "name": name})()


class _HostileMorphMany(MorphManyRelationManager):
    relationship_name = "comments"

    async def get_query(self) -> list[Any]:
        return [_item('<img src="x" onerror="alert(1)">', "<svg onload=alert(1)>")]


class _HostileIdMorphMany(MorphManyRelationManager):
    relationship_name = "comments"

    async def get_query(self) -> list[Any]:
        return [_item('x" onmouseover="alert(1)<img src=x onerror=alert(1)>')]


class _BenignMorphMany(MorphManyRelationManager):
    relationship_name = "comments"

    async def get_query(self) -> list[Any]:
        return [_item(7, "First comment")]


class TestMorphManyRenderXss:
    @pytest.mark.asyncio
    async def test_hostile_label_and_id_escaped_in_cell_text(self) -> None:
        mgr = _HostileMorphMany(parent_id=42)
        html = await mgr.render(request=None, resource_name="posts")
        assert "&lt;img" in html
        assert "&lt;svg" in html
        assert "<img" not in html
        assert "<svg" not in html

    @pytest.mark.asyncio
    async def test_hostile_item_id_escaped_in_attribute_positions(self) -> None:
        mgr = _HostileIdMorphMany(parent_id=42)
        html = await mgr.render(request=None, resource_name="posts")
        assert "&quot;" in html
        assert "&lt;img" in html
        assert "<img" not in html
        assert '<img ' not in html

    @pytest.mark.asyncio
    async def test_benign_render_keeps_root_panel_id_contract(self) -> None:
        mgr = _BenignMorphMany(parent_id=42)
        html = await mgr.render(request=None, resource_name="posts")
        assert 'id="relation-panel-comments"' in html
        assert "First comment" in html