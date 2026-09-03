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


def _session_row(sid: str, **extra: Any) -> dict:
    return {
        "session_id": sid,
        "admin_id": extra.get("admin_id", "u-2"),
        "ip_address": extra.get("ip_address", "10.0.0.1"),
        "user_agent": extra.get("user_agent", "curl/8"),
        "last_active_at": "2026-09-02 13:00:00",
        "expires_at": "2026-09-03 13:00:00",
    }


class TestSessionPanel:
    """R42 (doc 38): per-user session card on the edit page."""

    @pytest.mark.asyncio
    async def test_rows_render_with_revoke_and_revoke_all(self) -> None:
        c = _controller()
        c._session_service = MagicMock()
        c._session_service.list_user_sessions = AsyncMock(
            return_value=[_session_row("sess-aaaa-1111"), _session_row("sess-bbbb-2222")]
        )
        html = await c._sessions_html(
            _request(_FakeUser(user_id="u-1", is_superuser=True)), "u-2"
        )
        assert "Active sessions" in html
        assert "sess-aaa…" in html  # short id, never the full token
        assert "sess-aaaa-1111" not in html.replace(
            'value="sess-aaaa-1111"', ""
        )  # full id only inside the form value
        assert html.count(">Revoke</button>") == 2
        assert "Sign out everywhere" in html
        assert "/admin/users/u-2/sessions/revoke" in html
        assert "/admin/users/u-2/sessions/revoke-all" in html

    @pytest.mark.asyncio
    async def test_own_current_session_not_revocable(self) -> None:
        c = _controller()
        c._session_service = MagicMock()
        c._session_service.list_user_sessions = AsyncMock(
            return_value=[_session_row("sess-mine-0001", admin_id="u-1")]
        )
        req = _request(
            _FakeUser(user_id="u-1", is_superuser=True),
            session={"session_id": "sess-mine-0001"},
        )
        html = await c._sessions_html(req, "u-1")
        assert "this session" in html
        assert ">Revoke</button>" not in html
        assert "Sign out everywhere" not in html
        assert "Use Logout" in html

    @pytest.mark.asyncio
    async def test_service_without_method_degrades(self) -> None:
        c = _controller()
        c._session_service = SimpleNamespace(revoke_session=AsyncMock())
        html = await c._sessions_html(
            _request(_FakeUser(is_superuser=True)), "u-2"
        )
        assert "not supported" in html

    @pytest.mark.asyncio
    async def test_listing_error_keeps_page(self) -> None:
        c = _controller()
        c._session_service = MagicMock()
        c._session_service.list_user_sessions = AsyncMock(
            side_effect=RuntimeError("db down")
        )
        html = await c._sessions_html(
            _request(_FakeUser(is_superuser=True)), "u-2"
        )
        assert "Could not load" in html

    @pytest.mark.asyncio
    async def test_no_service_renders_nothing(self) -> None:
        c = _controller()
        c._session_service = None
        assert await c._sessions_html(
            _request(_FakeUser(is_superuser=True)), "u-2"
        ) == ""


class TestRevokeUserSession:
    """R42 (doc 38 §2.3): single-session revoke with ownership guard."""

    def _controller_with_sessions(self, sids: list[str]) -> Any:
        c = _controller()
        c._session_service = MagicMock()
        c._session_service.list_user_sessions = AsyncMock(
            return_value=[_session_row(s) for s in sids]
        )
        c._session_service.revoke_session = AsyncMock()
        return c

    @pytest.mark.asyncio
    async def test_revokes_owned_session(self) -> None:
        c = self._controller_with_sessions(["sess-target-01"])
        form = _FakeForm({"csrf_token": "", "session_id": "sess-target-01"})
        response = await c.revoke_session(
            _request(_FakeUser(is_superuser=True), form=form), "u-2"
        )
        c._session_service.revoke_session.assert_awaited_once_with("sess-target-01")
        assert "notice=" in response.headers["location"]
        assert "/admin/users/u-2/edit" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_foreign_session_id_rejected(self) -> None:
        """A session id belonging to another user must be refused."""
        c = self._controller_with_sessions(["sess-target-01"])
        form = _FakeForm({"csrf_token": "", "session_id": "sess-other-user"})
        response = await c.revoke_session(
            _request(_FakeUser(is_superuser=True), form=form), "u-2"
        )
        c._session_service.revoke_session.assert_not_awaited()
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_own_current_session_blocked(self) -> None:
        c = self._controller_with_sessions(["sess-mine-0001"])
        form = _FakeForm({"csrf_token": "", "session_id": "sess-mine-0001"})
        req = _request(
            _FakeUser(user_id="u-1", is_superuser=True),
            session={"session_id": "sess-mine-0001"},
            form=form,
        )
        response = await c.revoke_session(req, "u-1")
        c._session_service.revoke_session.assert_not_awaited()
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_missing_session_id_rejected(self) -> None:
        c = self._controller_with_sessions([])
        form = _FakeForm({"csrf_token": ""})
        response = await c.revoke_session(
            _request(_FakeUser(is_superuser=True), form=form), "u-2"
        )
        assert "error=" in response.headers["location"]


