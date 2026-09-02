"""R24 relations inline-mutation & follow-up regression tests (B32–B34).

See docs/09-01-2026/20-relations-inline-mutations.md.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from lexigram.admin.relations import (
    BelongsToManyRelationManager,
    RelationManager,
    register_relation_routes,
)


class _RecordingDataSource:
    """Related-record data source recording mutations."""

    def __init__(self, records: list[dict[str, Any]] | None = None) -> None:
        self.records = records or []
        self.created: list[dict[str, Any]] = []
        self.updated: list[tuple[str, dict[str, Any]]] = []
        self.deleted: list[str] = []

    async def create(self, data: dict[str, Any]) -> Any:
        self.created.append(dict(data))
        return {"id": "new", **data}

    async def update(self, record_id: str, data: dict[str, Any]) -> Any:
        self.updated.append((record_id, dict(data)))
        return {"id": record_id, **data}

    async def delete(self, record_id: str) -> bool:
        self.deleted.append(record_id)
        return True


def _manager_class(data_source: _RecordingDataSource) -> type[RelationManager]:
    class _PetsManager(RelationManager):
        relationship_name = "pets"

        def __init__(self, **kwargs: Any) -> None:
            kwargs.setdefault("data_source", data_source)
            super().__init__(**kwargs)

        @classmethod
        def table(cls, table_config: Any = None) -> list[Any]:
            return []

        async def get_query(self) -> list[Any]:
            return [{"id": "7", "name": "Rex"}]

        async def render(self, request: Any, resource_name: str = "") -> str:
            return "<div>panel</div>"

    return _PetsManager


def _request(
    path_params: dict[str, str], form_data: dict[str, Any] | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        path_params=path_params,
        state=SimpleNamespace(user=object()),
        client=SimpleNamespace(host="127.0.0.1"),
        headers={},
        scope={"admin_form_data": form_data} if form_data is not None else {},
    )


class TestB32InlineMutationsPersist:
    @pytest.mark.asyncio
    async def test_create_persists_submitted_form(self) -> None:
        ds = _RecordingDataSource()
        routes = register_relation_routes("users", _manager_class(ds))
        response = await routes[2].endpoint(
            _request(
                {"parent_id": "1"},
                form_data={"name": "Bella", "csrf_token": "tok"},
            )
        )
        assert response.status_code == 200
        # csrf_token stripped; the submitted data actually persisted.
        assert ds.created == [{"name": "Bella"}]

    @pytest.mark.asyncio
    async def test_update_persists_submitted_form(self) -> None:
        ds = _RecordingDataSource()
        routes = register_relation_routes("users", _manager_class(ds))
        response = await routes[4].endpoint(
            _request(
                {"parent_id": "1", "record_id": "7"},
                form_data={"name": "Max", "csrf_token": "tok"},
            )
        )
        assert response.status_code == 200
        assert ds.updated == [("7", {"name": "Max"})]

    @pytest.mark.asyncio
    async def test_delete_actually_deletes(self) -> None:
        ds = _RecordingDataSource()
        routes = register_relation_routes("users", _manager_class(ds))
        response = await routes[5].endpoint(
            _request({"parent_id": "1", "record_id": "7"})
        )
        assert response.status_code == 200
        assert ds.deleted == ["7"]

    @pytest.mark.asyncio
    async def test_disabled_inline_create_is_403(self) -> None:
        ds = _RecordingDataSource()
        cls = _manager_class(ds)

        class _NoInline(cls):  # type: ignore[misc, valid-type]
            inline_create = False

        routes = register_relation_routes("users", _NoInline)
        response = await routes[2].endpoint(
            _request({"parent_id": "1"}, form_data={"name": "Bella"})
        )
        assert response.status_code == 403
        assert ds.created == []

    @pytest.mark.asyncio
    async def test_bulk_delete_fallback_when_no_delete_method(self) -> None:
        class _Source:
            def __init__(self) -> None:
                self.bulk_deleted: list[list[str]] = []

            async def bulk_delete(self, ids: list[str]) -> int:
                self.bulk_deleted.append(list(ids))
                return len(ids)

        ds = _Source()

        class _Mgr(RelationManager):
            relationship_name = "pets"

            def __init__(self, **kwargs: Any) -> None:
                kwargs.setdefault("data_source", ds)
                super().__init__(**kwargs)

            @classmethod
            def table(cls, table_config: Any = None) -> list[Any]:
                return []

            async def get_query(self) -> list[Any]:
                return [{"id": "7", "name": "Rex"}]

        routes = register_relation_routes("users", _Mgr)
        response = await routes[5].endpoint(
            _request({"parent_id": "1", "record_id": "7"})
        )
        assert response.status_code == 200
        assert ds.bulk_deleted == [["7"]]


class _CountingPivotSource:
    """Pivot store counting find_many calls (B33)."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.find_many_calls = 0

    async def find_many(self, query: Any) -> Any:
        self.find_many_calls += 1
        return SimpleNamespace(items=list(self.rows), total=len(self.rows))


