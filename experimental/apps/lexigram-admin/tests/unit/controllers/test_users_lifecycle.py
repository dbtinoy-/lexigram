"""Admin user lifecycle tests (R38 — docs/09-01-2026/34-user-lifecycle.md).

Covers UsersController create / deactivate / activate: password policy +
duplicate-email guards on creation, self- and last-superadmin guards on
deactivation, session revocation, and audit events.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.controllers.access_control import UsersController

_GOOD_PASSWORD = "Zx9!vKm2#Qw7pT4s"  # noqa: S105 — test fixture


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
    by_email = {str(r.email): r for r in records}
    store.get_user_by_id = AsyncMock(side_effect=lambda uid: by_id.get(str(uid)))
    store.get_user_by_email = AsyncMock(
        side_effect=lambda email: by_email.get(str(email))
    )
    store.update_user = AsyncMock()
    store.create_user = AsyncMock(
        side_effect=lambda **kw: SimpleNamespace(
            user_id="u-new", email=kw.get("email", ""), roles=kw.get("roles", [])
        )
    )
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


def _super() -> _FakeUser:
    return _FakeUser("me", is_superuser=True)


def _location(resp: Any) -> str:
    return resp.headers["location"]


class TestCreate:
    @pytest.mark.asyncio
    async def test_happy_path_hashes_password_and_audits(self) -> None:
        c = _controller()
        c._user_store = _store([_record("me", is_superuser=True)])
        c._audit_service = MagicMock(log_event=AsyncMock())
        form = _FakeForm(
            {
                "name": "New Admin",
                "email": "New.Admin@Example.com",
                "password": _GOOD_PASSWORD,
                "password_confirm": _GOOD_PASSWORD,
            },
            multi={"roles": ["editor"]},
        )
        resp = await c.create(_request(_super(), form=form))
        assert resp.status_code == 302
        assert "notice=" in _location(resp)
        kwargs = c._user_store.create_user.await_args.kwargs
        assert kwargs["email"] == "new.admin@example.com"  # normalized
        assert kwargs["roles"] == ["editor"]
        hashed = kwargs["hashed_password"]
        assert hashed != _GOOD_PASSWORD
        assert hashed.startswith("$2")
        event = c._audit_service.log_event.await_args.kwargs
        assert event["event_type"] == AdminSecurityEventType.USER_CREATED

    @pytest.mark.asyncio
    async def test_duplicate_email_rejected_before_store_create(self) -> None:
        c = _controller()
        c._user_store = _store([_record("existing")])
        form = _FakeForm(
            {
                "name": "X",
                "email": "existing@example.com",
                "password": _GOOD_PASSWORD,
                "password_confirm": _GOOD_PASSWORD,
            }
        )
        resp = await c.create(_request(_super(), form=form))
        assert "error=" in _location(resp)
        c._user_store.create_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unreadable_duplicate_check_fails_closed(self) -> None:
        c = _controller()
        c._user_store = _store([])
        c._user_store.get_user_by_email = AsyncMock(side_effect=RuntimeError("db"))
        form = _FakeForm(
            {
                "name": "X",
                "email": "x@example.com",
                "password": _GOOD_PASSWORD,
                "password_confirm": _GOOD_PASSWORD,
            }
        )
        resp = await c.create(_request(_super(), form=form))
        assert "error=" in _location(resp)
        c._user_store.create_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_weak_password_rejected_by_policy(self) -> None:
        c = _controller()
        c._user_store = _store([])
        form = _FakeForm(
            {
                "name": "X",
                "email": "x@example.com",
                "password": "short",
                "password_confirm": "short",
            }
        )
        resp = await c.create(_request(_super(), form=form))
        assert "error=" in _location(resp)
        c._user_store.create_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_password_mismatch_rejected(self) -> None:
        c = _controller()
        c._user_store = _store([])
        form = _FakeForm(
            {
                "name": "X",
                "email": "x@example.com",
                "password": _GOOD_PASSWORD,
                "password_confirm": _GOOD_PASSWORD + "!",
            }
        )
        resp = await c.create(_request(_super(), form=form))
        assert "error=" in _location(resp)
        c._user_store.create_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_csrf_failure_rejected(self) -> None:
        csrf = MagicMock()
        csrf.validate_token = MagicMock(return_value=False)
        c = _controller(csrf_service=csrf)
        c._user_store = _store([])
        form = _FakeForm({"csrf_token": "bogus"})
        resp = await c.create(_request(_super(), form=form))
        assert "error=" in _location(resp)
        c._user_store.create_user.assert_not_awaited()


class TestDeactivate:
    @pytest.mark.asyncio
    async def test_happy_path_updates_revokes_and_audits(self) -> None:
        records = [
            _record("me", is_superuser=True),
            _record("victim", roles=["editor"]),
        ]
        c = _controller()
        c._user_store = _store(records)
        c._audit_service = MagicMock(log_event=AsyncMock())
        c._session_service = MagicMock(revoke_all_user_sessions=AsyncMock())
        resp = await c.deactivate(_request(_super(), form=_FakeForm()), "victim")
        assert "notice=" in _location(resp)
        assert records[1].is_active is False
        c._user_store.update_user.assert_awaited_once()
        c._session_service.revoke_all_user_sessions.assert_awaited_once_with("victim")
        event = c._audit_service.log_event.await_args.kwargs
        assert event["event_type"] == AdminSecurityEventType.USER_DEACTIVATED

    @pytest.mark.asyncio
    async def test_self_deactivation_blocked(self) -> None:
        c = _controller()
        c._user_store = _store([_record("me", is_superuser=True)])
        resp = await c.deactivate(_request(_super(), form=_FakeForm()), "me")
        assert "error=" in _location(resp)
        c._user_store.update_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_last_superadmin_blocked_even_for_flag_holder(self) -> None:
        # Target is the only ACTIVE superadmin on record (permanent-flag
        # holder; the other super is already inactive). Unlike role
        # demotion, deactivation must count flag-holders, so this blocks.
        target = _record("root", is_superuser=True)
        others = [_record("old-admin", roles=["superadmin"], is_active=False)]
        c = _controller()
        c._user_store = _store([target, *others])
        resp = await c.deactivate(_request(_super(), form=_FakeForm()), "root")
        assert "error=" in _location(resp)
        assert "last+active+super" in _location(resp).replace("%20", "+")
        c._user_store.update_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_superadmin_deactivation_allowed_with_another_active_super(
        self,
    ) -> None:
        records = [
            _record("root", is_superuser=True),
            _record("root2", roles=["superadmin"]),
        ]
        c = _controller()
        c._user_store = _store(records)
        resp = await c.deactivate(_request(_super(), form=_FakeForm()), "root")
        assert "notice=" in _location(resp)
        assert records[0].is_active is False

    @pytest.mark.asyncio
    async def test_fail_closed_on_empty_listing(self) -> None:
        target = _record("root", is_superuser=True)
        c = _controller()
        c._user_store = _store([target])
        c._user_store.list_users = AsyncMock(side_effect=RuntimeError("db"))
        resp = await c.deactivate(_request(_super(), form=_FakeForm()), "root")
        assert "error=" in _location(resp)
        c._user_store.update_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_revocation_failure_does_not_fail_the_request(self) -> None:
        records = [
            _record("me", is_superuser=True),
            _record("victim", roles=[]),
        ]
        c = _controller()
        c._user_store = _store(records)
        c._session_service = MagicMock(
            revoke_all_user_sessions=AsyncMock(side_effect=RuntimeError("down"))
        )
        resp = await c.deactivate(_request(_super(), form=_FakeForm()), "victim")
        assert "notice=" in _location(resp)
        assert records[1].is_active is False


class TestActivate:
    @pytest.mark.asyncio
    async def test_reactivates_and_audits(self) -> None:
        records = [
            _record("me", is_superuser=True),
            _record("dormant", is_active=False),
        ]
        c = _controller()
        c._user_store = _store(records)
        c._audit_service = MagicMock(log_event=AsyncMock())
        resp = await c.activate(_request(_super(), form=_FakeForm()), "dormant")
        assert "notice=" in _location(resp)
        assert records[1].is_active is True
        event = c._audit_service.log_event.await_args.kwargs
        assert event["event_type"] == AdminSecurityEventType.USER_REACTIVATED

    @pytest.mark.asyncio
    async def test_already_active_is_a_noop_notice(self) -> None:
        records = [_record("me", is_superuser=True), _record("fine")]
        c = _controller()
        c._user_store = _store(records)
        resp = await c.activate(_request(_super(), form=_FakeForm()), "fine")
        assert "notice=" in _location(resp)
        c._user_store.update_user.assert_not_awaited()
