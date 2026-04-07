from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.relations import MorphManyRelationManager


class ConcreteMorphMany(MorphManyRelationManager):
    relationship_name = "comments"
    morph_name = "commentable"
    morph_type_value = "post"


class TestMorphManyRelationManager:
    @pytest.fixture
    def manager(self) -> MorphManyRelationManager:
        return ConcreteMorphMany(parent_id="parent-1")

    def test_construct(self, manager: MorphManyRelationManager) -> None:
        assert manager.morph_name == "commentable"
        assert manager.morph_type_value == "post"
        assert manager.relationship_name == "comments"

    @pytest.mark.asyncio
    async def test_get_query_returns_empty_by_default(
        self, manager: MorphManyRelationManager
    ) -> None:
        items = await manager.get_query()
        assert items == []

    @pytest.mark.asyncio
    async def test_render_returns_string(
        self, manager: MorphManyRelationManager
    ) -> None:
        html = await manager.render(request=None, resource_name="posts")
        assert isinstance(html, str)

    @pytest.mark.asyncio
    async def test_render_shows_relationship_name(
        self, manager: MorphManyRelationManager
    ) -> None:
        html = await manager.render(request=None, resource_name="posts")
        assert "Comments" in html

    @pytest.mark.asyncio
    async def test_render_shows_empty_state(
        self, manager: MorphManyRelationManager
    ) -> None:
        html = await manager.render(request=None, resource_name="posts")
        assert "No related records found" in html

    @pytest.mark.asyncio
    async def test_render_with_inline_create(
        self, manager: MorphManyRelationManager
    ) -> None:
        html = await manager.render(request=None, resource_name="posts")
        assert "Add" in html

    @pytest.mark.asyncio
    async def test_render_table_structure(
        self, manager: MorphManyRelationManager
    ) -> None:
        html = await manager.render(request=None, resource_name="posts")
        assert "<table" in html
        assert "<thead" in html
        assert "<tbody" in html
