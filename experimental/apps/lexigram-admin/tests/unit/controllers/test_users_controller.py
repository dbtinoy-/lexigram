"""Users controller tests (R10 — docs/09-01-2026/06-access-control-ui.md)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.access_control import UsersController


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
    def __init__(self, single: dict | None = None, multi: dict | None = None):
        super().__init__(single or {})
        self._multi = multi or {}

    def getlist(self, key: str) -> list[str]:
        if key in self._multi:
            return list(self._multi[key])
        return [self[key]] if key in self else []


def _record(
    user_id: str,
    roles: list[str] | None = None,
    is_superuser: bool = False,
    is_active: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        user_id=user_id,
        email=f"{user_id}@example.com",
        name=user_id,
        roles=roles or [],
        is_superuser=is_superuser,
        is_active=is_active,
    )


def _store(records: list[Any]) -> MagicMock:
    store = MagicMock()
    store.list_users = AsyncMock(return_value=records)
    by_id = {str(r.user_id): r for r in records}
    store.get_user_by_id = AsyncMock(side_effect=lambda uid: by_id.get(str(uid)))
    store.update_user = AsyncMock()
    return store


def _request(
    user: Any,
    session: dict | None = None,
    form: Any = None,
    path: str = "/admin/users",
) -> MagicMock:
    req = MagicMock(spec=Request)
    req.__len__ = MagicMock(return_value=1)  # falsy spec'd Request workaround
    req.state.user = user
    req.state.container = None
    req.app.state.container = None
    req.scope = {"root_path": "/admin"}
    req.session = session if session is not None else {}
    req.query_params = {}
    req.url.path = path
    req.headers = {}
    req.client = SimpleNamespace(host="127.0.0.1")
    if form is not None:
        req.form = AsyncMock(return_value=form)
    return req


def _controller(**kwargs: Any) -> UsersController:
    return UsersController(renderer=MagicMock(), **kwargs)


class TestRoleOptions:
    @pytest.mark.asyncio
    async def test_union_of_stored_held_and_super_role(self) -> None:
        service = MagicMock()
        service.list_roles = AsyncMock(
            return_value=[SimpleNamespace(name="editor")]
        )
        c = _controller(role_service=service)
        users = [_record("u-1", roles=["legacy"])]
        options = await c._role_options(users)
        assert options == ["editor", "legacy", "superadmin"]

    @pytest.mark.asyncio
    async def test_service_failure_degrades_to_held_roles(self) -> None:
        service = MagicMock()
        service.list_roles = AsyncMock(side_effect=RuntimeError("db"))
        c = _controller(role_service=service)
        options = await c._role_options([_record("u-1", roles=["ops"])])
        assert options == ["ops", "superadmin"]


class TestDemotionGuard:
    def test_not_a_demotion_when_role_kept(self) -> None:
        c = _controller()
        target = _record("u-1", roles=["superadmin"])
        assert c._demotion_blocked(target, ["superadmin", "x"], [target]) is False

    def test_superuser_flag_survives_role_edits(self) -> None:
        c = _controller()
        target = _record("u-1", roles=["superadmin"], is_superuser=True)
        assert c._demotion_blocked(target, [], [target]) is False

    def test_blocks_last_superadmin_demotion(self) -> None:
        c = _controller()
        target = _record("u-1", roles=["superadmin"])
        others = [_record("u-2", roles=["editor"])]
        assert c._demotion_blocked(target, ["editor"], [target, *others]) is True

    def test_allows_demotion_with_another_active_superadmin(self) -> None:
        c = _controller()
        target = _record("u-1", roles=["superadmin"])
        other = _record("u-2", roles=["superadmin"])
        assert c._demotion_blocked(target, [], [target, other]) is False

    def test_inactive_superadmin_does_not_count(self) -> None:
        c = _controller()
        target = _record("u-1", roles=["superadmin"])
        other = _record("u-2", roles=["superadmin"], is_active=False)
        assert c._demotion_blocked(target, [], [target, other]) is True

    def test_fail_closed_on_empty_listing(self) -> None:
        """Unreadable user listing must block, never allow, the demotion."""
        c = _controller()
        target = _record("u-1", roles=["superadmin"])
        assert c._demotion_blocked(target, [], []) is True

    def test_superuser_flag_holder_counts_as_remaining_super(self) -> None:
        c = _controller()
        target = _record("u-1", roles=["superadmin"])
        other = _record("u-2", roles=[], is_superuser=True)
        assert c._demotion_blocked(target, [], [target, other]) is False

    def test_non_super_target_never_blocked(self) -> None:
        c = _controller()
        target = _record("u-1", roles=["editor"])
        assert c._demotion_blocked(target, [], [target]) is False


class TestUpdate:
    @pytest.mark.asyncio
    async def test_saves_roles_and_audits(self) -> None:
        target = _record("u-2", roles=["viewer"])
        store = _store([_record("u-1", roles=["superadmin"]), target])
        c = _controller()
        c._user_store = store
        c._audit_service = MagicMock()
        c._audit_service.log_event = AsyncMock()
        form = _FakeForm({"csrf_token": ""}, multi={"roles": ["editor", "viewer"]})
        req = _request(_FakeUser(is_superuser=True), form=form)
        response = await c.update(req, "u-2")
        assert "notice=" in response.headers["location"]
        store.update_user.assert_awaited_once()
        assert target.roles == ["editor", "viewer"]
        kwargs = c._audit_service.log_event.await_args.kwargs
        assert kwargs["admin_user_id"] == "u-1"
        assert kwargs["event_type"].value == "user_roles_updated"
        assert kwargs["metadata"]["roles_before"] == "viewer"
        assert kwargs["metadata"]["roles_after"] == "editor, viewer"

    @pytest.mark.asyncio
    async def test_blocks_last_superadmin_self_demotion(self) -> None:
        target = _record("u-1", roles=["superadmin"])
        store = _store([target])
        c = _controller()
        c._user_store = store
        form = _FakeForm({"csrf_token": ""}, multi={"roles": ["editor"]})
        req = _request(_FakeUser(user_id="u-1", is_superuser=True), form=form)
        response = await c.update(req, "u-1")
        store.update_user.assert_not_awaited()
        assert "error=" in response.headers["location"]
        assert target.roles == ["superadmin"]  # untouched

    @pytest.mark.asyncio
    async def test_unknown_user_is_friendly_error(self) -> None:
        c = _controller()
        c._user_store = _store([])
        form = _FakeForm({"csrf_token": ""})
        response = await c.update(
            _request(_FakeUser(is_superuser=True), form=form), "ghost"
        )
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_csrf_failure_rejected(self) -> None:
        csrf = MagicMock()
        csrf.validate_token.return_value = False
        store = _store([_record("u-2")])
        c = _controller(csrf_service=csrf)
        c._user_store = store
        form = _FakeForm({"csrf_token": "bad"})
        response = await c.update(
            _request(
                _FakeUser(is_superuser=True),
                session={"csrf_session_id": "sid"},
                form=form,
            ),
            "u-2",
        )
        store.update_user.assert_not_awaited()
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_store_failure_is_friendly(self) -> None:
        target = _record("u-2", roles=[])
        store = _store([_record("u-1", roles=["superadmin"]), target])
        store.update_user = AsyncMock(side_effect=RuntimeError("db exploded"))
        c = _controller()
        c._user_store = store
        form = _FakeForm({"csrf_token": ""}, multi={"roles": ["editor"]})
        response = await c.update(
            _request(_FakeUser(is_superuser=True), form=form), "u-2"
        )
        assert "error=" in response.headers["location"]
        assert "exploded" not in response.headers["location"]

    @pytest.mark.asyncio
    async def test_no_store_is_friendly_error(self) -> None:
        c = _controller()
        form = _FakeForm({"csrf_token": ""})
        response = await c.update(
            _request(_FakeUser(is_superuser=True), form=form), "u-2"
        )
        assert "error=" in response.headers["location"]
