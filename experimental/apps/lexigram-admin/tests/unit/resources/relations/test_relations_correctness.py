"""R21 relations-layer regression tests (B24–B27).

See docs/09-01-2026/17-relations-correctness.md. Each bug test fails on
the pre-R21 code.
"""

from __future__ import annotations

from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from lexigram.admin.relations import BelongsToManyRelationManager
from lexigram.admin.relations.manager_ext import RelationManager
from lexigram.admin.relations.routes import register_relation_routes


class _PivotDataSource:
    """In-memory pivot store."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self._next_id = 1

    async def find_many(self, query: Any) -> Any:
        return type("R", (), {"items": list(self.rows), "total": len(self.rows)})()

    async def create(self, data: dict[str, Any]) -> Any:
        row = {"id": f"p{self._next_id}", **data}
        self._next_id += 1
        self.rows.append(row)
        return row

    async def bulk_delete(self, ids: list[Any]) -> int:
        self.rows = [r for r in self.rows if r.get("id") not in ids]
        return len(ids)

    async def update(self, item_id: Any, data: dict[str, Any]) -> Any:
        for row in self.rows:
            if row.get("id") == item_id:
                row.update(data)
                return row
        return None


_SHARED_PIVOT = _PivotDataSource()


class RolesManager(BelongsToManyRelationManager):
    relationship_name = "roles"
    pivot_table = "user_roles"
    pivot_columns = ["assigned_at"]
    related_key = "role_id"
    related_key_local = "user_id"

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("data_source", _SHARED_PIVOT)
        super().__init__(**kwargs)

    async def get_query(self) -> list[Any]:
        # Dict rows, exactly as SQL data sources return them (B26).
        return [
            {"id": "1", "name": "Admin"},
            {"id": "2", "name": "Editor"},
        ]


class GroupsManager(BelongsToManyRelationManager):
    relationship_name = "groups"
    pivot_table = "user_groups"
    related_key = "group_id"
    related_key_local = "user_id"

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("data_source", _PivotDataSource())
        super().__init__(**kwargs)

    async def get_query(self) -> list[Any]:
        return [{"id": "g1", "name": "Staff"}]


class _AuthedUser:
    id = "admin-1"


def _app(*managers: type[RelationManager]) -> Starlette:
    routes: list[Any] = []
    for mgr_cls in managers:
        routes.extend(register_relation_routes("users", mgr_cls))
    app = Starlette(routes=routes)

    class _InjectUser:
        """Raw ASGI middleware placing an authed user on request.state."""

        def __init__(self, inner: Any) -> None:
            self._inner = inner

        async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
            if scope["type"] == "http":
                scope.setdefault("state", {})["user"] = _AuthedUser()
            await self._inner(scope, receive, send)

    return _InjectUser(app)  # type: ignore[return-value]


class TestB24PivotFormExtraction:
    def test_rendered_input_names_are_mapped_to_columns(self) -> None:
        mgr = RolesManager(parent_id="u1")
        extracted = mgr._extract_pivot_form_data(
            {
                "pivot_assigned_at_5": "2026-01-01",
                "csrf_token": "tok",
                "unrelated": "x",
            },
            "5",
        )
        assert extracted == {"assigned_at": "2026-01-01"}

    def test_plain_column_names_still_accepted(self) -> None:
        mgr = RolesManager(parent_id="u1")
        extracted = mgr._extract_pivot_form_data({"assigned_at": "2026-02-02"}, "5")
        assert extracted == {"assigned_at": "2026-02-02"}

    def test_no_configured_columns_never_mass_assigns_raw_form(self) -> None:
        mgr = GroupsManager(parent_id="u1")
        extracted = mgr._extract_pivot_form_data(
            {"csrf_token": "tok", "pivot_weight_g1": "10"}, "g1"
        )
        assert extracted == {"weight": "10"}  # csrf_token never leaks through

    @pytest.mark.asyncio
    async def test_update_pivot_receives_mapped_values(self) -> None:
        ds = _PivotDataSource()

        class Mgr(RolesManager):
            def __init__(self, **kwargs: Any) -> None:
                kwargs["data_source"] = ds
                super().__init__(**kwargs)

        mgr = Mgr(parent_id="u1")
        await mgr.attach("1", {"assigned_at": "old"})

        class _Req:
            path_params = {"related_id": "1"}
            scope = {
                "admin_form_data": {
                    "pivot_assigned_at_1": "2026-05-05",
                    "csrf_token": "tok",
                }
            }
            headers = {}

        await mgr.handle_pivot_update(_Req())
        assert ds.rows[0]["assigned_at"] == "2026-05-05"
        assert "csrf_token" not in ds.rows[0]


class TestB25RouteCollision:
    def test_each_manager_gets_distinct_paths(self) -> None:
        roles_routes = register_relation_routes("users", RolesManager)
        groups_routes = register_relation_routes("users", GroupsManager)
        roles_paths = {r.path for r in roles_routes}
        groups_paths = {r.path for r in groups_routes}
        assert roles_paths.isdisjoint(groups_paths)
        assert any("/relations/roles" in p for p in roles_paths)
        assert any("/relations/groups" in p for p in groups_paths)

    def test_second_manager_is_reachable(self) -> None:
        # Pre-fix: both managers mounted at .../relations/{rel_name}, the
        # first swallowed every request and rendered the WRONG relation.
        client = TestClient(_app(RolesManager, GroupsManager))
        html = client.get("/users/u1/relations/groups").text
        assert "Staff" in html
        assert "Admin" not in html


class TestB26DictRows:
    @pytest.mark.asyncio
    async def test_render_shows_dict_row_ids_and_labels(self) -> None:
        client = TestClient(_app(RolesManager))
        html = client.get("/users/u1/relations/roles").text
        assert "Admin" in html
        assert "Editor" in html
        assert 'data-related-id="1"' in html  # pre-fix: data-related-id=""


class TestB27PivotRoutesMounted:
    def test_toggle_sync_pivot_routes_exist(self) -> None:
        routes = register_relation_routes("users", RolesManager)
        paths = {(r.path, tuple(sorted(r.methods or []))) for r in routes}
        expected = [
            "/users/{parent_id}/relations/roles/toggle",
            "/users/{parent_id}/relations/roles/sync",
            "/users/{parent_id}/relations/roles/pivot/{related_id}",
        ]
        for path in expected:
            assert any(p == path for p, _m in paths), f"missing {path}"

    def test_toggle_attaches_and_detaches(self) -> None:
        ds = _PivotDataSource()

        class Mgr(RolesManager):
            def __init__(self, **kwargs: Any) -> None:
                kwargs["data_source"] = ds
                super().__init__(**kwargs)

        client = TestClient(_app(Mgr))
        # Attach (pre-fix: this URL 404'd — get_pivot_routes was never mounted)
        resp = client.post("/users/u1/relations/roles/toggle", data={"related_id": "1"})
        assert resp.status_code == 200
        assert len(ds.rows) == 1
        assert ds.rows[0]["role_id"] == "1"
        # Detach
        resp = client.post("/users/u1/relations/roles/toggle", data={"related_id": "1"})
        assert resp.status_code == 200
        assert ds.rows == []

    def test_unauthenticated_pivot_posts_fail_closed(self) -> None:
        routes = register_relation_routes("users", RolesManager)
        app = Starlette(routes=routes)  # no user injected
        client = TestClient(app)
        resp = client.post("/users/u1/relations/roles/toggle", data={"related_id": "1"})
        assert resp.status_code == 403

    def test_missing_data_source_maps_to_400(self) -> None:
        class NoDsManager(BelongsToManyRelationManager):
            relationship_name = "tags"
            pivot_table = "user_tags"

            async def get_query(self) -> list[Any]:
                return []

        client = TestClient(_app(NoDsManager))
        resp = client.post("/users/u1/relations/tags/toggle", data={"related_id": "1"})
        assert resp.status_code == 400
        assert "data source" in resp.text
