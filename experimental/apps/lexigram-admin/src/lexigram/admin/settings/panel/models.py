"""Pydantic models bound to configuration specs."""

from __future__ import annotations

from typing import Literal

from lexigram.domain import DomainModel
from lexigram.validation import Field

__all__ = [
    "DEFAULT_CSP",
    "STRICT_CSP",
    "BrandingSettings",
    "CacheSettings",
    "I18nSettings",
    "NotificationSettings",
    "ProfilerSettings",
    "RbacSettings",
    "SecuritySettings",
]

# Strict-by-default CSP: every first-party asset (htmx, Alpine, lucide,
# Sortable, Trix, Tailwind build) is vendored under the admin static mount,
# so no third-party origins are needed.
#
# ``'unsafe-eval'`` is REQUIRED (B14): the vendored ``alpine.min.js`` is the
# standard Alpine build, which compiles every directive expression through
# the ``AsyncFunction`` constructor; htmx ``hx-on-*`` handlers use
# ``new Function``. Browsers classify both as eval, so without this source
# every Alpine/htmx expression throws ``EvalError`` and the admin UI is
# dead. Removing it requires the Alpine CSP-build migration (docs
# 09-01-2026/14, "CSP v2").
#
# ``'unsafe-inline'`` remains until the inline <style>/<script> blocks move
# into the token/stylesheet pipeline (same CSP v2 roadmap).
#
# Operators using external chart CDNs (services/charts.py) must extend
# ``script-src`` via the security settings panel.
DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none';"
)

# The CSP v2 *candidate* policy (docs/09-01-2026/14 §3): what the enforced
# policy should become once the inline-script/style migration lands. Shipped
# by default as ``Content-Security-Policy-Report-Only`` so real deployments
# surface every would-be violation without breaking anything. Do NOT enforce
# this while the standard Alpine build + inline blocks remain in use.
STRICT_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none';"
)


class BrandingSettings(DomainModel):
    """Site branding and theme settings consumed by the admin renderer."""

    site_name: str = Field(
        default="Lexigram Admin",
        min_length=1,
        max_length=120,
        title="Site Name",
        description="Name shown in the topbar, login page, and document title.",
    )
    primary_color: str = Field(
        default="#6b7280",
        title="Primary Color",
        description="Hex color used for the primary UI accent.",
    )
    logo_url: str = Field(default="", max_length=2048, title="Logo URL")
    favicon_url: str = Field(default="", max_length=2048, title="Favicon URL")
    dark_mode: Literal["system", "light", "dark"] = Field(
        default="system",
        title="Dark Mode",
        description="Theme preference: follow the system, force light, or force dark.",
    )


class NotificationSettings(DomainModel):
    """Outbound email sender identity consumed by AdminNotificationService.

    Empty values mean "keep the code-configured default" — a fresh save
    with untouched fields changes nothing (doc 35).
    """

    email_from: str = Field(
        default="",
        max_length=254,
        title="From address",
        description=(
            "Sender email address for verification, password-reset, and "
            "notification emails. Leave empty to keep the configured "
            "default."
        ),
    )
    email_from_name: str = Field(
        default="",
        max_length=120,
        title="From name",
        description=(
            "Sender display name shown in email clients. Leave empty to "
            "keep the configured default."
        ),
    )


class CacheSettings(DomainModel):
    """Response caching settings consumed by AdminCacheMiddleware."""

    enabled: bool = Field(
        default=True,
        title="Enabled",
        description="Cache successful GET responses.",
    )
    default_ttl: int = Field(
        default=60,
        ge=0,
        title="Default TTL (seconds)",
        description="Default cache lifetime when no Cache-Control header is present.",
    )


class SecuritySettings(DomainModel):
    """HTTP security header settings consumed by AdminSecurityHeaders."""

    csp: str = Field(
        default=DEFAULT_CSP,
        title="Content Security Policy",
        description="Content-Security-Policy header value.",
    )
    hsts_max_age: int = Field(
        default=63072000,
        ge=0,
        title="HSTS Max Age (seconds)",
        description="Strict-Transport-Security max-age.",
    )
    frame_options: str = Field(
        default="DENY",
        title="X-Frame-Options",
        description=(
            "X-Frame-Options header value (DENY or SAMEORIGIN). "
            "Leave empty to omit the header and let the CSP "
            "frame-ancestors directive govern embedding."
        ),
    )
    csp_report_only: str = Field(
        default="",
        title="CSP Report-Only Candidate",
        description=(
            "Content-Security-Policy-Report-Only monitoring (CSP v2 "
            "migration). Leave empty to monitor the strict candidate "
            "policy (recommended), set to 'off' to disable monitoring, "
            "or provide a full policy string to monitor a custom "
            "candidate. Violations appear on the Security → CSP tab."
        ),
    )


class I18nSettings(DomainModel):
    """Internationalization defaults consumed by the i18n locale resolver."""

    default_locale: str = Field(
        default="en",
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$",
        title="Default Locale",
        description="Fallback BCP 47 locale tag used when a request resolves no locale.",
    )
    default_timezone: str = Field(
        default="UTC",
        min_length=1,
        max_length=64,
        title="Default Timezone",
        description="Fallback IANA timezone name used when a request resolves no timezone.",
    )


class RbacSettings(DomainModel):
    """RBAC defaults consumed by the permission service."""

    default_role: str = Field(
        default="viewer",
        min_length=1,
        max_length=120,
        title="Default Role",
        description="Role assigned to users with no explicit role mapping.",
    )
    allow_anonymous: bool = Field(
        default=False,
        title="Allow Anonymous",
        description="Permit requests without an authenticated identity.",
    )


class ProfilerSettings(DomainModel):
    """Profiler toggles. Rendering/persistence only — no consumer is wired (see plan)."""

    enabled: bool = Field(
        default=False,
        title="Enabled",
        description="Enable request profiling.",
    )
    slow_threshold_ms: int = Field(
        default=500,
        ge=1,
        title="Slow Threshold (ms)",
        description="Requests slower than this are flagged as slow.",
    )
