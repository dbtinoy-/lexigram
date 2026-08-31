from __future__ import annotations

import re
import secrets

from starlette.requests import Request

from lexigram.admin.auth.protocols import (
    AdminAuthServiceProtocol,
    AdminCsrfServiceProtocol,
    AdminEmailOtpServiceProtocol,
    AdminEmailVerificationServiceProtocol,
    AdminMfaServiceProtocol,
    AdminPasswordResetServiceProtocol,
)
from lexigram.admin.auth.store import AdminUserStoreProtocol
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.observability.admin_metrics import AdminMetrics
from lexigram.admin.resources.urls import admin_prefix_from_request, mount_admin_url
from lexigram.contracts.core import TaskManagerProtocol
from lexigram.logging import get_logger

_CACHE_CONTROL_NO_STORE = {"Cache-Control": "no-store"}

_DEFAULT_NEXT = "/admin/"

_LEX_ERR_RE = re.compile(r"^\[LEX_ERR_[A-Z0-9_]+\]\s+")

_SEE_DOCS_RE = re.compile(r"\n\s*→\s*See:.*$")


def _humanize_error(message: str) -> str:
    """Strip framework error prefixes from a message for user display.

    Args:
        message: Raw error message, possibly including a ``[LEX_ERR_*]``
            prefix and a trailing ``→ See:`` documentation line.

    Returns:
        The message with the prefix and docs line removed, stripped.
    """
    if not message:
        return ""
    return _SEE_DOCS_RE.sub("", _LEX_ERR_RE.sub("", message)).strip()


logger = get_logger(__name__)


class AuthCoreMixin(AdminController):
    """AuthController core: construction, CSRF, URL safety helpers."""

    def __init__(
        self,
        auth_service: AdminAuthServiceProtocol,
        csrf_service: AdminCsrfServiceProtocol,
        renderer: AdminRenderer,
        task_manager: TaskManagerProtocol | None = None,
        metrics: AdminMetrics | None = None,
        password_reset_service: AdminPasswordResetServiceProtocol | None = None,
        mfa_service: AdminMfaServiceProtocol | None = None,
        email_verification_service: AdminEmailVerificationServiceProtocol | None = None,
        email_otp_service: AdminEmailOtpServiceProtocol | None = None,
    ) -> None:
        """Initialise auth controller.

        Args:
            auth_service: Orchestrates credential verification, rate limiting,
                lockout checks, session issuance, and audit logging.
            csrf_service: Generates and validates CSRF tokens.
            renderer: AdminRenderer for page rendering.
            task_manager: Optional task manager; injected by the container in
                production, omitted in tests.
            metrics: Optional admin metrics collector.
            password_reset_service: Optional password reset orchestrator;
                injected by the container when registered, ``None`` otherwise.
            mfa_service: Optional TOTP 2FA orchestrator; injected by the
                container when registered, ``None`` otherwise.
            email_verification_service: Optional email verification
                orchestrator; ``None`` disables the verification gate.
            email_otp_service: Optional email OTP factor orchestrator;
                ``None`` disables email-code challenges.
        """
        super().__init__(renderer, task_manager)
        self._auth_service = auth_service
        self._csrf_service = csrf_service
        self._metrics = metrics or AdminMetrics(None)
        self._password_reset_service = password_reset_service
        self._mfa_service = mfa_service
        self._email_verification_service = email_verification_service
        self._email_otp_service = email_otp_service
        # Self-service registration — wired by the bundle provider from
        # ``AdminAuthConfig.registration`` (off unless explicitly enabled).
        self._user_store: AdminUserStoreProtocol | None = None
        self._registration_enabled = False
        self._registration_default_role = "admin"
        self._registration_domains: list[str] = []

    def _fresh_csrf(self, request: Request) -> str:
        """Generate a fresh CSRF token bound to a new session id."""
        csrf_session_id = secrets.token_urlsafe(16)
        request.session["csrf_session_id"] = csrf_session_id
        return self._csrf_service.generate_token(csrf_session_id)

    @staticmethod
    def _admin_path(request: Request, canonical_path: str = "/admin/") -> str:
        """Mount a canonical internal admin path under this request prefix."""
        return mount_admin_url(
            canonical_path,
            admin_prefix_from_request(request),
        )

    @staticmethod
    def _safe_next_url(candidate: str, default: str = _DEFAULT_NEXT) -> str:
        """Return ``candidate`` if it is a safe same-origin relative path, else the default.

        Rejects absolute URLs (any scheme), scheme-relative URLs (leading
        ``//``, interpreted by browsers as ``{current-scheme}://``), and
        anything not starting with a single ``/``.  This is the sole point
        every post-login/post-MFA/post-verification ``next`` value must pass
        through before being stored in session state or used in a redirect.

        Args:
            candidate: Raw ``next`` value from user input.

        Returns:
            ``candidate`` when it starts with a single ``/`` (and not
            ``//`` or ``/\\``), otherwise ``default``.
        """
        if (
            candidate
            and candidate.startswith("/")
            and not candidate.startswith("//")
            and not candidate.startswith("/\\")
        ):
            return candidate
        return default

    def _get_client_ip(self, request: Request) -> str:
        """Extract the real client IP from the request.

        Prefers the first value of the ``X-Forwarded-For`` header when present
        (set by reverse proxies), falling back to the direct TCP peer address.

        Args:
            request: Incoming HTTP request.

        Returns:
            IP address string, or ``"unknown"`` when unavailable.
        """
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
