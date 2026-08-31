"""Tests for RestoreActionHandler, PurgeActionHandler, and route registration.

Verifies that the restore/purge action dispatchers and resource routing
are properly wired for the soft-delete feature.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.actions.base import BulkAction
from lexigram.admin.actions.types import ActionContext
from lexigram.admin.config import AdminConfig
from lexigram.admin.core.routing import AdminRouter
from lexigram.admin.resources.base import Resource
from lexigram.result import Ok
from lexigram.admin.resources.action_handlers import (
    PurgeActionHandler,
    RestoreActionHandler,
)
from lexigram.admin.resources.handler import BulkActionHandler


class TestRestoreActionHandler:
    """Tests for RestoreActionHandler."""

    def test_can_handle_restore(self) -> None:
        handler = RestoreActionHandler()
        assert handler.can_handle("restore") is True

    def test_cannot_handle_other(self) -> None:
        handler = RestoreActionHandler()
        assert handler.can_handle("edit") is False

    def test_cannot_handle_empty(self) -> None:
        handler = RestoreActionHandler()
        assert handler.can_handle("") is False


class TestPurgeActionHandler:
    """Tests for PurgeActionHandler."""

    def test_can_handle_purge(self) -> None:
        handler = PurgeActionHandler()
        assert handler.can_handle("purge") is True

    def test_cannot_handle_other(self) -> None:
        handler = PurgeActionHandler()
        assert handler.can_handle("delete") is False

    def test_cannot_handle_empty(self) -> None:
        handler = PurgeActionHandler()
        assert handler.can_handle("") is False


class TestRestorePurgeRouteRegistration:
    """Tests for restore/purge route registration in AdminRouter."""

    def test_restore_route_in_build_resource_routes(self) -> None:
        config = AdminConfig(prefix="/admin")
        mock_resource = MagicMock()
        mock_resource.relations = []
        router = AdminRouter(config=config, resources={"users": mock_resource})
        routes = router._build_resource_routes("users", mock_resource)
        paths = [r.path for r in routes]
        assert any("/restore" in path for path in paths), (
            f"No route with '/restore' found in paths: {paths}"
        )

    def test_purge_route_in_build_resource_routes(self) -> None:
        config = AdminConfig(prefix="/admin")
        mock_resource = MagicMock()
        mock_resource.relations = []
        router = AdminRouter(config=config, resources={"users": mock_resource})
        routes = router._build_resource_routes("users", mock_resource)
        paths = [r.path for r in routes]
        assert any("/purge" in path for path in paths), (
            f"No route with '/purge' found in paths: {paths}"
        )

    def test_restore_and_purge_routes_require_mutating_methods(self) -> None:
        """Archive mutations must not be triggerable by a safe browser GET."""
        config = AdminConfig(prefix="/admin")
        mock_resource = MagicMock()
        mock_resource.relations = []
        router = AdminRouter(config=config, resources={"users": mock_resource})
        routes = router._build_resource_routes("users", mock_resource)
        restore_routes = [r for r in routes if "/restore" in (r.path or "")]
        purge_routes = [r for r in routes if "/purge" in (r.path or "")]
        assert restore_routes and purge_routes
        assert all(route.methods == {"POST"} for route in restore_routes)
        assert all(route.methods == {"POST", "DELETE"} for route in purge_routes)

    def test_routes_for_multiple_resources(self) -> None:
        config = AdminConfig(prefix="/admin")
        mock_users = MagicMock()
        mock_users.relations = []
        mock_posts = MagicMock()
        mock_posts.relations = []

        router = AdminRouter(
            config=config,
            resources={"users": mock_users, "posts": mock_posts},
        )

        users_routes = router._build_resource_routes("users", mock_users)
        posts_routes = router._build_resource_routes("posts", mock_posts)

        users_paths = [r.path for r in users_routes]
        posts_paths = [r.path for r in posts_routes]

        assert any("/restore" in p for p in users_paths)
        assert any("/purge" in p for p in users_paths)
        assert any("/restore" in p for p in posts_paths)
        assert any("/purge" in p for p in posts_paths)


class _FakeDataSource:
    """In-memory IDataSource fake for bulk handler tests."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {
            "1": {"id": "1", "name": "one"},
            "2": {"id": "2", "name": "two"},
        }

    async def find_one(self, item_id: Any) -> dict[str, Any] | None:
        return self._store.get(str(item_id))

    async def update(self, item_id: Any, data: dict[str, Any]) -> dict[str, Any] | None:
        record = self._store.get(str(item_id))
        if record is None:
            return None
        record.update(data)
        return record

    async def delete(self, item_id: Any) -> bool:
        return self._store.pop(str(item_id), None) is not None

    async def bulk_delete(self, ids: list[str]) -> int:
        deleted = 0
        for id_ in ids:
            if self._store.pop(str(id_), None) is not None:
                deleted += 1
        return deleted


