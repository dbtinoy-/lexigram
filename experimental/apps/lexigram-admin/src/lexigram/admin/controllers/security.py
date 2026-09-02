"""Security Center controller — sessions, audit log, lockouts (roadmap R12).

Superadmin-only operational visibility over the security data the admin
already captures: fleet-wide active sessions with remote revoke, a
filterable audit-log browser, and account-lockout lookup with manual
unlock. Design: docs/09-01-2026/05-security-center.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from secrets import token_hex
from typing import Any
from urllib.parse import quote_plus, urlencode

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from lexigram.admin.auth.models import AdminUser
from lexigram.admin.auth.next_url import build_login_redirect
from lexigram.admin.auth.protocols import (
    AdminAuditLogServiceProtocol,
    AdminCsrfServiceProtocol,
    AdminSessionServiceProtocol,
)
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.contracts.web import get, post
from lexigram.logging import get_logger

logger = get_logger(__name__)

__all__ = ["SecurityController"]

_WINDOWS: dict[str, tuple[str, int]] = {
    "1h": ("Last hour", 3600),
    "24h": ("Last 24 hours", 86400),
    "7d": ("Last 7 days", 604800),
    "30d": ("Last 30 days", 2592000),
}
_LIMITS = (50, 100, 250)


def _parse_ts(value: Any) -> datetime | None:
    """Parse an audit-row timestamp; None when unparseable (never fatal).

    Handles timezone-aware datetimes (Postgres drivers), naive datetimes
    and plain strings (SQLite hands TIMESTAMP columns back as text) —
    naive values are assumed UTC, matching how the stores write them.
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace(" ", "T"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _fmt_ts(value: Any) -> str:
    """Best-effort compact timestamp rendering for table cells."""
    if value is None:
        return "—"
    text = str(value)
    # Trim microseconds/timezone noise: "2026-09-01 14:20:33.123456+00:00"
    return text.split(".", maxsplit=1)[0].replace("T", " ")


def _short_id(value: Any, length: int = 8) -> str:
    """Truncate an identifier for display — never render full tokens."""
    text = str(value or "")
    return f"{text[:length]}…" if len(text) > length else text


class SecurityController(AdminController):
    """Security Center: sessions, audit browser, lockouts.

    Routes:
        GET  /admin/security                  - Overview
        GET  /admin/security/sessions         - Active sessions (all users)
        POST /admin/security/sessions/revoke  - Revoke a session
        GET  /admin/security/audit            - Audit-log browser
        GET  /admin/security/lockouts         - Lockout lookup
        POST /admin/security/lockouts/clear   - Manual unlock
        GET  /admin/security/csp              - CSP status + violations
        GET  /admin/security/csp/violations   - Violations fragment (HTMX)
    """

    prefix = "/security"

    def __init__(
        self,
        renderer: AdminRenderer,
        csrf_service: AdminCsrfServiceProtocol | None = None,
        session_service: AdminSessionServiceProtocol | None = None,
        super_admin_role: str = "superadmin",
    ) -> None:
        """Initialise the Security Center controller.

        Args:
            renderer: AdminRenderer for shell page rendering.
            csrf_service: CSRF token service (POST protection).
            session_service: Session lifecycle service (list/revoke).
            super_admin_role: Configured super-admin role name.
        """
        super().__init__(renderer=renderer)
        self._csrf_service = csrf_service
        self._session_service = session_service
        self._super_admin_role = super_admin_role
        # Wired best-effort at mount time (di/mount/controllers.py):
        self._audit_store: Any = None  # AdminAuditLogStoreProtocol
        self._audit_service: Any = None  # AdminAuditLogServiceProtocol
        self._lockout_store: Any = None  # AdminAccountLockoutStoreProtocol
        self._user_store: Any = None  # AdminUserStoreProtocol
        # Wired best-effort by _mount_csp_reporting (docs 30/31):
        self._csp_store: Any = None  # CspReportStore (shared with ingest)
        self._csp_settings: Any = None  # TenantConfigStore

    # -- access control -----------------------------------------------------

    def _is_super_admin(self, user: Any) -> bool:
        """Literal superuser flag OR the configured super-admin role (B1)."""
        if getattr(user, "is_superuser", False) is True:
            return True
        from lexigram.admin.rbac.super_admin import is_super_admin

        return bool(
            self._super_admin_role and is_super_admin(user, self._super_admin_role)
        )

    def _guard(self, request: Request) -> Response | None:
        """Redirect anonymous users to login; 403 non-superadmins."""
        user: AdminUser = self.current_user(request)
        if not user or getattr(user, "user_id", "guest") == "guest":
            return RedirectResponse(
                url=build_login_redirect(
                    self._admin_path(request, "/admin/login"),
                    str(request.url.path),
                ),
                status_code=302,
            )
        if not self._is_super_admin(user):
            logger.info(
                "security_center.denied",
                user_id=str(getattr(user, "user_id", "unknown")),
                path=request.url.path,
            )
            # R7: rendered as the styled Access Denied page for browsers.
            raise HTTPException(status_code=403, detail="Super admin required")
        return None

    # -- helpers ------------------------------------------------------------

    def _csrf_token(self, request: Request) -> str:
        """Return a CSRF token, creating and persisting the session id."""
        csrf_session_id = str(request.session.get("csrf_session_id", ""))
        if not csrf_session_id:
            csrf_session_id = token_hex(16)
            request.session["csrf_session_id"] = csrf_session_id
        if self._csrf_service is None:
            return ""
        return self._csrf_service.generate_token(csrf_session_id)

    def _csrf_ok(self, request: Request, csrf_token: str) -> bool:
        """Validate the submitted CSRF token against the session id."""
        if self._csrf_service is None:
            return True
        csrf_session_id = str(request.session.get("csrf_session_id", ""))
        return bool(
            csrf_session_id
            and self._csrf_service.validate_token(csrf_session_id, csrf_token)
        )

    @staticmethod
    def _redirect(url: str, message: str, is_error: bool = False) -> Response:
        """Return a 302 redirect carrying an error or notice flash param."""
        key = "error" if is_error else "notice"
        sep = "&" if "?" in url else "?"
        return RedirectResponse(
            url=f"{url}{sep}{key}={quote_plus(message)}", status_code=302
        )

    async def _audit(
        self,
        request: Request,
        event_type: AdminSecurityEventType,
        success: bool,
        **metadata: Any,
    ) -> None:
        """Append a security audit event attributed to the acting admin.

        Prefers the mount-time-wired audit service; falls back to a
        container lookup (request scope, then app state) for embedders
        that wire the controller manually.
        """
        try:
            audit_service = self._audit_service
            if audit_service is None:
                container = getattr(request.state, "container", None) or getattr(
                    request.app.state, "container", None
                )
                if container is None:
                    logger.warning(
                        "security_center.audit_skipped_no_container",
                        event_type=event_type.value,
                    )
                    return
                audit_service = await container.resolve(AdminAuditLogServiceProtocol)
            client = getattr(request, "client", None)
            user = self.current_user(request)
            acting_id = str(getattr(user, "user_id", "") or "") or None
            await audit_service.log_event(
                event_type=event_type,
                ip_address=getattr(client, "host", "unknown"),
                user_agent=request.headers.get("user-agent", "") or "",
                success=success,
                admin_user_id=acting_id,
                metadata=metadata,
            )
        except Exception:  # noqa: BLE001 — audit failures must not break requests
            logger.warning("security_center.audit_failed", event_type=event_type.value)

    async def _email_by_user_id(self) -> dict[str, str]:
        """Map admin user ids to emails for display, best-effort."""
        if self._user_store is None:
            return {}
        list_users = getattr(self._user_store, "list_users", None) or getattr(
            self._user_store, "get_all_users", None
        )
        if list_users is None:
            return {}
        try:
            users = await list_users()
        except Exception:  # noqa: BLE001 — display sugar only, never fatal
            logger.debug("security_center.user_listing_failed")
            return {}
        mapping: dict[str, str] = {}
        for u in users or []:
            if isinstance(u, dict):
                uid = str(u.get("user_id") or u.get("id") or "")
                email = str(u.get("email") or "")
            else:
                uid = str(getattr(u, "user_id", "") or getattr(u, "id", "") or "")
                email = str(getattr(u, "email", "") or "")
            if uid and email:
                mapping[uid] = email
        return mapping

    def _flash_from_query(self, request: Request, ctx: Any) -> None:
        """Surface ?notice=/?error= redirect params as flash messages."""
        error = request.query_params.get("error", "")
        notice = request.query_params.get("notice", "")
        if error:
            ctx.add_flash(error, "error")
        if notice:
            ctx.add_flash(notice, "success")

    async def _page(
        self, request: Request, html: str, title: str, crumb: str
    ) -> Response:
        """Render *html* in the admin shell with Security breadcrumbs."""
        from lexigram.admin.state.context import AdminContextManager

        async with AdminContextManager(request) as ctx:
            self._flash_from_query(request, ctx)
            crumbs = [("Home", self._admin_path(request))]
            if crumb != "Security":
                crumbs.append(
                    ("Security", self._admin_path(request, "/admin/security"))
                )
            return await self.render_admin(
                request,
                html,
                title=title,
                breadcrumbs=self.generate_breadcrumbs(*crumbs, current=crumb),
            )

    # -- shared page chrome ---------------------------------------------

    def _tabs(self, request: Request, active: str) -> str:
        """Sub-navigation tabs shared by all Security Center pages."""
        base = self._admin_path(request, "/admin/security")
        entries = (
            ("Overview", base, "overview"),
            ("Sessions", f"{base}/sessions", "sessions"),
            ("Audit log", f"{base}/audit", "audit"),
            ("Lockouts", f"{base}/lockouts", "lockouts"),
            ("CSP", f"{base}/csp", "csp"),
        )
        links = "".join(
            f'<a href="{escape(href)}" class="px-3 py-2 text-sm font-medium '
            + (
                "border-b-2 border-primary text-foreground"
                if key == active
                else "text-muted-foreground hover:text-foreground"
            )
            + f'">{escape(label)}</a>'
            for label, href, key in entries
        )
        return '<div class="flex gap-1 border-b border-border mb-6">' + links + "</div>"

    @staticmethod
    def _card(title: str, value: str, note: str = "") -> str:
        note_html = (
            f'<p class="text-xs text-muted-foreground mt-1">{escape(note)}</p>'
            if note
            else ""
        )
        return (
            '<div class="bg-card border border-border rounded-xl p-5">'
            f'<p class="text-sm text-muted-foreground">{escape(title)}</p>'
            f'<p class="text-2xl font-bold text-foreground mt-1">{escape(value)}</p>'
            f"{note_html}</div>"
        )

    @staticmethod
    def _table(headers: list[str], rows: list[str], empty: str) -> str:
        if not rows:
            return (
                '<div class="bg-card border border-border rounded-xl p-8 '
                'text-center text-muted-foreground">' + escape(empty) + "</div>"
            )
        head = "".join(
            '<th class="px-4 py-3 text-left text-xs font-medium '
            f'text-muted-foreground uppercase tracking-wider">{escape(h)}</th>'
            for h in headers
        )
        return (
            '<div class="bg-card border border-border rounded-xl overflow-x-auto">'
            '<table class="min-w-full divide-y divide-border">'
            f"<thead><tr>{head}</tr></thead>"
            '<tbody class="divide-y divide-border">' + "".join(rows) + "</tbody>"
            "</table></div>"
        )

    # -- routes -------------------------------------------------------------

    @get("/")
    async def overview(self, request: Request) -> Response:
        """Security Center landing page: live counts and quick links."""
        denied = self._guard(request)
        if denied is not None:
            return denied

        sessions: list[dict[str, Any]] = []
        list_sessions = getattr(self._session_service, "list_active_sessions", None)
        if list_sessions is not None:
            try:
                sessions = await list_sessions(limit=250)
            except Exception:  # noqa: BLE001 — overview must render regardless
                logger.warning("security_center.session_listing_failed")

        events: list[Any] = []
        if self._audit_store is not None:
            try:
                events = await self._audit_store.query_recent(
                    since_seconds=86400, limit=250
                )
            except Exception:  # noqa: BLE001 — overview must render regardless
                logger.warning("security_center.audit_query_failed")

        failures = sum(
            1
            for e in events
            if getattr(e, "event_type", None) == AdminSecurityEventType.LOGIN_FAILURE
        )
        unique_users = len(
            {str(s.get("admin_id", "")) for s in sessions if s.get("admin_id")}
        )

        cards = (
            self._card("Active sessions", str(len(sessions)), "across all admins")
            + self._card("Signed-in admins", str(unique_users), "distinct accounts")
            + self._card(
                "Failed logins (24h)",
                str(failures),
                "see the audit log for details",
            )
            + self._card("Audit events (24h)", str(len(events)), "all event types")
        )
        html = (
            self._tabs(request, "overview")
            + '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">'
            + cards
            + "</div>"
            + self._login_sparkline_html(events)
        )
        return await self._page(request, html, "Security", "Security")

    @staticmethod
    def _login_sparkline_html(events: list[Any], now: datetime | None = None) -> str:
        """Hourly login-activity sparkline (R43, doc 39).

        Buckets the audit events the overview already fetched —
        LOGIN_SUCCESS / LOGIN_FAILURE per hour over 24 h — into an
        inline SVG (CSP-safe: no script, no external assets). Rows with
        unparseable timestamps are skipped, never fatal.
        """
        now = now or datetime.now(UTC)
        buckets = 24
        successes = [0] * buckets
        failures = [0] * buckets
        parsed_any = False
        for e in events:
            etype = getattr(e, "event_type", None)
            if etype not in (
                AdminSecurityEventType.LOGIN_SUCCESS,
                AdminSecurityEventType.LOGIN_FAILURE,
            ):
                continue
            ts = _parse_ts(getattr(e, "created_at", None))
            if ts is None:
                continue
            age = (now - ts).total_seconds()
            if age < 0 or age >= buckets * 3600:
                continue
            # Oldest hour on the left, current hour on the right.
            idx = buckets - 1 - int(age // 3600)
            parsed_any = True
            if etype == AdminSecurityEventType.LOGIN_SUCCESS:
                successes[idx] += 1
            else:
                failures[idx] += 1

        heading = (
            '<h2 class="text-sm font-medium text-foreground mt-8 mb-3">'
            "Login activity</h2>"
        )
        if not parsed_any:
            return heading + (
                '<div class="bg-card border border-border rounded-xl p-8 '
                'text-center text-muted-foreground">No login activity in '
                "the last 24&nbsp;h.</div>"
            )

        bar_w, gap, chart_h = 10, 2, 48
        peak = max(s + f for s, f in zip(successes, failures, strict=True)) or 1
        rects = []
        for i in range(buckets):
            total = successes[i] + failures[i]
            if total == 0:
                continue
            x = i * (bar_w + gap)
            h_total = max(2, round(chart_h * total / peak))
            h_fail = max(2, round(h_total * failures[i] / total)) if failures[i] else 0
            h_ok = h_total - h_fail
            y = chart_h - h_total
            if h_fail:
                rects.append(
                    f'<rect x="{x}" y="{y}" width="{bar_w}" height="{h_fail}" '
                    'style="fill:var(--destructive)" rx="1"><title>'
                    f"{failures[i]} failed</title></rect>"
                )
            if h_ok:
                rects.append(
                    f'<rect x="{x}" y="{y + h_fail}" width="{bar_w}" '
                    f'height="{h_ok}" '
                    'style="fill:var(--muted-foreground);fill-opacity:.6" rx="1">'
                    f"<title>{successes[i]} successful</title></rect>"
                )
        width = buckets * (bar_w + gap) - gap
        total_ok, total_fail = sum(successes), sum(failures)
        cap_note = " · window truncated at 250 events" if len(events) >= 250 else ""
        return heading + (
            '<div class="bg-card border border-border rounded-xl p-5" '
            'data-testid="login-sparkline">'
            f'<svg viewBox="0 0 {width} {chart_h}" width="{width}" '
            f'height="{chart_h}" role="img" aria-label="Login attempts per '
            'hour, last 24 hours" class="block">'
            + "".join(rects)
            + "</svg>"
            + '<p class="text-xs text-muted-foreground mt-2">'
            f"{total_ok} successful · {total_fail} failed · hourly, oldest "
            f"left · last 24 h{escape(cap_note)}</p></div>"
        )

    # -- CSP tab (docs 30/31) --------------------------------------------

    @get("/csp")
    async def csp_page(self, request: Request) -> Response:
        """CSP status: enforced/report-only policies + violation reports."""
        denied = self._guard(request)
        if denied is not None:
            return denied

        from lexigram.admin.services.security.pages import (
            render_csp_cards,
            render_csp_violations_region,
            resolve_csp_policies,
        )

        base = self._admin_path(request, "/admin/security")
        enforced, report_only, ro_status = await resolve_csp_policies(
            self._csp_settings
        )
        html = (
            self._tabs(request, "csp")
            + '<div class="space-y-6">'
            + render_csp_cards(
                enforced,
                report_only,
                ro_status,
                report_endpoint=f"{base}/csp-report",
            )
            + self._enforcement_card_html(request, enforced, report_only)
            + render_csp_violations_region(
                self._csp_store, fragment_url=f"{base}/csp/violations"
            )
            + "</div>"
        )
        return await self._page(request, html, "Content Security Policy", "CSP")

    @get("/csp/violations")
    async def csp_violations_fragment(self, request: Request) -> Response:
        """Violations region only, for HTMX polling swaps."""
        denied = self._guard(request)
        if denied is not None:
            return denied

        from starlette.responses import HTMLResponse

        from lexigram.admin.services.security.pages import (
            render_csp_violations_region,
        )

        base = self._admin_path(request, "/admin/security")
        return HTMLResponse(
            render_csp_violations_region(
                self._csp_store, fragment_url=f"{base}/csp/violations"
            )
        )

    def _enforcement_card_html(
        self,
        request: Request,
        enforced: str,
        report_only: str | None,
    ) -> str:
        """Enforcement card: readiness + promote/rollback actions (R48).

        Design: docs/09-01-2026/44-csp-enforcement-flip.md. Promotion is
        ack-gated (not refused) when the candidate would break the stock
        UI or violations were recorded — deployments that migrated their
        front-end can still flip, everyone else is warned in plain words.
        """
        from lexigram.admin.services.security.promotion import ui_compat_blockers
        from lexigram.admin.settings.panel.models import DEFAULT_CSP

        base = self._admin_path(request, "/admin/security/csp")
        overridden = enforced != DEFAULT_CSP
        source_note = (
            "settings override (<code>admin.security.csp</code>)"
            if overridden
            else "compile-time default"
        )
        monitoring_on = bool(report_only)

        violations = 0
        received = 0
        if self._csp_store is not None:
            try:
                violations = len(self._csp_store.list_violations())
                received = int(getattr(self._csp_store, "total_received", 0))
            except Exception:  # noqa: BLE001 — card must render regardless
                logger.warning("security_center.csp_store_read_failed")

        blockers = ui_compat_blockers(report_only) if report_only else []
        needs_ack = bool(blockers) or violations > 0

        rows = [
            f'<p class="text-sm text-muted-foreground">Enforced policy source: {source_note}.</p>'
        ]
        if monitoring_on:
            rows.append(
                '<p class="text-sm text-muted-foreground">Report-only monitoring: '
                f"<strong>on</strong> · {received} report(s) received · "
                f"{violations} distinct violation(s). The violation store is "
                "in-memory and resets on restart — judge readiness over a "
                "representative uptime window.</p>"
            )
        else:
            rows.append(
                '<p class="text-sm text-muted-foreground">Report-only monitoring '
                "is <strong>off</strong> — enable it (settings key "
                "<code>admin.security.csp_report_only</code>) and drive "
                "violations to zero before promoting.</p>"
            )
        for blocker in blockers:
            rows.append(
                f'<p class="text-sm text-destructive mt-2">⚠ {escape(blocker)}</p>'
            )

        actions = ""
        if monitoring_on and report_only != enforced:
            ack = ""
            if needs_ack:
                ack = (
                    '<label class="flex items-start gap-2 text-sm text-muted-foreground mt-3">'
                    '<input type="checkbox" name="acknowledge" value="1" class="mt-1">'
                    "I understand the warnings above and want to enforce this "
                    "policy anyway.</label>"
                )
            actions += (
                f'<form method="post" action="{escape(base)}/promote" class="mt-4">'
                f'<input type="hidden" name="csrf_token" value="{escape(self._csrf_token(request))}">'
                f"{ack}"
                f'<button type="submit" class="rounded-lg bg-primary text-primary-foreground '
                'px-4 py-2 text-sm font-medium mt-3">Promote candidate to enforced</button>'
                "</form>"
            )
        elif monitoring_on and report_only == enforced:
            actions += (
                '<p class="text-sm text-muted-foreground mt-3">The candidate '
                "policy is already the enforced policy.</p>"
            )
        if overridden:
            actions += (
                f'<form method="post" action="{escape(base)}/rollback" class="mt-3">'
                f'<input type="hidden" name="csrf_token" value="{escape(self._csrf_token(request))}">'
                '<button type="submit" class="rounded-lg border border-border '
                'px-4 py-2 text-sm font-medium">Roll back to the compile-time '
                "default</button></form>"
            )

        return (
            '<div class="bg-card border border-border rounded-xl p-6">'
            '<h2 class="text-sm font-medium">Enforcement</h2>'
            + "".join(rows)
            + actions
            + "</div>"
        )

    @post("/csp/promote")
    async def csp_promote(self, request: Request) -> Response:
        """Promote the report-only candidate policy to enforcement."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/security/csp")
        form = request.scope.get("admin_form_data") or await request.form()
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(base, "Invalid or expired form token.", True)
        if self._csp_settings is None:
            return self._redirect(
                base, "Settings store unavailable — cannot change policies.", True
            )

        from lexigram.admin.services.security.pages import resolve_csp_policies
        from lexigram.admin.services.security.promotion import ui_compat_blockers

        enforced, report_only, _ = await resolve_csp_policies(self._csp_settings)
        if not report_only:
            return self._redirect(
                base,
                "Report-only monitoring is off — there is no candidate "
                "policy to promote.",
                True,
            )
        if report_only == enforced:
            return self._redirect(
                base, "The candidate policy is already enforced.", False
            )

        blockers = ui_compat_blockers(report_only)
        violations = 0
        if self._csp_store is not None:
            try:
                violations = len(self._csp_store.list_violations())
            except Exception:  # noqa: BLE001 — treat unreadable store as zero
                logger.warning("security_center.csp_store_read_failed")
        acknowledged = str(form.get("acknowledge", "")) == "1"
        if (blockers or violations > 0) and not acknowledged:
            reasons = []
            if blockers:
                reasons.append(f"{len(blockers)} known UI-compatibility issue(s)")
            if violations > 0:
                reasons.append(f"{violations} recorded violation(s)")
            return self._redirect(
                base,
                "Promotion needs explicit acknowledgement: "
                + " and ".join(reasons)
                + ". Tick the checkbox to proceed anyway.",
                True,
            )

        try:
            await self._csp_settings.set("admin.security.csp", report_only)
            # Report-only of the now-enforced policy is pure noise.
            await self._csp_settings.set("admin.security.csp_report_only", "off")
        except Exception:  # noqa: BLE001 — surface the failure, change nothing else
            logger.warning("security_center.csp_promote_write_failed")
            return self._redirect(
                base, "Saving the policy failed — nothing was changed.", True
            )
        await self._audit(
            request,
            AdminSecurityEventType.SETTINGS_UPDATED,
            True,
            source="csp_tab",
            action="csp_promote",
            policy_length=len(report_only),
            acknowledged=acknowledged,
            blockers=len(blockers),
            violations=violations,
        )
        logger.info("security_center.csp_promoted", policy_length=len(report_only))
        return self._redirect(
            base,
            "Candidate policy promoted to enforcement. Headers update "
            "within 30 seconds; use Roll back if anything breaks.",
            False,
        )

    @post("/csp/rollback")
    async def csp_rollback(self, request: Request) -> Response:
        """Revert the enforced policy to the compile-time default."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/security/csp")
        form = request.scope.get("admin_form_data") or await request.form()
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(base, "Invalid or expired form token.", True)
        if self._csp_settings is None:
            return self._redirect(
                base, "Settings store unavailable — cannot change policies.", True
            )
        try:
            # Empty string ⇒ middleware falls back to DEFAULT_CSP; empty
            # report-only ⇒ strict candidate monitoring resumes (doc 30).
            await self._csp_settings.set("admin.security.csp", "")
            await self._csp_settings.set("admin.security.csp_report_only", "")
        except Exception:  # noqa: BLE001 — surface the failure, change nothing else
            logger.warning("security_center.csp_rollback_write_failed")
            return self._redirect(
                base, "Saving the rollback failed — nothing was changed.", True
            )
        await self._audit(
            request,
            AdminSecurityEventType.SETTINGS_UPDATED,
            True,
            source="csp_tab",
            action="csp_rollback",
        )
        logger.info("security_center.csp_rolled_back")
        return self._redirect(
            base,
            "Enforced policy reverted to the compile-time default; "
            "report-only monitoring restored. Headers update within "
            "30 seconds.",
            False,
        )

    @get("/sessions")
    async def sessions_page(self, request: Request) -> Response:
        """Fleet-wide active session list with remote revoke."""
        denied = self._guard(request)
        if denied is not None:
            return denied

        sessions: list[dict[str, Any]] = []
        supported = False
        list_sessions = getattr(self._session_service, "list_active_sessions", None)
        if list_sessions is not None:
            supported = True
            try:
                sessions = await list_sessions(limit=250)
            except Exception:  # noqa: BLE001 — page must render regardless
                logger.warning("security_center.session_listing_failed")

        emails = await self._email_by_user_id()
        current_session_id = str(request.session.get("session_id", ""))
        csrf = self._csrf_token(request)
        revoke_url = self._admin_path(request, "/admin/security/sessions/revoke")

        rows = []
        for s in sessions:
            sid = str(s.get("session_id", ""))
            admin_id = str(s.get("admin_id", ""))
            who = emails.get(admin_id) or _short_id(admin_id)
            is_current = sid == current_session_id
            action = (
                '<span class="text-xs text-muted-foreground">this session</span>'
                if is_current
                else (
                    f'<form method="post" action="{escape(revoke_url)}" class="inline">'
                    f'<input type="hidden" name="csrf_token" value="{escape(csrf)}">'
                    f'<input type="hidden" name="session_id" value="{escape(sid)}">'
                    '<button type="submit" class="text-sm font-medium '
                    'text-destructive hover:underline">Revoke</button></form>'
                )
            )
            rows.append(
                "<tr>"
                f'<td class="px-4 py-3 text-sm font-mono">{escape(_short_id(sid))}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(who)}'
                + (
                    ' <span class="text-xs text-primary font-medium">(you)</span>'
                    if is_current
                    else ""
                )
                + "</td>"
                f'<td class="px-4 py-3 text-sm">{escape(str(s.get("ip_address") or "—"))}</td>'
                f'<td class="px-4 py-3 text-sm text-muted-foreground max-w-[16rem] truncate">{escape(str(s.get("user_agent") or "—"))}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(_fmt_ts(s.get("last_active_at")))}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(_fmt_ts(s.get("expires_at")))}</td>'
                f'<td class="px-4 py-3 text-sm">{action}</td>'
                "</tr>"
            )

        empty = (
            "No active sessions."
            if supported
            else "The configured session service does not support fleet listing."
        )
        html = self._tabs(request, "sessions") + self._table(
            ["Session", "Admin", "IP", "User agent", "Last active", "Expires", ""],
            rows,
            empty,
        )
        return await self._page(request, html, "Sessions — Security", "Sessions")

    @post("/sessions/revoke")
    async def revoke_session(self, request: Request) -> Response:
        """Revoke a session remotely (CSRF-protected, audited)."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        back = self._admin_path(request, "/admin/security/sessions")

        # The CSRF middleware already consumed the body and cached the form.
        form = request.scope.get("admin_form_data") or await request.form()
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(back, "Invalid or expired form token.", True)
        session_id = str(form.get("session_id", "")).strip()
        if not session_id:
            return self._redirect(back, "Missing session id.", True)
        if session_id == str(request.session.get("session_id", "")):
            return self._redirect(back, "Use Logout to end your own session.", True)
        if self._session_service is None:
            return self._redirect(back, "Session service unavailable.", True)

        user = self.current_user(request)
        try:
            await self._session_service.revoke_session(session_id)
        except Exception:  # noqa: BLE001 — surface a friendly error, log the rest
            logger.exception("security_center.revoke_failed")
            return self._redirect(back, "Could not revoke the session.", True)

        await self._audit(
            request,
            AdminSecurityEventType.SESSION_REVOKED,
            True,
            revoked_session_id=_short_id(session_id),
            acting_admin_id=str(getattr(user, "user_id", "")),
            source="security_center",
        )
        logger.info(
            "security_center.session_revoked",
            session_id=_short_id(session_id),
            acting_admin_id=str(getattr(user, "user_id", "")),
        )
        return self._redirect(back, "Session revoked.")

    @staticmethod
    def _parse_audit_query(
        q: Any,
    ) -> tuple[str, int, AdminSecurityEventType | None, str | None, bool]:
        """Normalise audit-browser query params (shared by page + fragment).

        Args:
            q: Query-params mapping.

        Returns:
            ``(window_key, limit, event_type, user_filter, live)`` with
            unknown windows/limits/event types already coerced to defaults.
        """
        window_key = q.get("window", "24h")
        if window_key not in _WINDOWS:
            window_key = "24h"
        try:
            limit = int(q.get("limit", "100"))
        except ValueError:
            limit = 100
        if limit not in _LIMITS:
            limit = 100
        raw_type = q.get("event_type", "")
        event_type: AdminSecurityEventType | None = None
        if raw_type:
            try:
                event_type = AdminSecurityEventType(raw_type)
            except ValueError:
                event_type = None
        user_filter = q.get("user_id", "").strip() or None
        live = q.get("live", "") in ("1", "true", "on")
        return window_key, limit, event_type, user_filter, live

    async def _audit_table_region(
        self, request: Request, now: datetime | None = None
    ) -> str:
        """Audit table region — the htmx swap target for the live tail.

        Live audit tail (R47, docs/09-01-2026/43-live-audit-tail.md):
        with ``live=1`` the region carries htmx polling attributes whose
        fragment URL preserves the current filters, so the live view and
        the filtered view can never disagree. Without ``live`` no polling
        attributes render (CSP-region rationale: never poll a region that
        cannot change on its own).

        Args:
            request: Current request (query params define the filters).
            now: Injectable clock for the "updated" caption (tests).

        Returns:
            ``<div id="security-audit-table">…</div>`` HTML.
        """
        window_key, limit, event_type, user_filter, live = self._parse_audit_query(
            request.query_params
        )
        events: list[Any] = []
        if self._audit_store is not None:
            try:
                events = await self._audit_store.query_recent(
                    admin_user_id=user_filter,
                    event_type=event_type,
                    since_seconds=_WINDOWS[window_key][1],
                    limit=limit,
                )
            except Exception:  # noqa: BLE001 — page must render regardless
                logger.warning("security_center.audit_query_failed")

        emails = await self._email_by_user_id()
        rows = []
        for e in events:
            ok = getattr(e, "success", False) is True
            badge = (
                '<span class="text-xs font-medium text-green-600">ok</span>'
                if ok
                else '<span class="text-xs font-medium text-destructive">fail</span>'
            )
            uid = str(getattr(e, "admin_user_id", "") or "")
            who = emails.get(uid) or (_short_id(uid) if uid else "—")
            etype = getattr(e, "event_type", None)
            rows.append(
                "<tr>"
                f'<td class="px-4 py-3 text-sm">{escape(_fmt_ts(getattr(e, "created_at", None)))}</td>'
                f'<td class="px-4 py-3 text-sm font-medium">{escape(getattr(etype, "value", str(etype)))}</td>'
                f'<td class="px-4 py-3 text-sm">{badge}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(who)}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(str(getattr(e, "ip_address", "") or "—"))}</td>'
                "</tr>"
            )
        table = self._table(
            ["Time", "Event", "Result", "Admin", "IP"],
            rows,
            "No audit events match the current filters.",
        )

        attrs = ""
        caption = ""
        if live:
            params: dict[str, str] = {
                "window": window_key,
                "limit": str(limit),
                "live": "1",
            }
            if event_type is not None:
                params["event_type"] = event_type.value
            if user_filter:
                params["user_id"] = user_filter
            url = (
                self._admin_path(request, "/admin/security/audit/table")
                + "?"
                + urlencode(params)
            )
            attrs = f' hx-get="{escape(url)}" hx-trigger="every 5s" hx-swap="outerHTML"'
            ts = (now or datetime.now(UTC)).strftime("%H:%M:%S")
            caption = (
                '<p class="text-xs text-muted-foreground mb-2">'
                f"Live — refreshing every 5 s · updated {ts} UTC</p>"
            )
        return f'<div id="security-audit-table"{attrs}>{caption}{table}</div>'

    @get("/audit")
    async def audit_page(self, request: Request) -> Response:
        """Filterable audit-log browser with an optional live tail."""
        denied = self._guard(request)
        if denied is not None:
            return denied

        window_key, limit, event_type, user_filter, live = self._parse_audit_query(
            request.query_params
        )

        type_options = '<option value="">All events</option>' + "".join(
            f'<option value="{escape(t.value)}"'
            + (" selected" if event_type is not None and t is event_type else "")
            + f">{escape(t.value)}</option>"
            for t in AdminSecurityEventType
        )
        window_options = "".join(
            f'<option value="{escape(key)}"'
            + (" selected" if key == window_key else "")
            + f">{escape(label)}</option>"
            for key, (label, _) in _WINDOWS.items()
        )
        limit_options = "".join(
            f'<option value="{n}"'
            + (" selected" if n == limit else "")
            + f">{n}</option>"
            for n in _LIMITS
        )
        select_cls = "rounded-lg border border-border bg-background px-3 py-2 text-sm"
        filters = (
            f'<form method="get" class="flex flex-wrap items-end gap-3 mb-4">'
            f'<label class="text-sm text-muted-foreground">Event'
            f'<select name="event_type" class="{select_cls} block mt-1">{type_options}</select></label>'
            f'<label class="text-sm text-muted-foreground">Window'
            f'<select name="window" class="{select_cls} block mt-1">{window_options}</select></label>'
            f'<label class="text-sm text-muted-foreground">Limit'
            f'<select name="limit" class="{select_cls} block mt-1">{limit_options}</select></label>'
            f'<label class="text-sm text-muted-foreground">User id'
            f'<input type="text" name="user_id" value="{escape(user_filter or "")}" '
            f'placeholder="all users" class="{select_cls} block mt-1"></label>'
            '<label class="text-sm text-muted-foreground flex items-center gap-2 pb-2">'
            f'<input type="checkbox" name="live" value="1"{" checked" if live else ""}>'
            "Live</label>"
            '<button type="submit" class="rounded-lg bg-primary text-primary-foreground '
            'px-4 py-2 text-sm font-medium">Filter</button></form>'
        )

        html = (
            self._tabs(request, "audit")
            + filters
            + await self._audit_table_region(request)
        )
        return await self._page(request, html, "Audit log — Security", "Audit log")

    @get("/audit/table")
    async def audit_table_fragment(self, request: Request) -> Response:
        """Audit table region only, for HTMX live-tail polling swaps."""
        denied = self._guard(request)
        if denied is not None:
            return denied

        from starlette.responses import HTMLResponse

        return HTMLResponse(await self._audit_table_region(request))

    @get("/lockouts")
    async def lockouts_page(self, request: Request) -> Response:
        """Lockout lookup by email, with manual unlock."""
        denied = self._guard(request)
        if denied is not None:
            return denied

        email = request.query_params.get("email", "").strip()
        result_html = ""
        if email and self._lockout_store is not None:
            info = None
            try:
                info = await self._lockout_store.get_active_lockout(email)
            except Exception:  # noqa: BLE001 — page must render regardless
                logger.warning("security_center.lockout_lookup_failed")
            if info is None:
                result_html = (
                    '<div class="bg-card border border-border rounded-xl p-5 '
                    'text-sm text-muted-foreground">No active lockout for '
                    f"<strong>{escape(email)}</strong>.</div>"
                )
            else:
                csrf = self._csrf_token(request)
                clear_url = self._admin_path(request, "/admin/security/lockouts/clear")
                kind = (
                    "Permanent — manual unlock required"
                    if getattr(info, "is_permanent", False) is True
                    else f"Temporary — auto-unlocks at {_fmt_ts(getattr(info, 'unlock_at', None))}"
                )
                result_html = (
                    '<div class="bg-card border border-destructive/30 rounded-xl p-5">'
                    f'<p class="text-sm font-medium text-foreground">'
                    f"{escape(email)} is locked out</p>"
                    f'<p class="text-sm text-muted-foreground mt-1">{escape(kind)}</p>'
                    f'<p class="text-sm text-muted-foreground">Consecutive failures: '
                    f"{int(getattr(info, 'consecutive_failures', 0) or 0)} · Locked at: "
                    f"{escape(_fmt_ts(getattr(info, 'locked_at', None)))}</p>"
                    f'<form method="post" action="{escape(clear_url)}" class="mt-3">'
                    f'<input type="hidden" name="csrf_token" value="{escape(csrf)}">'
                    f'<input type="hidden" name="email" value="{escape(email)}">'
                    '<button type="submit" class="rounded-lg bg-primary '
                    'text-primary-foreground px-4 py-2 text-sm font-medium">'
                    "Unlock account</button></form></div>"
                )
        elif email:
            result_html = (
                '<div class="bg-card border border-border rounded-xl p-5 '
                'text-sm text-muted-foreground">Lockout store unavailable.</div>'
            )

        lookup_url = self._admin_path(request, "/admin/security/lockouts")
        form = (
            f'<form method="get" action="{escape(lookup_url)}" '
            'class="flex items-end gap-3 mb-4">'
            '<label class="text-sm text-muted-foreground">Account email'
            f'<input type="email" name="email" value="{escape(email)}" required '
            'placeholder="admin@example.com" class="rounded-lg border border-border '
            'bg-background px-3 py-2 text-sm block mt-1 min-w-[18rem]"></label>'
            '<button type="submit" class="rounded-lg bg-primary '
            'text-primary-foreground px-4 py-2 text-sm font-medium">'
            "Check</button></form>"
        )
        fleet_html = await self._active_lockouts_html(request)
        html = self._tabs(request, "lockouts") + form + result_html + fleet_html
        return await self._page(request, html, "Lockouts — Security", "Lockouts")

    async def _active_lockouts_html(self, request: Request) -> str:
        """Fleet-wide active-lockout table (R41, doc 37 §2.2).

        Duck-typed against ``list_active_lockouts`` so stores predating
        the protocol addition degrade to a note instead of a 500;
        listing errors are logged and the rest of the page still works.
        """
        if self._lockout_store is None:
            return ""
        heading = (
            '<h2 class="text-sm font-medium text-foreground mt-8 mb-3">'
            "Active lockouts</h2>"
        )
        lister = getattr(self._lockout_store, "list_active_lockouts", None)
        if not callable(lister):
            return heading + (
                '<div class="bg-card border border-border rounded-xl p-5 '
                'text-sm text-muted-foreground">Listing is not supported by '
                "this lockout store — use the lookup above.</div>"
            )
        try:
            lockouts = await lister(limit=100)
        except Exception:  # noqa: BLE001 — the lookup form must keep working
            logger.warning("security_center.lockout_list_failed")
            return heading + (
                '<div class="bg-card border border-border rounded-xl p-5 '
                'text-sm text-muted-foreground">Could not load the lockout '
                "list — check the server log.</div>"
            )
        csrf = self._csrf_token(request)
        clear_url = self._admin_path(request, "/admin/security/lockouts/clear")
        rows = []
        for row in lockouts:
            row = dict(row)
            row_email = str(row.get("email", "") or "")
            kind = (
                "Permanent"
                if bool(row.get("is_permanent", False))
                else f"Auto-unlocks {_fmt_ts(row.get('unlock_at'))}"
            )
            rows.append(
                "<tr>"
                f'<td class="px-4 py-3 text-sm font-medium">{escape(row_email)}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(kind)}</td>'
                f'<td class="px-4 py-3 text-sm">'
                f"{int(row.get('consecutive_failures', 0) or 0)}</td>"
                f'<td class="px-4 py-3 text-sm">'
                f"{escape(_fmt_ts(row.get('locked_at')))}</td>"
                f'<td class="px-4 py-3 text-sm">'
                f'<form method="post" action="{escape(clear_url)}" class="inline">'
                f'<input type="hidden" name="csrf_token" value="{escape(csrf)}">'
                f'<input type="hidden" name="email" value="{escape(row_email)}">'
                '<button type="submit" class="text-sm font-medium text-primary '
                'hover:underline">Unlock</button></form></td>'
                "</tr>"
            )
        return heading + self._table(
            ["Account", "Kind", "Failures", "Locked at", ""],
            rows,
            "No active lockouts.",
        )

    @post("/lockouts/clear")
    async def clear_lockout(self, request: Request) -> Response:
        """Manually unlock an account (CSRF-protected, audited)."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        back = self._admin_path(request, "/admin/security/lockouts")

        # The CSRF middleware already consumed the body and cached the form.
        form = request.scope.get("admin_form_data") or await request.form()
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(back, "Invalid or expired form token.", True)
        email = str(form.get("email", "")).strip()
        if not email:
            return self._redirect(back, "Missing account email.", True)
        if self._lockout_store is None:
            return self._redirect(back, "Lockout store unavailable.", True)

        user = self.current_user(request)
        try:
            await self._lockout_store.clear_lockout(email)
        except Exception:  # noqa: BLE001 — surface a friendly error, log the rest
            logger.exception("security_center.unlock_failed")
            return self._redirect(back, "Could not unlock the account.", True)

        await self._audit(
            request,
            AdminSecurityEventType.ACCOUNT_UNLOCKED,
            True,
            email=email,
            acting_admin_id=str(getattr(user, "user_id", "")),
            source="security_center",
        )
        logger.info(
            "security_center.account_unlocked",
            email=email,
            acting_admin_id=str(getattr(user, "user_id", "")),
        )
        return self._redirect(f"{back}?email={quote_plus(email)}", "Account unlocked.")
