"""Authentication, MFA, email OTP, verification, and registration configurations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from lexigram.admin.config.security import (
    AdminPasswordPolicyConfig,
    AdminSecurityConfig,
)
from lexigram.domain import DomainModel
from lexigram.validation import (
    Field,
    SecretStr,
    model_validator,
)


@dataclass(init=False)
class AdminMfaConfig(DomainModel):
    """Two-factor authentication (TOTP) configuration.

    Controls whether TOTP 2FA is offered, the issuer label embedded in
    provisioning URIs, and the allowed clock-skew window for codes.
    """

    enabled: bool = Field(default=True, description="Enable TOTP 2FA")
    factor: str = Field(
        default="totp",
        description="Second factor used at login: 'totp' (authenticator app) or 'email' (one-time code)",
    )
    issuer: str = Field(
        default="Lexigram Admin",
        description="TOTP issuer label shown in authenticator apps",
    )
    skew: int = Field(
        default=1,
        ge=0,
        le=2,
        description="Allowed clock skew in 30 second steps",
    )


@dataclass(init=False)
class AdminEmailOtpConfig(DomainModel):
    """Email one-time-password (login factor) configuration.

    Controls whether the email-OTP factor is available, how long a code
    stays valid, and the minimum interval between sends.
    """

    enabled: bool = Field(default=True, description="Enable email OTP factor")
    ttl_minutes: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Code validity window in minutes",
    )
    resend_cooldown_seconds: int = Field(
        default=60,
        ge=5,
        le=600,
        description="Minimum seconds between email OTP sends",
    )


@dataclass(init=False)
class AdminEmailVerificationConfig(DomainModel):
    """Email verification (login gate) configuration.

    Controls the verify-your-email flow: whether it is offered, whether
    unverified users are blocked at login, and the verify-link lifetime.
    """

    enabled: bool = Field(default=True, description="Enable email verification flow")
    enforcement: bool = Field(
        default=True,
        description="Block login until the email is verified",
    )
    token_ttl_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Verify link validity in hours",
    )


@dataclass(init=False)
class AdminRegistrationConfig(DomainModel):
    """Self-service registration configuration.

    Off by default — admin panels are typically invite-only. When enabled,
    ``GET/POST /admin/register`` becomes available and new accounts receive
    the configured default role.
    """

    enabled: bool = Field(default=False, description="Allow self-service registration")
    default_role: str = Field(
        default="admin", description="Role granted to new accounts"
    )
    allowed_email_domains: list[str] = Field(
        default_factory=list,
        description="Restrict registration to these email domains (empty = any)",
    )


@dataclass(init=False)
class AdminAuthConfig(DomainModel):
    """Authentication configuration."""

    enabled: bool = Field(default=True, description="Enable authentication")
    env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment for cookie security defaults",
    )
    session_secret: SecretStr = Field(
        default=SecretStr("change-me-in-production"),
        description="Session secret for signing",
    )
    login_url: str = Field(default="/admin/login")
    logout_url: str = Field(default="/admin/logout")
    session_lifetime: int = Field(default=86400, ge=300)  # 5 min minimum
    permission_cache_ttl: int = Field(default=300, ge=0)  # 5 minutes

    # Security settings
    idle_timeout: int = Field(
        default=3600, ge=60, description="Session idle timeout in seconds"
    )
    csrf_token_lifetime: int = Field(
        default=3600, ge=60, description="CSRF token expiry in seconds"
    )
    password_policy: AdminPasswordPolicyConfig = Field(
        default_factory=AdminPasswordPolicyConfig,
    )
    security: AdminSecurityConfig = Field(
        default_factory=AdminSecurityConfig,
    )
    mfa: AdminMfaConfig = Field(default_factory=AdminMfaConfig)
    email_otp: AdminEmailOtpConfig = Field(default_factory=AdminEmailOtpConfig)
    email_verification: AdminEmailVerificationConfig = Field(
        default_factory=AdminEmailVerificationConfig
    )
    registration: AdminRegistrationConfig = Field(
        default_factory=AdminRegistrationConfig
    )

    # Users and Roles (Sync)
    users: list[Any] = Field(default_factory=list)
    roles: dict[str, Any] = Field(default_factory=dict)

    # Identity bridge (spec D3): "internal" = framework admin_users table
    # (default); "app" = AdminPrincipalProviderProtocol implemented by the app.
    principal_source: Literal["internal", "app"] = Field(default="internal")

    # OAuth/SSO (optional)
    oauth_enabled: bool = Field(default=False)
    oauth_providers: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}

    @model_validator(mode="after")
    def validate_security(self) -> AdminAuthConfig:
        """Ensure secure settings in production."""
        if not isinstance(self.session_secret, SecretStr):
            self.session_secret = SecretStr(self.session_secret)
        insecure_defaults = (
            "change-me",
            "your-secret-key",
            "secret",
            "password",
            "change-me-in-production",
        )

        if (
            self.env in {"production", "staging"}
            and self.session_secret.get_secret_value().lower() in insecure_defaults
        ):
            raise ValueError(
                "CRITICAL SECURITY ERROR: Default admin session_secret detected in "
                f"{self.env.upper()}.\n"
                "You MUST set a secure session secret via LEX_ADMIN__AUTH__SESSION_SECRET.",
            )

        if (
            self.env in {"production", "staging"}
            and self.oauth_enabled
            and not self.oauth_providers
        ):
            raise ValueError(
                "oauth_providers must be configured when oauth_enabled=True"
            )

        if (
            self.env in {"production", "staging"}
            and self.csrf_token_lifetime > self.idle_timeout
        ):
            raise ValueError("csrf_token_lifetime must not exceed idle_timeout")

        return self
