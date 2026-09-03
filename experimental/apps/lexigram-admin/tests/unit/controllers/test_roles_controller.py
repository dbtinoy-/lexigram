"""Roles controller tests (R10 — docs/09-01-2026/06-access-control-ui.md)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.exceptions import HTTPException
from starlette.requests import Request

from lexigram.admin.controllers.access_control import RolesController
from lexigram.contracts.core.result import Err, Ok


class _FakeUser:
    def __init__(
        self,
        user_id: str = "u-1",
        roles: list[str] | None = None,
        is_superuser: bool = False,
    ) -> None:
        self.user_id = user_id
        self.email = f"{user_id}@example.com"
        self.roles = roles or []
        self.is_superuser = is_superuser
        self.permissions: frozenset[str] = frozenset()


class _FakeForm(dict):
    """dict with FormData-style getlist for multi-value fields."""

    def __init__(self, single: dict | None = None, multi: dict | None = None):
        super().__init__(single or {})
        self._multi = multi or {}

    def getlist(self, key: str) -> list[str]:
        if key in self._multi:
            return list(self._multi[key])
        return [self[key]] if key in self else []


def _role(
    name: str,
    permissions: list[str] | None = None,
    inherits: list[str] | None = None,
    is_system: bool = False,
    description: str = "",
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        description=description,
        permissions=permissions or [],
        inherits=inherits or [],
        is_system=is_system,
    )


def _request(
    user: Any,
    session: dict | None = None,
    form: Any = None,
    query: dict | None = None,
    path: str = "/admin/roles",
) -> MagicMock:
    req = MagicMock(spec=Request)
    req.__len__ = MagicMock(return_value=1)  # falsy spec'd Request workaround
    req.state.user = user
    req.state.container = None
    req.app.state.container = None
    req.scope = {"root_path": "/admin"}
    req.session = session if session is not None else {}
    req.query_params = query or {}
    req.url.path = path
    req.headers = {}
    req.client = SimpleNamespace(host="127.0.0.1")
    if form is not None:
        req.form = AsyncMock(return_value=form)
    return req


def _controller(**kwargs: Any) -> RolesController:
    return RolesController(renderer=MagicMock(), **kwargs)


class TestSuperAdminGate:
    def test_literal_superuser_flag_passes(self) -> None:
        assert _controller()._is_super_admin(_FakeUser(is_superuser=True)) is True

    def test_magicmock_truthy_flag_is_rejected(self) -> None:
        """B1 regression: only a literal True flag counts."""
        assert _controller()._is_super_admin(MagicMock()) is False

    def test_configured_role_passes(self) -> None:
        c = _controller(super_admin_role="root")
        assert c._is_super_admin(_FakeUser(roles=["root"])) is True

    def test_guard_redirects_guests_to_login(self) -> None:
        response = _controller()._guard(_request(_FakeUser(user_id="guest")))
        assert response is not None
        assert response.status_code == 302
        assert "/admin/login" in response.headers["location"]

    def test_guard_403_for_non_superadmin(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _controller()._guard(_request(_FakeUser(roles=["editor"])))
        assert exc_info.value.status_code == 403

    def test_guard_passes_superadmin(self) -> None:
        assert _controller()._guard(_request(_FakeUser(roles=["superadmin"]))) is None


class TestPermissionParsing:
    def test_matrix_and_custom_lines_merge_dedupe_sort(self) -> None:
        form = _FakeForm(
            {"custom_permissions": "posts.publish\nusers.list\n\n"},
            multi={"permissions": ["users.list", "roles.view"]},
        )
        valid, rejected = RolesController._parse_permissions(form)
        assert valid == ["posts.publish", "roles.view", "users.list"]
        assert rejected == []

    def test_scope_suffixes_accepted(self) -> None:
        form = _FakeForm({"custom_permissions": "posts.update:self\nposts.view:all"})
        valid, rejected = RolesController._parse_permissions(form)
        assert valid == ["posts.update:self", "posts.view:all"]
        assert rejected == []

    def test_bad_formats_rejected(self) -> None:
        form = _FakeForm(
            {"custom_permissions": "no-dot\nUPPER.CASE!\nx.y:everything"}
        )
        valid, rejected = RolesController._parse_permissions(form)
        assert valid == []
        assert len(rejected) == 3

    def test_plain_dict_form_supported(self) -> None:
        valid, _ = RolesController._parse_permissions({"permissions": "users.list"})
        assert valid == ["users.list"]


class TestCreate:
    @pytest.mark.asyncio
    async def test_creates_role(self) -> None:
        service = MagicMock()
        service.create_role = AsyncMock(return_value=Ok(_role("editor")))
        c = _controller(role_service=service)
        form = _FakeForm(
            {"csrf_token": "", "name": "Editor", "description": "d"},
            multi={"permissions": ["users.list"], "inherits": ["viewer"]},
        )
        response = await c.create(_request(_FakeUser(is_superuser=True), form=form))
        assert "notice=" in response.headers["location"]
        kwargs = service.create_role.await_args.kwargs
        assert kwargs["name"] == "editor"  # normalised to lowercase
        assert kwargs["permissions"] == ["users.list"]
        assert kwargs["inherits"] == ["viewer"]
        assert kwargs["actor_id"] == "u-1"  # audit attribution

    @pytest.mark.asyncio
    async def test_invalid_name_rejected(self) -> None:
        service = MagicMock()
        service.create_role = AsyncMock()
        c = _controller(role_service=service)
        form = _FakeForm({"csrf_token": "", "name": "bad name!"})
        response = await c.create(_request(_FakeUser(is_superuser=True), form=form))
        service.create_role.assert_not_awaited()
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_invalid_permission_rejected(self) -> None:
        service = MagicMock()
        service.create_role = AsyncMock()
        c = _controller(role_service=service)
        form = _FakeForm(
            {"csrf_token": "", "name": "editor", "custom_permissions": "not valid"}
        )
        response = await c.create(_request(_FakeUser(is_superuser=True), form=form))
        service.create_role.assert_not_awaited()
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_duplicate_error_surfaces(self) -> None:
        service = MagicMock()
        service.create_role = AsyncMock(return_value=Err(ValueError("exists")))
        c = _controller(role_service=service)
        form = _FakeForm({"csrf_token": "", "name": "editor"})
        response = await c.create(_request(_FakeUser(is_superuser=True), form=form))
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_csrf_failure_rejected(self) -> None:
        csrf = MagicMock()
        csrf.validate_token.return_value = False
        service = MagicMock()
        service.create_role = AsyncMock()
        c = _controller(csrf_service=csrf, role_service=service)
        form = _FakeForm({"csrf_token": "bad", "name": "editor"})
        response = await c.create(
            _request(
                _FakeUser(is_superuser=True),
                session={"csrf_session_id": "sid"},
                form=form,
            )
        )
        service.create_role.assert_not_awaited()
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_no_service_is_friendly_error(self) -> None:
        c = _controller()
        form = _FakeForm({"csrf_token": "", "name": "editor"})
        response = await c.create(_request(_FakeUser(is_superuser=True), form=form))
        assert "error=" in response.headers["location"]


class TestUpdate:
    @pytest.mark.asyncio
    async def test_updates_role(self) -> None:
        service = MagicMock()
        service.update_role = AsyncMock(return_value=Ok(_role("editor")))
        c = _controller(role_service=service)
        form = _FakeForm(
            {"csrf_token": "", "description": "new"},
            multi={"permissions": ["users.view"]},
        )
        response = await c.update(
            _request(_FakeUser(is_superuser=True), form=form), "editor"
        )
        assert "notice=" in response.headers["location"]
        kwargs = service.update_role.await_args.kwargs
        assert kwargs["name"] == "editor"
        assert kwargs["permissions"] == ["users.view"]

    @pytest.mark.asyncio
    async def test_service_error_surfaces(self) -> None:
        service = MagicMock()
        service.update_role = AsyncMock(return_value=Err(ValueError("missing")))
        c = _controller(role_service=service)
        form = _FakeForm({"csrf_token": ""})
        response = await c.update(
            _request(_FakeUser(is_superuser=True), form=form), "ghost"
        )
        assert "error=" in response.headers["location"]


class TestDelete:
    def _users(self, *role_lists: list[str]) -> MagicMock:
        store = MagicMock()
        store.list_users = AsyncMock(
            return_value=[
                SimpleNamespace(user_id=f"u-{i}", roles=r, is_active=True)
                for i, r in enumerate(role_lists)
            ]
        )
        return store

    @pytest.mark.asyncio
    async def test_deletes_unassigned_role(self) -> None:
        service = MagicMock()
        service.delete_role = AsyncMock(return_value=Ok(True))
        service.list_roles = AsyncMock(return_value=[])
        c = _controller(role_service=service)
        c._user_store = self._users(["other"])
        form = _FakeForm({"csrf_token": ""})
        response = await c.delete(
            _request(_FakeUser(is_superuser=True), form=form), "editor"
        )
        service.delete_role.assert_awaited_once_with("editor", actor_id="u-1")
        assert "notice=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_blocks_delete_while_assigned(self) -> None:
        service = MagicMock()
        service.delete_role = AsyncMock()
        c = _controller(role_service=service)
        c._user_store = self._users(["editor"], ["editor", "x"])
        form = _FakeForm({"csrf_token": ""})
        response = await c.delete(
            _request(_FakeUser(is_superuser=True), form=form), "editor"
        )
        service.delete_role.assert_not_awaited()
        assert "error=" in response.headers["location"]
        assert "2" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_system_role_error_surfaces(self) -> None:
        service = MagicMock()
        service.delete_role = AsyncMock(return_value=Err(ValueError("system role")))
        service.list_roles = AsyncMock(return_value=[])
        c = _controller(role_service=service)
        c._user_store = self._users([])
        form = _FakeForm({"csrf_token": ""})
        response = await c.delete(
            _request(_FakeUser(is_superuser=True), form=form), "superadmin"
        )
        assert "error=" in response.headers["location"]


class TestMatrixRendering:
    def test_inventory_options_render_with_checked_state(self) -> None:
        inventory = MagicMock()
        inventory.options.return_value = {"users": ["users.list", "users.view"]}
        c = _controller(permission_inventory=inventory)
        html = c._matrix_html({"users.list"})
        assert 'value="users.list" checked' in html
        assert 'value="users.view">' in html

    def test_unknown_permissions_prefill_custom_textarea(self) -> None:
        inventory = MagicMock()
        inventory.options.return_value = {"users": ["users.list"]}
        c = _controller(permission_inventory=inventory)
        html = c._matrix_html({"users.list", "posts.publish"})
        assert "posts.publish" in html

    def test_no_inventory_still_renders_custom_field(self) -> None:
        html = _controller()._matrix_html(set())
        assert "custom_permissions" in html


class TestEffectiveCard:
    """R40 (doc 36): effective-permissions preview card."""

    def test_inherited_permissions_show_provenance(self) -> None:
        roles = [
            _role("viewer", ["posts.read"]),
            _role("editor", ["posts.write"], inherits=["viewer"]),
        ]
        html = _controller()._effective_html("editor", roles)
        assert "Effective permissions" in html
        assert "(2 total)" in html
        assert "posts.write" in html
        assert "posts.read" in html
        assert "via viewer" in html

    def test_missing_inherited_role_warns(self) -> None:
        roles = [_role("editor", ["posts.write"], inherits=["ghost"])]
        html = _controller()._effective_html("editor", roles)
        assert "Warning" in html
        assert "ghost" in html
        assert "grant nothing" in html

    def test_cycle_terminates_and_renders(self) -> None:
        roles = [
            _role("a", ["p.a"], inherits=["b"]),
            _role("b", ["p.b"], inherits=["a"]),
        ]
        html = _controller()._effective_html("a", roles)
        assert "(2 total)" in html
        assert "via b" in html

    def test_no_permissions_renders_none_placeholders(self) -> None:
        html = _controller()._effective_html("empty", [_role("empty")])
        assert "none" in html


class TestDuplicatePrefill:
    """R40 (doc 36 §2.4): GET /roles/new?from=<role> prefill."""

    def _controller_with_page_capture(self, roles: list) -> tuple[Any, list]:
        service = MagicMock()
        service.list_roles = AsyncMock(return_value=roles)
        c = _controller(role_service=service)
        captured: list = []

        async def _page(request, html, *a, **kw):
            captured.append(html)
            return MagicMock()

        c._page = _page
        return c, captured

    @pytest.mark.asyncio
    async def test_unknown_source_redirects_with_error(self) -> None:
        c, _ = self._controller_with_page_capture([])
        response = await c.new_page(
            _request(_FakeUser(is_superuser=True), query={"from": "ghost"})
        )
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_prefills_from_source_role(self) -> None:
        roles = [
            _role("viewer", ["posts.read"]),
            _role(
                "editor",
                ["posts.write"],
                inherits=["viewer"],
                description="Editing role",
            ),
        ]
        c, captured = self._controller_with_page_capture(roles)
        await c.new_page(
            _request(_FakeUser(is_superuser=True), query={"from": "editor"})
        )
        html = captured[0]
        assert 'value="editor-copy"' in html
        assert "Duplicating" in html
        assert "Editing role" in html
        assert 'value="viewer" checked' in html  # inherits prefilled
        assert "posts.write" in html  # custom textarea (no inventory)

    @pytest.mark.asyncio
    async def test_blank_form_without_from(self) -> None:
        c, captured = self._controller_with_page_capture([])
        await c.new_page(_request(_FakeUser(is_superuser=True)))
        assert "Duplicating" not in captured[0]
        assert 'name="name" value=""' in captured[0]


class TestDeleteInheritedGuard:
    """R40 (doc 36 §2.5): deletion blocked while other roles inherit."""

    @pytest.mark.asyncio
    async def test_blocks_delete_while_inherited(self) -> None:
        service = MagicMock()
        service.delete_role = AsyncMock()
        service.list_roles = AsyncMock(
            return_value=[
                _role("viewer"),
                _role("editor", inherits=["viewer"]),
            ]
        )
        c = _controller(role_service=service)
        store = MagicMock()
        store.list_users = AsyncMock(return_value=[])
        c._user_store = store
        form = _FakeForm({"csrf_token": ""})
        response = await c.delete(
            _request(_FakeUser(is_superuser=True), form=form), "viewer"
        )
        service.delete_role.assert_not_awaited()
        location = response.headers["location"]
        assert "error=" in location
        assert "editor" in location


class TestListEffectiveCounts:
    """R40 (doc 36 §2.3): list page shows inherited counts + Duplicate."""

    @pytest.mark.asyncio
    async def test_inherited_count_and_duplicate_link(self) -> None:
        service = MagicMock()
        service.list_roles = AsyncMock(
            return_value=[
                _role("viewer", ["posts.read"]),
                _role("editor", ["posts.write"], inherits=["viewer"]),
            ]
        )
        c = _controller(role_service=service)
        store = MagicMock()
        store.list_users = AsyncMock(return_value=[])
        c._user_store = store
        captured: list = []

        async def _page(request, html, *a, **kw):
            captured.append(html)
            return MagicMock()

        c._page = _page
        await c.list_page(_request(_FakeUser(is_superuser=True)))
        html = captured[0]
        assert "(+1 inherited)" in html
        assert "/admin/roles/new?from=editor" in html
        assert ">Duplicate</a>" in html
