from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.relations import MorphToRelationManager


class ConcreteMorphTo(MorphToRelationManager):
    relationship_name = "commentable"
    morph_name = "commentable"
    morph_types = {
        "post": type("PostResource", (), {"name": "Posts"}),
        "video": type("VideoResource", (), {"name": "Videos"}),
    }


class TestMorphToRelationManager:
    @pytest.fixture
    def manager(self) -> MorphToRelationManager:
        return ConcreteMorphTo(
            parent_id="parent-1",
            current_type="post",
            current_id="42",
        )

    def test_construct(self, manager: MorphToRelationManager) -> None:
        assert manager.morph_name == "commentable"
        assert manager.current_type == "post"
        assert manager.current_id == "42"

    @pytest.mark.asyncio
    async def test_get_available_types(
        self, manager: MorphToRelationManager
    ) -> None:
        types = await manager.get_available_types()
        assert len(types) == 2
        labels = {t["value"]: t["label"] for t in types}
        assert labels["post"] == "Posts"
        assert labels["video"] == "Videos"

    @pytest.mark.asyncio
    async def test_search_records(
        self, manager: MorphToRelationManager
    ) -> None:
        records = await manager.search_records("post", "test")
        assert records == []

    @pytest.mark.asyncio
    async def test_render_returns_string(
        self, manager: MorphToRelationManager
    ) -> None:
        html = await manager.render(request=None, resource_name="comments")
        assert isinstance(html, str)
        assert "commentable" in html

    @pytest.mark.asyncio
    async def test_render_shows_current_selection(
        self, manager: MorphToRelationManager
    ) -> None:
        html = await manager.render(request=None, resource_name="comments")
        assert "post" in html
        assert "42" in html

    @pytest.mark.asyncio
    async def test_render_shows_type_options(
        self, manager: MorphToRelationManager
    ) -> None:
        html = await manager.render(request=None, resource_name="comments")
        assert "Posts" in html
        assert "Videos" in html

    @pytest.mark.asyncio
    async def test_get_selected_record(
        self, manager: MorphToRelationManager
    ) -> None:
        record = await manager.get_selected_record()
        assert record == {"type": "post", "id": "42"}

    @pytest.mark.asyncio
    async def test_get_selected_record_none(self) -> None:
        mgr = ConcreteMorphTo(parent_id="x")
        record = await mgr.get_selected_record()
        assert record is None
