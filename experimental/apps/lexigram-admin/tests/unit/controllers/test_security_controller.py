"""Security Center controller tests (R12 — docs/09-01-2026/05-security-center.md)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.exceptions import HTTPException
from starlette.requests import Request

from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.controllers.security import (
    SecurityController,
    _fmt_ts,
    _short_id,
)


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


def _request(
    user: Any,
    session: dict | None = None,
    form: dict | None = None,
    query: dict | None = None,
    path: str = "/admin/security",
) -> MagicMock:
    req = MagicMock(spec=Request)
    # Request inherits __len__ from HTTPConnection; a spec'd MagicMock
    # defaults it to 0, making bool(request) False and tripping the
    # truthiness check inside middleware.auth.current_user.
    req.__len__ = MagicMock(return_value=1)
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


def _controller(**kwargs: Any) -> SecurityController:
    return SecurityController(renderer=MagicMock(), **kwargs)


class TestSuperAdminGate:
    def test_literal_superuser_flag_passes(self) -> None:
        c = _controller()
        assert c._is_super_admin(_FakeUser(is_superuser=True)) is True

    def test_magicmock_truthy_flag_is_rejected(self) -> None:
        """B1 regression: only a literal True flag counts."""
        c = _controller()
        assert c._is_super_admin(MagicMock()) is False

    def test_configured_role_passes(self) -> None:
        c = _controller(super_admin_role="root")
        assert c._is_super_admin(_FakeUser(roles=["root"])) is True

    def test_default_role_denied_under_configured_role(self) -> None:
        c = _controller(super_admin_role="root")
        assert c._is_super_admin(_FakeUser(roles=["superadmin"])) is False

    def test_plain_admin_denied(self) -> None:
        c = _controller()
        assert c._is_super_admin(_FakeUser(roles=["admin"])) is False

    def test_guard_redirects_guests_to_login(self) -> None:
        c = _controller()
        guest = _FakeUser(user_id="guest")
        response = c._guard(_request(guest))
        assert response is not None
        assert response.status_code == 302
        assert "/admin/login" in response.headers["location"]

    def test_guard_403_for_non_superadmin(self) -> None:
        c = _controller()
        with pytest.raises(HTTPException) as exc_info:
            c._guard(_request(_FakeUser(roles=["editor"])))
        assert exc_info.value.status_code == 403

    def test_guard_passes_superadmin(self) -> None:
        c = _controller()
        assert c._guard(_request(_FakeUser(roles=["superadmin"]))) is None


class TestHelpers:
    def test_redirect_uses_query_separator(self) -> None:
        c = _controller()
        r = c._redirect("/admin/security/sessions", "done")
        assert r.headers["location"] == "/admin/security/sessions?notice=done"

    def test_redirect_appends_with_ampersand_when_query_present(self) -> None:
        c = _controller()
        r = c._redirect("/admin/security/lockouts?email=a%40b.c", "ok")
        assert r.headers["location"].endswith("&notice=ok")

    def test_redirect_error_key(self) -> None:
        c = _controller()
        r = c._redirect("/x", "boom", is_error=True)
        assert "error=boom" in r.headers["location"]

    def test_short_id_truncates(self) -> None:
        assert _short_id("abcdefghijkl") == "abcdefgh…"
        assert _short_id("abc") == "abc"
        assert _short_id(None) == ""

    def test_fmt_ts_handles_none_and_microseconds(self) -> None:
        assert _fmt_ts(None) == "—"
        assert _fmt_ts("2026-09-01T10:00:00.123456+00:00") == "2026-09-01 10:00:00"


class TestRevokeSession:
    @pytest.mark.asyncio
    async def test_revokes_and_audits(self) -> None:
        session_service = MagicMock()
        session_service.revoke_session = AsyncMock()
        c = _controller(session_service=session_service)
        c._audit_service = MagicMock()
        c._audit_service.log_event = AsyncMock()
        req = _request(
            _FakeUser(is_superuser=True),
            session={"session_id": "mine"},
            form={"csrf_token": "", "session_id": "target-session"},
        )
        response = await c.revoke_session(req)
        session_service.revoke_session.assert_awaited_once_with("target-session")
        assert response.status_code == 302
        assert "notice=" in response.headers["location"]
        # The mount-time-wired audit service is used and attributed.
        c._audit_service.log_event.assert_awaited_once()
        kwargs = c._audit_service.log_event.await_args.kwargs
        assert kwargs["admin_user_id"] == "u-1"
        assert kwargs["metadata"]["source"] == "security_center"

    @pytest.mark.asyncio
    async def test_refuses_own_session(self) -> None:
        session_service = MagicMock()
        session_service.revoke_session = AsyncMock()
        c = _controller(session_service=session_service)
        req = _request(
            _FakeUser(is_superuser=True),
            session={"session_id": "mine"},
            form={"csrf_token": "", "session_id": "mine"},
        )
        response = await c.revoke_session(req)
        session_service.revoke_session.assert_not_awaited()
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_missing_session_id_is_an_error(self) -> None:
        c = _controller(session_service=MagicMock())
        req = _request(
            _FakeUser(is_superuser=True), session={}, form={"csrf_token": ""}
        )
        response = await c.revoke_session(req)
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_csrf_failure_rejected(self) -> None:
        csrf = MagicMock()
        csrf.validate_token.return_value = False
        session_service = MagicMock()
        session_service.revoke_session = AsyncMock()
        c = _controller(csrf_service=csrf, session_service=session_service)
        req = _request(
            _FakeUser(is_superuser=True),
            session={"csrf_session_id": "sid"},
            form={"csrf_token": "bad", "session_id": "x"},
        )
        response = await c.revoke_session(req)
        session_service.revoke_session.assert_not_awaited()
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_service_failure_is_friendly(self) -> None:
        session_service = MagicMock()
        session_service.revoke_session = AsyncMock(side_effect=RuntimeError("db"))
        c = _controller(session_service=session_service)
        req = _request(
            _FakeUser(is_superuser=True),
            session={},
            form={"csrf_token": "", "session_id": "x"},
        )
        response = await c.revoke_session(req)
        assert "error=" in response.headers["location"]
        assert "db" not in response.headers["location"]


class TestClearLockout:
    @pytest.mark.asyncio
    async def test_clears_and_audits(self) -> None:
        c = _controller()
        c._lockout_store = MagicMock()
        c._lockout_store.clear_lockout = AsyncMock()
        req = _request(
            _FakeUser(is_superuser=True),
            session={},
            form={"csrf_token": "", "email": "locked@example.com"},
        )
        response = await c.clear_lockout(req)
        c._lockout_store.clear_lockout.assert_awaited_once_with("locked@example.com")
        assert "notice=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_missing_email_is_an_error(self) -> None:
        c = _controller()
        c._lockout_store = MagicMock()
        req = _request(
            _FakeUser(is_superuser=True), session={}, form={"csrf_token": ""}
        )
        response = await c.clear_lockout(req)
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_no_store_is_an_error(self) -> None:
        c = _controller()
        req = _request(
            _FakeUser(is_superuser=True),
            session={},
            form={"csrf_token": "", "email": "a@b.c"},
        )
        response = await c.clear_lockout(req)
        assert "error=" in response.headers["location"]


class TestEmailMapping:
    @pytest.mark.asyncio
    async def test_maps_user_id_records(self) -> None:
        c = _controller()
        store = MagicMock()
        store.list_users = AsyncMock(
            return_value=[SimpleNamespace(user_id="u-1", email="a@b.c")]
        )
        c._user_store = store
        assert await c._email_by_user_id() == {"u-1": "a@b.c"}

    @pytest.mark.asyncio
    async def test_maps_dict_records(self) -> None:
        c = _controller()
        store = MagicMock()
        store.list_users = AsyncMock(return_value=[{"id": "u-2", "email": "x@y.z"}])
        c._user_store = store
        assert await c._email_by_user_id() == {"u-2": "x@y.z"}

    @pytest.mark.asyncio
    async def test_store_failure_returns_empty(self) -> None:
        c = _controller()
        store = MagicMock()
        store.list_users = AsyncMock(side_effect=RuntimeError("down"))
        c._user_store = store
        assert await c._email_by_user_id() == {}

    @pytest.mark.asyncio
    async def test_no_store_returns_empty(self) -> None:
        c = _controller()
        assert await c._email_by_user_id() == {}


class TestActiveLockoutList:
    """R41 (doc 37): fleet-wide active-lockout table on the Lockouts tab."""

    @pytest.mark.asyncio
    async def test_rows_render_with_unlock_forms(self) -> None:
        c = _controller()
        c._lockout_store = MagicMock()
        c._lockout_store.list_active_lockouts = AsyncMock(
            return_value=[
                {
                    "email": "locked@example.com",
                    "locked_at": "2026-09-02 10:00:00",
                    "unlock_at": "2026-09-02 10:15:00",
                    "consecutive_failures": 5,
                    "is_permanent": 0,
                },
                {
                    "email": "banned@example.com",
                    "locked_at": "2026-09-02 09:00:00",
                    "unlock_at": None,
                    "consecutive_failures": 50,
                    "is_permanent": 1,
                },
            ]
        )
        html = await c._active_lockouts_html(_request(_FakeUser(is_superuser=True)))
        assert "Active lockouts" in html
        assert "locked@example.com" in html
        assert "Auto-unlocks" in html
        assert "banned@example.com" in html
        assert "Permanent" in html
        assert html.count("/admin/security/lockouts/clear") == 2
        assert html.count(">Unlock</button>") == 2

    @pytest.mark.asyncio
    async def test_empty_state(self) -> None:
        c = _controller()
        c._lockout_store = MagicMock()
        c._lockout_store.list_active_lockouts = AsyncMock(return_value=[])
        html = await c._active_lockouts_html(_request(_FakeUser(is_superuser=True)))
        assert "No active lockouts." in html

    @pytest.mark.asyncio
    async def test_store_without_method_degrades_to_note(self) -> None:
        c = _controller()
        c._lockout_store = SimpleNamespace(get_active_lockout=AsyncMock())
        html = await c._active_lockouts_html(_request(_FakeUser(is_superuser=True)))
        assert "not supported" in html

    @pytest.mark.asyncio
    async def test_store_error_keeps_page_usable(self) -> None:
        c = _controller()
        c._lockout_store = MagicMock()
        c._lockout_store.list_active_lockouts = AsyncMock(
            side_effect=RuntimeError("db down")
        )
        html = await c._active_lockouts_html(_request(_FakeUser(is_superuser=True)))
        assert "Could not load" in html

    @pytest.mark.asyncio
    async def test_no_store_renders_nothing(self) -> None:
        c = _controller()
        c._lockout_store = None
        html = await c._active_lockouts_html(_request(_FakeUser(is_superuser=True)))
        assert html == ""


class TestLoginSparkline:
    """R43 (doc 39): hourly login-activity sparkline on the overview."""

    _NOW = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)

    def _event(self, etype: AdminSecurityEventType, created_at: Any) -> Any:
        return SimpleNamespace(event_type=etype, created_at=created_at)

    def test_buckets_land_at_the_right_offsets(self) -> None:
        events = [
            # 30 min ago -> current hour (rightmost bucket)
            self._event(
                AdminSecurityEventType.LOGIN_SUCCESS,
                self._NOW - timedelta(minutes=30),
            ),
            # 23.5 h ago -> oldest bucket (leftmost)
            self._event(
                AdminSecurityEventType.LOGIN_FAILURE,
                self._NOW - timedelta(hours=23, minutes=30),
            ),
            # 25 h ago -> outside the window, dropped
            self._event(
                AdminSecurityEventType.LOGIN_FAILURE,
                self._NOW - timedelta(hours=25),
            ),
        ]
        html = SecurityController._login_sparkline_html(events, now=self._NOW)
        assert 'data-testid="login-sparkline"' in html
        assert "1 successful · 1 failed" in html
        # leftmost bucket (x=0) is the failure; rightmost is the success
        assert '<rect x="0" ' in html
        assert 'x="276"' in html  # bucket 23 * (10 + 2)
        assert html.count("<rect") == 2

    def test_failure_bars_use_the_destructive_token(self) -> None:
        events = [
            self._event(AdminSecurityEventType.LOGIN_FAILURE, self._NOW)
        ]
        html = SecurityController._login_sparkline_html(events, now=self._NOW)
        assert "fill:var(--destructive)" in html
        assert "fill:var(--muted-foreground)" not in html

    def test_sqlite_string_timestamps_are_parsed(self) -> None:
        events = [
            self._event(
                AdminSecurityEventType.LOGIN_SUCCESS, "2026-09-02 11:45:00"
            )
        ]
        html = SecurityController._login_sparkline_html(events, now=self._NOW)
        assert "1 successful · 0 failed" in html

    def test_garbage_timestamps_are_skipped_not_fatal(self) -> None:
        events = [
            self._event(AdminSecurityEventType.LOGIN_SUCCESS, "not-a-time"),
            self._event(AdminSecurityEventType.LOGIN_SUCCESS, None),
        ]
        html = SecurityController._login_sparkline_html(events, now=self._NOW)
        assert "No login activity" in html

    def test_non_login_events_are_ignored(self) -> None:
        events = [
            self._event(AdminSecurityEventType.SESSION_REVOKED, self._NOW)
        ]
        html = SecurityController._login_sparkline_html(events, now=self._NOW)
        assert "No login activity" in html

    def test_empty_window_renders_empty_state(self) -> None:
        html = SecurityController._login_sparkline_html([], now=self._NOW)
        assert "No login activity" in html
        assert "<svg" not in html

    def test_cap_note_when_window_truncated(self) -> None:
        events = [
            self._event(AdminSecurityEventType.LOGIN_SUCCESS, self._NOW)
            for _ in range(250)
        ]
        html = SecurityController._login_sparkline_html(events, now=self._NOW)
        assert "window truncated at 250 events" in html
