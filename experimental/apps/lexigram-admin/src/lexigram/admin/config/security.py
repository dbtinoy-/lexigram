"""Security, RBAC, password policy, rate limiting, and audit configurations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram.domain import DomainModel
from lexigram.validation import (
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


@dataclass(init=False)
class AdminPasswordPolicyConfig(DomainModel):
    """Password policy configuration for admin authentication.

    Follows NIST SP 800-63B guidelines.
    """

    min_length: int = Field(default=12, ge=8, le=128)
    max_length: int = Field(default=128, ge=32, le=1024)
    require_uppercase: bool = Field(default=True)
    require_lowercase: bool = Field(default=True)
    require_digit: bool = Field(default=True)
    require_special: bool = Field(default=True)
    reject_common_passwords: bool = Field(default=True)
    reject_containing_email: bool = Field(default=True)

    model_config = {"extra": "forbid"}


@dataclass(init=False)
class AdminSecurityConfig(DomainModel):
    """Security hardening configuration for admin authentication.

    Controls rate limiting, progressive lockout, and setup token protection.
    """

    ip_rate_limit_enabled: bool = Field(default=True)
    ip_rate_limit_per_minute: int = Field(default=10, ge=1)
    ip_rate_limit_per_15_minutes: int = Field(default=30, ge=1)
    ip_rate_limit_per_hour: int = Field(default=60, ge=1)

    # Progressive lockout thresholds: list of (failure_count, lockout_minutes)
    # e.g. [(5, 15), (10, 60), (15, 240), (20, 1440)] means:
    #   5 failures → 15 min lockout, 10 → 1hr, 15 → 4hr, 20 → 24hr
    lockout_thresholds: list[tuple[int, int]] = Field(
        default_factory=lambda: [(5, 15), (10, 60), (15, 240), (20, 1440)],
    )
    permanent_lockout_threshold: int = Field(default=50, ge=10)

    setup_token: SecretStr | None = Field(
        default=None,
        description="Optional ADMIN_SETUP_TOKEN — when set, must be provided during first-run setup.",
    )

    @field_validator("setup_token")
    @classmethod
    def _coerce_setup_token(cls, value: Any) -> Any:
        """Accept plain strings from env/YAML; store as SecretStr."""
        if value is None or isinstance(value, SecretStr):
            return value
        return SecretStr(str(value))

    setup_token_optin_unsafe: bool = Field(
        default=False,
        description=(
            "Explicit escape hatch: boot without a setup token. Only for "
            "local/ephemeral environments — leaves the first-run wizard open "
            "to any visitor until an admin account is created."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def _map_legacy_setup_token(cls, data: Any) -> Any:
        """Map the legacy ``ADMIN_SETUP_TOKEN`` input key onto ``setup_token``.

        Keeps existing deployments working unchanged: the token can be
        provided as a config key (``admin.security.ADMIN_SETUP_TOKEN`` in
        YAML/``from_dict`` input) or as the bare ``ADMIN_SETUP_TOKEN``
        environment variable.  Explicit ``setup_token`` always wins.

        Args:
            data: Raw input dict (or already-built instance) before field
                assignment.

        Returns:
            The input dict with the legacy key mapped onto ``setup_token``
            when the latter is absent.
        """
        if not isinstance(data, dict):
            return data
        if "ADMIN_SETUP_TOKEN" in data and "setup_token" not in data:
            return {**data, "setup_token": data["ADMIN_SETUP_TOKEN"]}
        if "setup_token" not in data:
            import os

            legacy = os.getenv("ADMIN_SETUP_TOKEN")
            if legacy:
                return {**data, "setup_token": legacy}
        return data

    model_config = {"extra": "forbid"}


@dataclass(init=False)
class AdminRbacConfig(DomainModel):
    """RBAC editing-page configuration."""

    #: Role name granted wildcard admin rights.  Matches the role string
    #: already special-cased by settings/widgets/impersonation.
    super_admin_role: str = Field(default="superadmin")


@dataclass(init=False)
class AdminRateLimitConfig(DomainModel):
    """Rate limiting configuration."""

    enabled: bool = Field(default=True)
    requests_per_minute: int = Field(default=60, ge=1)
    requests_per_hour: int = Field(default=1000, ge=1)
    burst_size: int = Field(default=10, ge=1)

    # Per-action limits
    create_per_minute: int = Field(default=30, ge=0)
    update_per_minute: int = Field(default=60, ge=0)
    delete_per_minute: int = Field(default=20, ge=0)
    bulk_per_minute: int = Field(default=5, ge=0)

    model_config = {"extra": "forbid"}


@dataclass(init=False)
class AdminAuditConfig(DomainModel):
    """Audit logging configuration."""

    read_audit_enabled: bool = Field(
        default=False,
        description="Log read operations (off by default; compliance mode only).",
    )

    model_config = {"extra": "forbid"}