class TestRevokeAllUserSessions:
    """R42 (doc 38): sign-out-everywhere with self block."""

    @pytest.mark.asyncio
    async def test_revokes_all_for_other_user(self) -> None:
        c = _controller()
        c._session_service = MagicMock()
        c._session_service.revoke_all_user_sessions = AsyncMock()
        form = _FakeForm({"csrf_token": ""})
        response = await c.revoke_all_sessions(
            _request(_FakeUser(user_id="u-1", is_superuser=True), form=form), "u-2"
        )
        c._session_service.revoke_all_user_sessions.assert_awaited_once_with("u-2")
        assert "notice=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_self_blocked(self) -> None:
        c = _controller()
        c._session_service = MagicMock()
        c._session_service.revoke_all_user_sessions = AsyncMock()
        form = _FakeForm({"csrf_token": ""})
        response = await c.revoke_all_sessions(
            _request(_FakeUser(user_id="u-1", is_superuser=True), form=form), "u-1"
        )
        c._session_service.revoke_all_user_sessions.assert_not_awaited()
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_no_service_friendly_error(self) -> None:
        c = _controller()
        c._session_service = None
        form = _FakeForm({"csrf_token": ""})
        response = await c.revoke_all_sessions(
            _request(_FakeUser(is_superuser=True), form=form), "u-2"
        )
        assert "error=" in response.headers["location"]


class TestAdminInitiatedReset:
    """R44 (doc 40): Send password reset link from the user form."""

    def _controller_with_target(self) -> Any:
        from lexigram.contracts.core.result import Ok

        c = _controller()
        c._password_reset_service = MagicMock()
        c._password_reset_service.request_reset = AsyncMock(return_value=Ok(None))
        store = MagicMock()
        store.get_user_by_id = AsyncMock(
            return_value=SimpleNamespace(
                user_id="u-2", email="target@example.com", roles=[]
            )
        )
        c._user_store = store
        return c

    def _req(self, form: Any = None) -> MagicMock:
        req = _request(_FakeUser(user_id="u-1", is_superuser=True), form=form)
        req.base_url = "http://testserver/"
        return req

    @pytest.mark.asyncio
    async def test_sends_reset_with_target_email_and_request_context(self) -> None:
        c = self._controller_with_target()
        form = _FakeForm({"csrf_token": ""})
        response = await c.reset_password(self._req(form), "u-2")
        kwargs = c._password_reset_service.request_reset.await_args.kwargs
        assert kwargs["email"] == "target@example.com"
        assert kwargs["ip_address"] == "127.0.0.1"
        assert kwargs["base_url"] == "http://testserver/"
        assert "notice=" in response.headers["location"]
        assert "/admin/users/u-2/edit" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_rate_limit_error_surfaces(self) -> None:
        from lexigram.contracts.core.result import Err

        c = self._controller_with_target()
        c._password_reset_service.request_reset = AsyncMock(
            return_value=Err(ValueError("Too many password reset requests."))
        )
        form = _FakeForm({"csrf_token": ""})
        response = await c.reset_password(self._req(form), "u-2")
        assert "error=" in response.headers["location"]
        assert "Too+many" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_unknown_user_redirects_to_list(self) -> None:
        c = self._controller_with_target()
        c._user_store.get_user_by_id = AsyncMock(return_value=None)
        form = _FakeForm({"csrf_token": ""})
        response = await c.reset_password(self._req(form), "ghost")
        c._password_reset_service.request_reset.assert_not_awaited()
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_no_service_friendly_error(self) -> None:
        c = self._controller_with_target()
        c._password_reset_service = None
        form = _FakeForm({"csrf_token": ""})
        response = await c.reset_password(self._req(form), "u-2")
        assert "error=" in response.headers["location"]

    def test_card_renders_with_button(self) -> None:
        c = self._controller_with_target()
        html = c._account_actions_html(
            _request(_FakeUser(is_superuser=True)), "u-2", "target@example.com"
        )
        assert "Account actions" in html
        assert "Send password reset link" in html
        assert "/admin/users/u-2/reset-password" in html
        assert "target@example.com" in html

    def test_card_degrades_without_service(self) -> None:
        c = _controller()
        c._password_reset_service = None
        html = c._account_actions_html(
            _request(_FakeUser(is_superuser=True)), "u-2", "target@example.com"
        )
        assert "not\n available".replace("\n ", " ") in html


