"""Email delivery status + test send page (roadmap R11).

Superadmin-only visibility into outbound email: which
``MailerProtocol`` backend is bound (if any), the configured sender
identity, and a one-click "send test email" to the acting admin's own
address. Design: docs/09-01-2026/07-mailer-onboarding.md. Reuses the
access-control base (gate, CSRF, flash, mount-time wiring — docs 05/06).
"""

from __future__ import annotations

from html import escape
from typing import Any

from starlette.requests import Request
from starlette.responses import Response

from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol
from lexigram.admin.controllers.access_control import (
    _BTN_CLS,
    _AccessControlController,
    _fmt_ts,
)
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.services.notifications import AdminNotificationService
from lexigram.admin.services.notifications.models import NotificationRecipient
from lexigram.contracts.web import get, post
from lexigram.logging import get_logger

logger = get_logger(__name__)

__all__ = ["EmailDeliveryController"]


class EmailDeliveryController(_AccessControlController):
    """Email delivery diagnostics (superadmin-only).

    Routes:
        GET  /admin/email      - Delivery status + test-send form
        POST /admin/email/test - Send a test email to the acting admin
    """

    prefix = "/email"

    def __init__(
        self,
        renderer: AdminRenderer,
        csrf_service: AdminCsrfServiceProtocol | None = None,
        notification_service: AdminNotificationService | None = None,
        super_admin_role: str = "superadmin",
    ) -> None:
        """Initialise the email delivery controller.

        Args:
            renderer: AdminRenderer for shell page rendering.
            csrf_service: CSRF token service (POST protection).
            notification_service: Notification/email orchestrator.
            super_admin_role: Configured super-admin role name.
        """
        super().__init__(
            renderer=renderer,
            csrf_service=csrf_service,
            super_admin_role=super_admin_role,
        )
        self._notification_service = notification_service
        # Delivery log store (R46, doc 42) — attached best-effort at mount.
        self._delivery_log: Any = None

    # -- rendering ----------------------------------------------------------

    def _status_card(
        self,
        sender: tuple[str, str] | None = None,
        health: Any = None,
    ) -> str:
        """Runtime delivery status: backend, sender identity, health, guidance.

        Args:
            sender: Effective ``(from_email, from_name)`` after settings
                overrides (doc 35); falls back to the frozen config.
            health: Backend ``HealthCheckResult`` or ``None``.
        """
        service = self._notification_service
        if service is None:
            return (
                '<div class="bg-card border border-border rounded-xl p-6">'
                '<h2 class="text-sm font-medium text-destructive">'
                "Notification service unavailable</h2>"
                '<p class="text-sm text-muted-foreground mt-2">The admin '
                "notification service failed to resolve — check the boot "
                "log for registration errors.</p></div>"
            )

        config = getattr(service, "config", None)
        if sender is not None:
            from_email, from_name = sender
        else:
            from_email = str(getattr(config, "email_from", "") or "")
            from_name = str(getattr(config, "email_from_name", "") or "")

        if service.mailer_bound:
            backend = service.mailer_backend_name or "unknown"
            health_line = self._health_line(health)
            fallback_note = (
                '<p class="text-sm text-muted-foreground mt-2">This is the '
                "automatic <strong>debug-mode console fallback</strong>: "
                "emails are written to the server log instead of being "
                "delivered. Bind a real <code>MailerProtocol</code> backend "
                "before production.</p>"
                if service.mailer_is_debug_fallback
                else ""
            )
            status_html = (
                '<h2 class="text-sm font-medium text-green-600">'
                "Email delivery: configured</h2>"
                '<dl class="mt-3 space-y-1 text-sm">'
                f'<div><dt class="inline text-muted-foreground">Backend:</dt> '
                f'<dd class="inline font-mono">{escape(backend)}</dd></div>'
                f'<div><dt class="inline text-muted-foreground">From:</dt> '
                f'<dd class="inline">{escape(from_name)} '
                f"&lt;{escape(from_email)}&gt;</dd></div>"
                f"{health_line}"
                f"</dl>{fallback_note}"
            )
        else:
            status_html = (
                '<h2 class="text-sm font-medium text-destructive">'
                "Email delivery: not configured</h2>"
                '<p class="text-sm text-muted-foreground mt-2">'
                "Verification, password-reset, and one-time-password emails "
                "cannot be delivered. Bind a <code>MailerProtocol</code> "
                "backend (for example the lexigram-notification "
                "<code>MailerModule</code> with driver <code>smtp</code>, "
                "<code>sendgrid</code>, or <code>console</code>), or enable "
                "debug mode to get the automatic console fallback for "
                "development.</p>"
            )
        return (
            '<div class="bg-card border border-border rounded-xl p-6">'
            + status_html
            + "</div>"
        )

    @staticmethod
    def _health_line(health: Any) -> str:
        """Render the backend health check as a status line (doc 35).

        ``None`` (no check available / check errored) renders as a muted
        "unknown" rather than nothing, so operators can tell "not
        checkable" apart from "healthy".
        """
        if health is None:
            return (
                '<div><dt class="inline text-muted-foreground">Health:</dt> '
                '<dd class="inline text-muted-foreground">unknown '
                "(backend exposes no health check)</dd></div>"
            )
        status = str(getattr(getattr(health, "status", None), "value", "") or "")
        message = str(getattr(health, "message", "") or "")
        cls = {
            "healthy": "text-green-600",
            "unhealthy": "text-destructive",
        }.get(status, "text-amber-600")
        suffix = f" — {escape(message)}" if message else ""
        return (
            '<div><dt class="inline text-muted-foreground">Health:</dt> '
            f'<dd class="inline font-medium {cls}">{escape(status or "unknown")}'
            f"{suffix}</dd></div>"
        )

    def _test_form(self, request: Request) -> str:
        """Test-send form addressed to the acting admin's own email."""
        user = self.current_user(request)
        email = str(getattr(user, "email", "") or "")
        disabled = (
            self._notification_service is None
            or not self._notification_service.mailer_bound
        )
        button = (
            '<button type="submit" class="rounded-lg bg-muted '
            'text-muted-foreground px-4 py-2 text-sm font-medium" disabled>'
            "Send test email</button>"
            if disabled
            else f'<button type="submit" class="{_BTN_CLS}">Send test email</button>'
        )
        return (
            '<div class="bg-card border border-border rounded-xl p-6 mt-4">'
            '<h2 class="text-sm font-medium">Send a test email</h2>'
            '<p class="text-sm text-muted-foreground mt-2">Delivers to your '
            f"own address (<strong>{escape(email)}</strong>) so the button "
            "cannot be used to send arbitrary mail.</p>"
            f'<form method="post" action="{escape(self._admin_path(request, "/admin/email/test"))}" class="mt-4">'
            f'<input type="hidden" name="csrf_token" value="{escape(self._csrf_token(request))}">'
            f"{button}</form></div>"
        )

    async def _deliveries_html(self, limit: int = 50) -> str:
        """Recent-deliveries table (R46, doc 42).

        Args:
            limit: Maximum rows to display.

        Returns:
            Card HTML; empty string when no delivery-log store is attached
            (page degrades to its Phase 2 shape) and a muted note when the
            store errors.
        """
        store = self._delivery_log
        if store is None:
            return ""
        try:
            rows = await store.list_recent(limit=limit)
        except Exception:  # noqa: BLE001 — diagnostics must not break the page
            logger.warning("email_delivery.log_listing_failed")
            return (
                '<div class="bg-card border border-border rounded-xl p-6 mt-4">'
                '<h2 class="text-sm font-medium">Recent deliveries</h2>'
                '<p class="text-sm text-muted-foreground mt-2">'
                "Delivery log unavailable.</p></div>"
            )
        header = (
            '<div class="bg-card border border-border rounded-xl p-6 mt-4">'
            f'<h2 class="text-sm font-medium">Recent deliveries '
            f'<span class="text-muted-foreground font-normal">({len(rows)} shown)</span></h2>'
            '<p class="text-sm text-muted-foreground mt-2">Emails handed to the '
            "mailer backend, newest first. &ldquo;Sent&rdquo; means the backend "
            "accepted the message, not that it reached an inbox.</p>"
        )
        if not rows:
            return (
                header + '<p class="text-sm text-muted-foreground mt-4">'
                "No deliveries recorded yet.</p></div>"
            )
        body: list[str] = []
        for row in rows:
            success = bool(row.get("success"))
            error = str(row.get("error") or "")
            if success:
                outcome = '<span class="text-sm font-medium text-primary">Sent</span>'
            else:
                detail = (
                    f'<span class="block text-xs text-muted-foreground" '
                    f'title="{escape(error)}">{escape(error[:80])}'
                    f"{'…' if len(error) > 80 else ''}</span>"
                    if error
                    else ""
                )
                outcome = f'<span class="text-sm font-medium text-destructive">Failed</span>{detail}'
            body.append(
                "<tr class='border-b border-border'>"
                f'<td class="px-4 py-3 text-sm whitespace-nowrap">{escape(_fmt_ts(row.get("created_at")))}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(str(row.get("notification_type") or ""))}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(str(row.get("recipient") or ""))}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(str(row.get("subject") or ""))}</td>'
                f'<td class="px-4 py-3">{outcome}</td>'
                "</tr>"
            )
        head_cls = (
            "px-4 py-2 text-left text-xs font-medium text-muted-foreground "
            "uppercase tracking-wider"
        )
        return (
            header + '<div class="overflow-x-auto mt-4"><table class="w-full">'
            '<thead><tr class="border-b border-border">'
            f'<th class="{head_cls}">Time</th>'
            f'<th class="{head_cls}">Type</th>'
            f'<th class="{head_cls}">Recipient</th>'
            f'<th class="{head_cls}">Subject</th>'
            f'<th class="{head_cls}">Outcome</th>'
            f"</tr></thead><tbody>{''.join(body)}</tbody></table></div></div>"
        )

    # -- routes -------------------------------------------------------------

    @get("/")
    async def status_page(self, request: Request) -> Response:
        """Email delivery status card + test-send form + recent deliveries."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        sender: tuple[str, str] | None = None
        health: Any = None
        service = self._notification_service
        if service is not None:
            try:
                sender = await service.effective_sender()
            except Exception:  # noqa: BLE001 — card falls back to config identity
                logger.warning("email_delivery.effective_sender_failed")
            try:
                health = await service.mailer_health()
            except Exception:  # noqa: BLE001 — diagnostics must not break the page
                logger.warning("email_delivery.health_check_failed")
        html = (
            '<div class="max-w-2xl">'
            + self._status_card(sender=sender, health=health)
            + self._test_form(request)
            + await self._deliveries_html()
            + "</div>"
        )
        return await self._page(
            request, html, "Email delivery", "Email", "/admin/email"
        )

    @post("/test")
    async def send_test(self, request: Request) -> Response:
        """Send a test email to the acting admin (CSRF-checked)."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/email")
        form = await self._form(request)
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(base, "Invalid or expired form token.", True)
        if self._notification_service is None:
            return self._redirect(base, "Notification service unavailable.", True)

        user = self.current_user(request)
        email = str(getattr(user, "email", "") or "")
        if not email:
            return self._redirect(
                base, "Your account has no email address to deliver to.", True
            )

        result = await self._notification_service.notify_test_email(
            NotificationRecipient(
                email=email,
                name=str(getattr(user, "name", "") or "") or None,
                user_id=getattr(user, "user_id", None),
            )
        )
        if result.is_err():
            logger.warning(
                "email_delivery.test_failed",
                error=str(result.unwrap_err()),
                to=email,
            )
            return self._redirect(
                base,
                "Test email failed — check the server log for the backend error.",
                True,
            )
        logger.info("email_delivery.test_sent", to=email)
        backend: Any = self._notification_service.mailer_backend_name or "backend"
        return self._redirect(base, f"Test email accepted by {backend} for {email}.")
