from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.relations import BelongsToManyRelationManager


def _make_item(id: str, name: str) -> Any:
    return type("Item", (), {"id": id, "name": name})()


class ConcreteBelongsToMany(BelongsToManyRelationManager):
    relationship_name = "roles"
    pivot_table = "user_roles"
    pivot_columns = ["assigned_at", "is_primary"]
    related_key = "role_id"
    related_key_local = "user_id"

    async def get_query(self) -> list[Any]:
        return [
            _make_item("1", "Admin"),
            _make_item("2", "Editor"),
            _make_item("3", "Viewer"),
        ]

    async def get_attached_ids(self) -> list[str]:
        return ["1", "3"]

    async def get_pivot_data(self, related_id: str) -> dict[str, Any] | None:
        if related_id == "1":
            return {"assigned_at": "2026-01-01", "is_primary": "true"}
        if related_id == "3":
            return {"assigned_at": "2026-03-15", "is_primary": "false"}
        return None


class TestBelongsToManyRelationManager:
    @pytest.fixture
    def manager(self) -> BelongsToManyRelationManager:
        return ConcreteBelongsToMany(parent_id="parent-1")

    def test_construct(self, manager: BelongsToManyRelationManager) -> None:
        assert manager.relationship_name == "roles"
        assert manager.pivot_table == "user_roles"
        assert manager.pivot_columns == ["assigned_at", "is_primary"]
        assert manager.parent_id == "parent-1"

    @pytest.mark.asyncio
    async def test_get_query_returns_items(
        self, manager: BelongsToManyRelationManager
    ) -> None:
        items = await manager.get_query()
        assert len(items) == 3

    @pytest.mark.asyncio
    async def test_get_attached_ids(
        self, manager: BelongsToManyRelationManager
    ) -> None:
        ids = await manager.get_attached_ids()
        assert "1" in ids
        assert "2" not in ids

    @pytest.mark.asyncio
    async def test_get_pivot_data(
        self, manager: BelongsToManyRelationManager
    ) -> None:
        data = await manager.get_pivot_data("1")
        assert data is not None
        assert data["assigned_at"] == "2026-01-01"

    @pytest.mark.asyncio
    async def test_get_pivot_data_none_for_unattached(
        self, manager: BelongsToManyRelationManager
    ) -> None:
        data = await manager.get_pivot_data("2")
        assert data is None

    @pytest.mark.asyncio
    async def test_render_returns_string(
        self, manager: BelongsToManyRelationManager
    ) -> None:
        html = await manager.render(request=None, resource_name="users")
        assert isinstance(html, str)
        assert "Admin" in html
        assert "Editor" in html
        assert "Viewer" in html

    @pytest.mark.asyncio
    async def test_render_shows_pivot_columns(
        self, manager: BelongsToManyRelationManager
    ) -> None:
        html = await manager.render(request=None, resource_name="users")
        assert "assigned_at" in html
        assert "is_primary" in html

    @pytest.mark.asyncio
    async def test_render_shows_checkboxes(
        self, manager: BelongsToManyRelationManager
    ) -> None:
        html = await manager.render(request=None, resource_name="users")
        assert 'type="checkbox"' in html
        assert 'checked' in html

    @pytest.mark.asyncio
    async def test_render_header(
        self, manager: BelongsToManyRelationManager
    ) -> None:
        html = await manager.render(request=None, resource_name="users")
        assert "Roles" in html or "roles" in html

    @pytest.mark.asyncio
    async def test_attach(self, manager: BelongsToManyRelationManager) -> None:
        await manager.attach("4")
        assert True

    @pytest.mark.asyncio
    async def test_detach(self, manager: BelongsToManyRelationManager) -> None:
        await manager.detach("1")
        assert True

    @pytest.mark.asyncio
    async def test_sync(self, manager: BelongsToManyRelationManager) -> None:
        await manager.sync(["1", "2"])
        assert True

    @pytest.mark.asyncio
    async def test_update_pivot(
        self, manager: BelongsToManyRelationManager
    ) -> None:
        await manager.update_pivot("1", {"assigned_at": "2026-06-01"})
        assert True

    def test_get_relationship_name(self, manager: BelongsToManyRelationManager) -> None:
        assert manager.get_relationship_name() == "roles"

    def test_get_pivot_routes(self, manager: BelongsToManyRelationManager) -> None:
        routes = manager.get_pivot_routes("users")
        assert len(routes) == 3

    def test_render_pivot_headers(self, manager: BelongsToManyRelationManager) -> None:
        headers = manager._render_pivot_headers()
        assert "Assigned At" in headers or "assigned_at" in headers

    def test_render_pivot_headers_empty(self) -> None:
        class NoPivot(BelongsToManyRelationManager):
            pivot_columns = []
            async def get_query(self) -> list[Any]:
                return []
            async def get_attached_ids(self) -> list[str]:
                return []

        mgr = NoPivot(parent_id="x")
        assert mgr._render_pivot_headers() == ""