class TestEmailInvite:
    """R45 (doc 41): create account + emailed set-password invite."""

    def _controller(self) -> Any:
        from lexigram.contracts.core.result import Ok

        c = _controller()
        c._password_reset_service = MagicMock()
        c._password_reset_service.issue_invite = AsyncMock(return_value=Ok(None))
        store = MagicMock()
        store.get_user_by_email = AsyncMock(return_value=None)
        store.list_users = AsyncMock(return_value=[])
        store.create_user = AsyncMock(
            return_value=SimpleNamespace(user_id="u-new", email="new@example.com")
        )
        c._user_store = store
        return c

    def _req(self, form: Any) -> MagicMock:
        req = _request(_FakeUser(user_id="u-1", is_superuser=True), form=form)
        req.base_url = "http://testserver/"
        return req

    @pytest.mark.asyncio
    async def test_creates_account_and_sends_invite(self) -> None:
        c = self._controller()
        form = _FakeForm(
            {"csrf_token": "", "name": "New Admin", "email": "New@Example.com"},
            multi={"roles": ["editor"]},
        )
        response = await c.invite(self._req(form))
        create_kwargs = c._user_store.create_user.await_args.kwargs
        assert create_kwargs["email"] == "new@example.com"  # lowercased
        assert create_kwargs["roles"] == ["editor"]
        assert create_kwargs["hashed_password"]  # throwaway, never plain
        invite_kwargs = c._password_reset_service.issue_invite.await_args.kwargs
        assert invite_kwargs["email"] == "new@example.com"
        assert "notice=" in response.headers["location"]
        assert "Invite+sent" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_duplicate_email_blocks_before_creation(self) -> None:
        c = self._controller()
        c._user_store.get_user_by_email = AsyncMock(
            return_value=SimpleNamespace(user_id="u-2")
        )
        form = _FakeForm(
            {"csrf_token": "", "name": "X", "email": "new@example.com"}
        )
        response = await c.invite(self._req(form))
        c._user_store.create_user.assert_not_awaited()
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_missing_service_refuses_before_creating(self) -> None:
        c = self._controller()
        c._password_reset_service = None
        form = _FakeForm(
            {"csrf_token": "", "name": "X", "email": "new@example.com"}
        )
        response = await c.invite(self._req(form))
        c._user_store.create_user.assert_not_awaited()
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_invite_email_failure_names_the_retry_path(self) -> None:
        from lexigram.contracts.core.result import Err

        c = self._controller()
        c._password_reset_service.issue_invite = AsyncMock(
            return_value=Err(ValueError("smtp down"))
        )
        form = _FakeForm(
            {"csrf_token": "", "name": "X", "email": "new@example.com"}
        )
        response = await c.invite(self._req(form))
        c._user_store.create_user.assert_awaited()  # account exists
        location = response.headers["location"]
        assert "error=" in location
        assert "was+created" in location
        assert "reset+link" in location

    @pytest.mark.asyncio
    async def test_invalid_identity_rejected(self) -> None:
        c = self._controller()
        form = _FakeForm({"csrf_token": "", "name": "", "email": "not-an-email"})
        response = await c.invite(self._req(form))
        c._user_store.create_user.assert_not_awaited()
        assert "error=" in response.headers["location"]
