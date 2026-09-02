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


class TestLiveAuditTail:
    """Live audit tail (R47 — docs/09-01-2026/43-live-audit-tail.md)."""

    @staticmethod
    def _event(**overrides: Any) -> SimpleNamespace:
        from lexigram.admin.auth.types import AdminSecurityEventType

        defaults = {
            "event_type": AdminSecurityEventType.LOGIN_FAILURE,
            "success": False,
            "admin_user_id": "u-1",
            "ip_address": "10.0.0.9",
            "created_at": "2026-09-02 10:00:00",
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def test_parse_live_flag_variants(self) -> None:
        c = _controller()
        for raw, expected in (
            ("1", True),
            ("true", True),
            ("on", True),
            ("", False),
            ("0", False),
            ("yes", False),
        ):
            *_, live = c._parse_audit_query({"live": raw})
            assert live is expected, raw
        *_, live = c._parse_audit_query({})
        assert live is False

    @pytest.mark.asyncio
    async def test_region_without_live_has_no_polling_attrs(self) -> None:
        c = _controller()
        req = _request(_FakeUser(is_superuser=True))
        html = await c._audit_table_region(req)
        assert 'id="security-audit-table"' in html
        assert "hx-get" not in html
        assert "hx-trigger" not in html
        assert "Live — refreshing" not in html

    @pytest.mark.asyncio
    async def test_live_region_polls_fragment_with_filters(self) -> None:
        from datetime import UTC, datetime

        c = _controller()
        store = SimpleNamespace(query_recent=AsyncMock(return_value=[]))
        c._audit_store = store
        req = _request(
            _FakeUser(is_superuser=True),
            query={
                "live": "1",
                "window": "1h",
                "limit": "50",
                "event_type": "login_failure",
                "user_id": "u-42",
            },
        )
        html = await c._audit_table_region(
            req, now=datetime(2026, 9, 2, 15, 4, 5, tzinfo=UTC)
        )
        assert 'hx-trigger="every 5s"' in html
        assert 'hx-swap="outerHTML"' in html
        assert "/admin/security/audit/table?" in html
        assert "window=1h" in html
        assert "limit=50" in html
        assert "live=1" in html
        assert "event_type=login_failure" in html
        assert "user_id=u-42" in html
        assert "updated 15:04:05 UTC" in html
        # The underlying query honours the same filters.
        kwargs = store.query_recent.await_args.kwargs
        assert kwargs["admin_user_id"] == "u-42"
        assert kwargs["limit"] == 50
        assert kwargs["since_seconds"] == 3600

    @pytest.mark.asyncio
    async def test_live_region_renders_event_rows(self) -> None:
        c = _controller()
        c._audit_store = SimpleNamespace(
            query_recent=AsyncMock(return_value=[self._event()])
        )
        req = _request(_FakeUser(is_superuser=True), query={"live": "1"})
        html = await c._audit_table_region(req)
        assert "login_failure" in html
        assert ">fail</span>" in html
        assert "10.0.0.9" in html

    @pytest.mark.asyncio
    async def test_user_filter_cannot_inject_markup(self) -> None:
        c = _controller()
        c._audit_store = SimpleNamespace(query_recent=AsyncMock(return_value=[]))
        req = _request(
            _FakeUser(is_superuser=True),
            query={"live": "1", "user_id": '"><script>alert(1)</script>'},
        )
        html = await c._audit_table_region(req)
        assert "<script>" not in html
        # urlencode() percent-escapes the payload inside the hx-get URL.
        assert "user_id=%22%3E%3Cscript%3E" in html

    @pytest.mark.asyncio
    async def test_store_error_degrades_to_empty_state(self) -> None:
        c = _controller()
        c._audit_store = SimpleNamespace(
            query_recent=AsyncMock(side_effect=OSError("db gone"))
        )
        req = _request(_FakeUser(is_superuser=True), query={"live": "1"})
        html = await c._audit_table_region(req)
        assert "No audit events match the current filters." in html
        assert 'hx-trigger="every 5s"' in html  # keeps polling for recovery

    @pytest.mark.asyncio
    async def test_fragment_route_returns_region_only(self) -> None:
        c = _controller()
        req = _request(
            _FakeUser(is_superuser=True), path="/admin/security/audit/table"
        )
        response = await c.audit_table_fragment(req)
        body = response.body.decode()
        assert body.startswith('<div id="security-audit-table"')
        assert "Sessions</a>" not in body  # no tabs — fragment, not a page

    @pytest.mark.asyncio
    async def test_fragment_route_gated(self) -> None:
        """Authed non-superadmins get the same 403 as every security page."""
        c = _controller()
        with pytest.raises(HTTPException):
            await c.audit_table_fragment(_request(_FakeUser()))


class TestCspEnforcementFlip:
    """CSP promotion workflow (R48 — docs/09-01-2026/44-csp-enforcement-flip.md)."""

    @staticmethod
    def _settings(
        enforced: str | None = None, report_only: str | None = None
    ) -> SimpleNamespace:
        values = {
            "admin.security.csp": enforced,
            "admin.security.csp_report_only": report_only,
        }

        async def get(key: str, default: object = None) -> object:
            return values.get(key, default)

        return SimpleNamespace(get=get, set=AsyncMock())

    # -- card ---------------------------------------------------------------

    def test_card_monitoring_off(self) -> None:
        from lexigram.admin.settings.panel.models import DEFAULT_CSP

        c = _controller()
        html = c._enforcement_card_html(
            _request(_FakeUser(is_superuser=True)), DEFAULT_CSP, None
        )
        assert "monitoring is <strong>off</strong>" in html
        assert "/csp/promote" not in html
        assert "/csp/rollback" not in html

    def test_card_strict_candidate_warns_and_requires_ack(self) -> None:
        from lexigram.admin.settings.panel.models import DEFAULT_CSP, STRICT_CSP

        c = _controller()
        html = c._enforcement_card_html(
            _request(_FakeUser(is_superuser=True)), DEFAULT_CSP, STRICT_CSP
        )
        assert html.count("⚠") == 3
        assert 'name="acknowledge"' in html
        assert "/csp/promote" in html

    def test_card_candidate_already_enforced(self) -> None:
        from lexigram.admin.settings.panel.models import DEFAULT_CSP

        c = _controller()
        html = c._enforcement_card_html(
            _request(_FakeUser(is_superuser=True)), DEFAULT_CSP, DEFAULT_CSP
        )
        assert "already the enforced policy" in html
        assert "/csp/promote" not in html

    def test_card_override_offers_rollback(self) -> None:
        c = _controller()
        html = c._enforcement_card_html(
            _request(_FakeUser(is_superuser=True)), "default-src 'none'", None
        )
        assert "/csp/rollback" in html
        assert "settings override" in html

    def test_card_shows_violation_counts(self) -> None:
        from lexigram.admin.settings.panel.models import DEFAULT_CSP, STRICT_CSP

        c = _controller()
        c._csp_store = SimpleNamespace(
            list_violations=lambda: [object(), object()], total_received=7
        )
        html = c._enforcement_card_html(
            _request(_FakeUser(is_superuser=True)), DEFAULT_CSP, STRICT_CSP
        )
        assert "7 report(s) received" in html
        assert "2 distinct violation(s)" in html

    # -- promote ------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_promote_without_settings_store_errors(self) -> None:
        c = _controller()
        req = _request(_FakeUser(is_superuser=True), form={"csrf_token": ""})
        resp = await c.csp_promote(req)
        assert "Settings+store+unavailable" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_promote_requires_active_monitoring(self) -> None:
        c = _controller()
        c._csp_settings = self._settings(report_only="off")
        req = _request(_FakeUser(is_superuser=True), form={"csrf_token": ""})
        resp = await c.csp_promote(req)
        assert "no+candidate" in resp.headers["location"]
        c._csp_settings.set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_promote_already_enforced_is_noop(self) -> None:
        from lexigram.admin.settings.panel.models import STRICT_CSP

        c = _controller()
        c._csp_settings = self._settings(enforced=STRICT_CSP)
        req = _request(_FakeUser(is_superuser=True), form={"csrf_token": ""})
        resp = await c.csp_promote(req)
        assert "already+enforced" in resp.headers["location"]
        c._csp_settings.set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_promote_strict_without_ack_blocked(self) -> None:
        c = _controller()
        c._csp_settings = self._settings()  # default enforced, strict candidate
        req = _request(_FakeUser(is_superuser=True), form={"csrf_token": ""})
        resp = await c.csp_promote(req)
        loc = resp.headers["location"]
        assert "acknowledgement" in loc
        assert "3+known+UI-compatibility" in loc
        c._csp_settings.set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_promote_strict_with_ack_writes_both_keys(self) -> None:
        from lexigram.admin.settings.panel.models import STRICT_CSP

        c = _controller()
        c._csp_settings = self._settings()
        audit = AsyncMock()
        c._audit_service = SimpleNamespace(log_event=audit)
        req = _request(
            _FakeUser(is_superuser=True),
            form={"csrf_token": "", "acknowledge": "1"},
        )
        resp = await c.csp_promote(req)
        assert "notice=" in resp.headers["location"]
        calls = {call.args[0]: call.args[1] for call in c._csp_settings.set.await_args_list}
        assert calls["admin.security.csp"] == STRICT_CSP
        assert calls["admin.security.csp_report_only"] == "off"
        meta = audit.await_args.kwargs["metadata"]
        assert meta["action"] == "csp_promote"
        assert meta["acknowledged"] is True
        assert meta["blockers"] == 3

    @pytest.mark.asyncio
    async def test_promote_compatible_candidate_needs_no_ack(self) -> None:
        from lexigram.admin.settings.panel.models import DEFAULT_CSP

        candidate = DEFAULT_CSP + "; report-to csp-endpoint"
        c = _controller()
        c._csp_settings = self._settings(report_only=candidate)
        req = _request(_FakeUser(is_superuser=True), form={"csrf_token": ""})
        resp = await c.csp_promote(req)
        assert "notice=" in resp.headers["location"]
        calls = {call.args[0]: call.args[1] for call in c._csp_settings.set.await_args_list}
        assert calls["admin.security.csp"] == candidate

    @pytest.mark.asyncio
    async def test_promote_with_violations_needs_ack(self) -> None:
        from lexigram.admin.settings.panel.models import DEFAULT_CSP

        candidate = DEFAULT_CSP + "; report-to csp-endpoint"
        c = _controller()
        c._csp_settings = self._settings(report_only=candidate)
        c._csp_store = SimpleNamespace(
            list_violations=lambda: [object()], total_received=1
        )
        req = _request(_FakeUser(is_superuser=True), form={"csrf_token": ""})
        resp = await c.csp_promote(req)
        assert "1+recorded+violation" in resp.headers["location"]
        c._csp_settings.set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_promote_csrf_failure_rejected(self) -> None:
        csrf = MagicMock()
        csrf.validate_token.return_value = False
        c = _controller(csrf_service=csrf)
        c._csp_settings = self._settings()
        req = _request(
            _FakeUser(is_superuser=True),
            session={"csrf_session_id": "sid"},
            form={"csrf_token": "bad"},
        )
        resp = await c.csp_promote(req)
        assert "error=" in resp.headers["location"]
        c._csp_settings.set.assert_not_awaited()

    # -- rollback -----------------------------------------------------------

    @pytest.mark.asyncio
    async def test_rollback_clears_override_and_restores_monitoring(self) -> None:
        c = _controller()
        c._csp_settings = self._settings(enforced="default-src 'none'")
        audit = AsyncMock()
        c._audit_service = SimpleNamespace(log_event=audit)
        req = _request(_FakeUser(is_superuser=True), form={"csrf_token": ""})
        resp = await c.csp_rollback(req)
        assert "notice=" in resp.headers["location"]
        calls = {call.args[0]: call.args[1] for call in c._csp_settings.set.await_args_list}
        assert calls["admin.security.csp"] == ""
        assert calls["admin.security.csp_report_only"] == ""
        assert audit.await_args.kwargs["metadata"]["action"] == "csp_rollback"

    @pytest.mark.asyncio
    async def test_rollback_without_settings_store_errors(self) -> None:
        c = _controller()
        req = _request(_FakeUser(is_superuser=True), form={"csrf_token": ""})
        resp = await c.csp_rollback(req)
        assert "Settings+store+unavailable" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_promote_and_rollback_gated(self) -> None:
        c = _controller()
        with pytest.raises(HTTPException):
            await c.csp_promote(_request(_FakeUser(), form={"csrf_token": ""}))
        with pytest.raises(HTTPException):
            await c.csp_rollback(_request(_FakeUser(), form={"csrf_token": ""}))