class _TagsManager(BelongsToManyRelationManager):
    relationship_name = "tags"
    pivot_table = "user_tags"
    pivot_columns = ["weight"]
    related_key = "tag_id"
    related_key_local = "user_id"

    async def get_query(self) -> list[Any]:
        return [{"id": str(i), "name": f"Tag {i}"} for i in range(1, 6)]


class TestB33RenderPivotBatching:
    @pytest.mark.asyncio
    async def test_render_fetches_pivot_rows_a_constant_number_of_times(
        self,
    ) -> None:
        ds = _CountingPivotSource(
            [
                {"id": f"p{i}", "user_id": "u1", "tag_id": str(i), "weight": i}
                for i in range(1, 6)
            ]
        )
        mgr = _TagsManager(parent_id="u1", data_source=ds)
        request = SimpleNamespace(scope={}, headers={})
        html = await mgr.render(request, "users")
        # get_attached_ids (1) + get_pivot_data_map (1). Pre-fix this was
        # 1 + N (one full fetch per attached row) = 6.
        assert ds.find_many_calls == 2
        assert "Tag 1" in html

    @pytest.mark.asyncio
    async def test_pivot_map_matches_per_id_lookups(self) -> None:
        ds = _CountingPivotSource(
            [
                {"id": "p1", "user_id": "u1", "tag_id": "1", "weight": 10},
                {"id": "p2", "user_id": "u1", "tag_id": "2", "weight": 20},
            ]
        )
        mgr = _TagsManager(parent_id="u1", data_source=ds)
        batched = await mgr.get_pivot_data_map(["1", "2", "3"])
        assert batched == {
            "1": {"weight": 10},
            "2": {"weight": 20},
            "3": None,
        }
        assert batched["1"] == await mgr.get_pivot_data("1")

    @pytest.mark.asyncio
    async def test_map_respects_get_pivot_data_overrides(self) -> None:
        class _Overridden(_TagsManager):
            async def get_pivot_data(self, related_id: str) -> dict[str, Any]:
                return {"weight": f"override-{related_id}"}

        mgr = _Overridden(parent_id="u1", data_source=_CountingPivotSource([]))
        batched = await mgr.get_pivot_data_map(["9"])
        assert batched == {"9": {"weight": "override-9"}}


class TestB34GetItemsFilters:
    @pytest.mark.asyncio
    async def test_filters_are_applied(self) -> None:
        class _Mgr(RelationManager):
            relationship_name = "pets"

            @classmethod
            def table(cls, table_config: Any = None) -> list[Any]:
                return []

            async def get_query(self) -> list[Any]:
                return [
                    {"id": "1", "kind": "dog"},
                    {"id": "2", "kind": "cat"},
                    {"id": "3", "kind": "dog"},
                ]

        mgr = _Mgr(parent_id="1")
        items = await mgr.get_items(kind="dog")
        assert [i["id"] for i in items] == ["1", "3"]

    @pytest.mark.asyncio
    async def test_filters_compose_with_pagination(self) -> None:
        class _Mgr(RelationManager):
            relationship_name = "pets"

            @classmethod
            def table(cls, table_config: Any = None) -> list[Any]:
                return []

            async def get_query(self) -> list[Any]:
                return [{"id": str(i), "kind": "dog"} for i in range(10)]

        mgr = _Mgr(parent_id="1")
        items = await mgr.get_items(page=2, per_page=3, kind="dog")
        assert [i["id"] for i in items] == ["3", "4", "5"]
