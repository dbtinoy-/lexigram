"""Pydantic models bound to configuration specs."""

from __future__ import annotations

from typing import Literal

from lexigram.domain import DomainModel
from lexigram.validation import Field

__all__ = [
    "DEFAULT_CSP",
    "BrandingSettings",
    "CacheSettings",
    "I18nSettings",
    "ProfilerSettings",
    "RbacSettings",
    "SecuritySettings",
]

DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.tailwindcss.com; "
    "style-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.tailwindcss.com; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self' https://unpkg.com; "
    "frame-ancestors 'none';"
)


class BrandingSettings(DomainModel):
    """Site branding and theme settings consumed by the admin renderer."""

    site_name: str = Field(
        default="Lexigram Admin",
        title="Site Name",
        description="Name shown in the topbar, login page, and document title.",
    )
    primary_color: str = Field(
        default="#6b7280",
        title="Primary Color",
        description="Hex color used for the primary UI accent.",
    )
    logo_url: str = Field(default="", title="Logo URL")
    favicon_url: str = Field(default="", title="Favicon URL")
    dark_mode: Literal["system", "light", "dark"] = Field(
        default="system",
        title="Dark Mode",
        description="Theme preference: follow the system, force light, or force dark.",
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


class I18nSettings(DomainModel):
    """Internationalization defaults consumed by the i18n locale resolver."""

    default_locale: str = Field(
        default="en",
        title="Default Locale",
        description="Fallback BCP 47 locale tag used when a request resolves no locale.",
    )
    default_timezone: str = Field(
        default="UTC",
        title="Default Timezone",
        description="Fallback IANA timezone name used when a request resolves no timezone.",
    )


class RbacSettings(DomainModel):
    """RBAC defaults consumed by the permission service."""

    default_role: str = Field(
        default="viewer",
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