class _BulkResource(Resource):
    """Concrete Resource for bulk handler tests."""

    name = "items"


class _ArchiveAction(BulkAction):
    """Server-backed custom action used to verify generic bulk dispatch."""

    def __init__(self) -> None:
        super().__init__(name="archive", label="Archive")

    async def authorize(self, records: list[Any], user: Any = None) -> Any:
        del records, user
        return Ok(None)

    async def execute(self, records: list[Any], ctx: ActionContext) -> Any:
        for record in records:
            await ctx.data_source.update(record["id"], {"archived": True})
        return Ok({"message": f"Archived {len(records)} record(s)"})


class TestBulkActionHandlerPurgeRestore:
    """Tests for BulkActionHandler purge and restore dispatch."""

    def setup_method(self) -> None:
        self.handler = BulkActionHandler()
        self.ds = _FakeDataSource()
        self.resource = _BulkResource()
        self.resource._data_source = self.ds

    @pytest.mark.asyncio
    async def test_custom_declared_bulk_action_executes_server_hook(self) -> None:
        action = _ArchiveAction()
        self.resource.bulk_actions = [action]
        scope = self._make_scope(
            "POST",
            scope_extra={"admin_resource_prefix": "items"},
        )
        request = Request(scope)
        form = MagicMock()
        form.get = lambda key, default=None: {"action": "archive"}.get(key, default)
        form.getlist = lambda key: {"ids": ["1", "2"]}.get(key, [])
        request.scope["admin_form_data"] = form

        response = await self.handler.handle(request, self.resource)

        assert response.status_code == 302
        assert self.ds._store["1"]["archived"] is True
        assert self.ds._store["2"]["archived"] is True

    @pytest.mark.asyncio
    async def test_string_bulk_action_uses_explicit_resource_callback(self) -> None:
        self.resource.bulk_actions = ["archive"]

        async def bulk_archive(records: list[dict[str, Any]]) -> dict[str, str]:
            for record in records:
                await self.ds.update(record["id"], {"archived": True})
            return {"message": "Archived records"}

        self.resource.bulk_archive = bulk_archive  # type: ignore[attr-defined]
        scope = self._make_scope(
            "POST",
            scope_extra={"admin_resource_prefix": "items"},
        )
        request = Request(scope)
        form = MagicMock()
        form.get = lambda key, default=None: {"action": "archive"}.get(key, default)
        form.getlist = lambda key: {"ids": ["1"]}.get(key, [])
        request.scope["admin_form_data"] = form

        response = await self.handler.handle(request, self.resource)

        assert response.status_code == 302
        assert self.ds._store["1"]["archived"] is True

    def _make_scope(
        self,
        method: str,
        *,
        query: dict[str, list[str]] | None = None,
        scope_extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scope: dict[str, Any] = {
            "type": "http",
            "method": method,
            "path": "/admin/users/bulk",
            "query_string": b"",
            "headers": [],
            "path_params": {},
            "app": None,
            "state": MagicMock(),
        }
        if query:
            scope["query_string"] = (
                "&".join(f"{k}={v}" for k, vals in query.items() for v in vals)
            ).encode()
        scope.update(scope_extra or {})
        return scope

    def test_can_handle_purge_and_restore_confirms(self) -> None:
        assert self.handler.can_handle("bulk")
        assert self.handler.can_handle("bulk-delete-confirm")
        assert self.handler.can_handle("bulk-purge-confirm")
        assert self.handler.can_handle("bulk-restore-confirm")

    @pytest.mark.asyncio
    async def test_get_purge_confirm_renders_purge_slide_over(self) -> None:
        scope = self._make_scope(
            "GET",
            query={"ids": ["1", "2"]},
            scope_extra={
                "admin_action": "bulk-purge-confirm",
                "admin_resource_prefix": "users",
            },
        )
        request = Request(scope)
        response = await self.handler.handle(request, self.resource)
        assert response.status_code == 200
        body = response.body.decode()
        assert "PURGE" in body
        assert "{&quot;action&quot;:&quot;purge&quot;}" in body
        assert "Purge" in body

    @pytest.mark.asyncio
    async def test_get_restore_confirm_renders_restore_slide_over(self) -> None:
        scope = self._make_scope(
            "GET",
            query={"ids": ["1", "2"]},
            scope_extra={
                "admin_action": "bulk-restore-confirm",
                "admin_resource_prefix": "users",
            },
        )
        request = Request(scope)
        response = await self.handler.handle(request, self.resource)
        assert response.status_code == 200
        body = response.body.decode()
        assert "RESTORE" in body
        assert "{&quot;action&quot;:&quot;restore&quot;}" in body

    @pytest.mark.asyncio
    async def test_get_delete_confirm_defaults_to_delete(self) -> None:
        scope = self._make_scope(
            "GET",
            query={"ids": ["1"]},
            scope_extra={"admin_resource_prefix": "users"},
        )
        request = Request(scope)
        response = await self.handler.handle(request, self.resource)
        assert response.status_code == 200
        body = response.body.decode()
        assert "DELETE" in body
        assert "{&quot;action&quot;:&quot;delete&quot;}" in body

    @pytest.mark.asyncio
    async def test_post_purge_removes_records(self) -> None:
        scope = self._make_scope(
            "POST",
            scope_extra={"admin_resource_prefix": "users"},
        )
        request = Request(scope)
        form = MagicMock()
        form.get = lambda k, d=None: {"action": "purge"}.get(k, d)
        form.getlist = lambda k: {"ids": ["1", "2"]}.get(k, [])
        request.scope["admin_form_data"] = form
        response = await self.handler.handle(request, self.resource)
        assert response.status_code == 302
        assert self.ds._store == {}

    @pytest.mark.asyncio
    async def test_post_restore_clears_deleted_at(self) -> None:
        self.ds._store["1"] = {"id": "1", "name": "one", "deleted_at": "2026-01-01"}
        scope = self._make_scope("POST", scope_extra={"admin_resource_prefix": "users"})
        request = Request(scope)
        form = MagicMock()
        form.get = lambda k, d=None: {"action": "restore"}.get(k, d)
        form.getlist = lambda k: {"ids": ["1", "2"]}.get(k, [])
        request.scope["admin_form_data"] = form
        response = await self.handler.handle(request, self.resource)
        assert response.status_code == 302
        assert self.ds._store["1"]["deleted_at"] is None
        assert "2" in self.ds._store

    @pytest.mark.asyncio
    async def test_post_delete_honors_soft_delete_and_hooks(self) -> None:
        self.resource.soft_delete_enabled = True
        events: list[str] = []

        async def before(item_id: Any) -> None:
            events.append(f"before:{item_id}")

        async def after(item_id: Any) -> None:
            events.append(f"after:{item_id}")

        self.resource.before_delete = before  # type: ignore[method-assign]
        self.resource.after_delete = after  # type: ignore[method-assign]
        scope = self._make_scope("POST", scope_extra={"admin_resource_prefix": "users"})
        request = Request(scope)
        form = MagicMock()
        form.get = lambda k, d=None: {"action": "delete"}.get(k, d)
        form.getlist = lambda k: {"ids": ["1", "2"]}.get(k, [])
        request.scope["admin_form_data"] = form

        response = await self.handler.handle(request, self.resource)

        assert response.status_code == 302
        assert self.ds._store["1"]["deleted_at"] is not None
        assert self.ds._store["2"]["deleted_at"] is not None
        assert events == ["before:1", "after:1", "before:2", "after:2"]

    @pytest.mark.asyncio
    async def test_post_purge_runs_archive_hooks(self) -> None:
        events: list[str] = []

        async def before(data: dict[str, Any]) -> dict[str, Any]:
            events.append(f"before:{data['id']}")
            return data

        async def after(item_id: Any) -> None:
            events.append(f"after:{item_id}")

        self.resource.before_purge = before  # type: ignore[method-assign]
        self.resource.after_purge = after  # type: ignore[method-assign]
        scope = self._make_scope("POST", scope_extra={"admin_resource_prefix": "users"})
        request = Request(scope)
        form = MagicMock()
        form.get = lambda k, d=None: {"action": "purge"}.get(k, d)
        form.getlist = lambda k: {"ids": ["1", "2"]}.get(k, [])
        request.scope["admin_form_data"] = form

        response = await self.handler.handle(request, self.resource)

        assert response.status_code == 302
        assert self.ds._store == {}
        assert events == ["before:1", "after:1", "before:2", "after:2"]

    @pytest.mark.asyncio
    async def test_post_unknown_action_returns_400(self) -> None:
        scope = self._make_scope("POST", scope_extra={"admin_resource_prefix": "users"})
        request = Request(scope)
        form = MagicMock()
        form.get = lambda k, d=None: {"action": "explode"}.get(k, d)
        form.getlist = lambda k: {"ids": ["1"]}.get(k, [])
        request.scope["admin_form_data"] = form
        response = await self.handler.handle(request, self.resource)
        assert response.status_code == 400
