"""Configuration models for Lexigram Auth.

This module provides Pydantic models for configuring authentication
and authorization in Lexigram applications.

Example:
    from lexigram.auth.config import AuthConfig

    # From YAML
    config = AuthConfig.from_yaml("application.yaml")

    # From environment
    config = AuthConfig()  # reads LEX_AUTH__* env vars
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, cast

from lexigram.auth import constants as const
from lexigram.config import BaseConfig
from lexigram.contracts.core.config import Environment
from lexigram.logging import get_logger
from lexigram.validation import ConfigDict, Field, SecretStr, model_validator

_logger = get_logger(__name__)


@dataclass(init=False)
class AuthUserConfig(BaseConfig):
    """Single user configuration for bootstrapping.

    The configuration historically used ``username`` as the primary
    identifier.  We now prefer ``name`` but keep ``username`` for
    backwards-compatibility; the validator below will map ``username``
    to ``name`` when the latter is missing.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    # ``username`` is kept for legacy support but not required
    username: str | None = Field(None, description="Legacy username")
    name: str = Field(..., description="User name (preferred over username)")
    email: str = Field(..., description="Email address")
    password: str | None = Field(default=None, description="Plain password")
    password_hash: str | None = Field(default=None, description="Pre-hashed password")
    roles: list[str] = Field(default_factory=list, description="List of role names")
    is_active: bool = Field(default=True, description="Whether user is active")

    @model_validator(mode="before")
    def _handle_username(self, values: dict[str, Any]) -> dict[str, Any]:
        # migrate ``username`` -> ``name`` if necessary
        if "username" in values and "name" not in values:
            values["name"] = values.pop("username")
        return values


@dataclass(init=False)
class AuthRoleConfig(BaseConfig):
    """Role configuration with permissions and inheritance."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    name: str = Field(..., description="Role name")
    description: str = Field(default="", description="Role description")
    permissions: list[str] = Field(
        default_factory=list,
        description="Permission patterns",
    )
    inherits: list[str] = Field(
        default_factory=list,
        description="Parent roles to inherit from",
    )


@dataclass(init=False)
class RBACConfig(BaseConfig):
    """RBAC system configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True, description="Enable RBAC enforcement")
    superuser_bypass: bool = Field(
        default=True,
        description="Allow superuser role to bypass all checks",
    )
    default_role: str = Field(
        default="viewer",
        description="Default role for new users",
    )
    cache_permissions: bool = Field(
        default=True,
        description="Cache resolved permissions",
    )
    permission_cache_ttl: int = Field(
        default=300,
        description="Permission cache TTL in seconds",
    )


@dataclass(init=False)
class JWTConfig(BaseConfig):
    """JWT Configuration

    JWT verification policy
    -----------------------
    The framework enforces verified-only JWT decoding by default.

    - ``PRODUCTION`` / ``STAGING``: A secret is **required**. The
      ``allow_unverified_dev`` flag is silently ignored even if set to
      ``True``; unverified decode is never permitted.
    - ``DEVELOPMENT`` with ``allow_unverified_dev=True``: When no secret
      is configured the service will decode tokens **without** signature
      verification. A single warning is emitted at boot. This is an explicit
      opt-in intended only for local development workflows.
    - ``DEVELOPMENT`` with ``allow_unverified_dev=False`` (default) and a
      missing secret: raises at boot, same as production.

    Set ``LEX_AUTH__TOKEN__ALLOW_UNVERIFIED_DEV=true`` (or pass the field
    directly) to enable the development opt-in.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    from lexigram.contracts.core import Duration

    secret_key: SecretStr = Field(..., description="Secret key for signing tokens")
    algorithm: str = Field(
        default=const.DEFAULT_TOKEN_ALGORITHM, description="Algorithm"
    )
    access_token_expire: Duration = Field(
        default=Duration.minutes(const.DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES),
        description="Access token expiry duration",
    )
    refresh_token_expire: Duration = Field(
        default=Duration.days(const.DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS),
        description="Refresh token expiry duration",
    )
    id_token_expire: Duration = Field(
        default=Duration.hours(1),
        description="ID token expiry duration",
    )
    key_rotation_grace_period: Duration = Field(
        default=Duration.seconds(const.DEFAULT_JWT_KEY_ROTATION_GRACE_PERIOD_SECONDS),
        description=(
            "Duration during which tokens signed by a rotated-out key remain "
            "accepted. Prevents immediate logout on key rotation."
        ),
    )
    required_audience: str | None = Field(
        default=None,
        description=(
            "Expected ``aud`` claim for every token verified by this service. "
            "When set, tokens whose audience does not match are rejected outright. "
            "Leave as ``None`` only for internal, single-service deployments where "
            "audience segregation is not required."
        ),
    )
    allow_unverified_dev: bool = Field(
        default=False,
        description=(
            "Allow unverified JWT decode when the secret is absent. "
            "ONLY effective in Environment.DEVELOPMENT. "
            "Silently overridden to False in PRODUCTION and STAGING regardless "
            "of what is set here. "
            "Set to True only for local development workflows where a real JWT "
            "secret is not available. "
            "A warning is logged at boot whenever this mode is active."
        ),
    )

    @model_validator(mode="after")
    def validate_jwt_security(self) -> JWTConfig:
        """Enforce verified-only JWT policy based on deployment environment."""
        if not isinstance(self.secret_key, SecretStr):
            self.secret_key = SecretStr(self.secret_key)
        env = self.environment
        _STRICT_ENVS = {Environment.PRODUCTION, Environment.STAGING}

        if env in _STRICT_ENVS:
            # In production/staging, allow_unverified_dev is always overridden.
            # We cannot mutate frozen fields here, but we enforce the policy
            # at boot via TokenProvider; warn if caller explicitly set it.
            if self.allow_unverified_dev:
                _logger.warning(
                    "jwt_allow_unverified_dev_ignored",
                    environment=env.value,
                    reason="allow_unverified_dev is not permitted in PRODUCTION/STAGING; "
                    "flag silently overridden to False",
                )
            # Validate secret quality in strict environments.
            if self.secret_key.get_secret_value() in ("change-me", "your-secret-key"):
                raise ValueError(
                    "CRITICAL SECURITY ERROR: Default JWT secret_key detected in "
                    f"{env.value.upper()}.\n"
                    "You MUST set a secure secret key via LEX_AUTH__TOKEN__SECRET_KEY.",
                )
            if (
                self.algorithm.startswith("HS")
                and len(self.secret_key.get_secret_value()) < 32
            ):
                raise ValueError(
                    f"SECURITY ERROR: {self.algorithm} requires a secret of at "
                    f"least 32 bytes in {env.value}.\n"
                    "Either provide a strong secret (e.g. secrets.token_hex(32)) "
                    "or switch to RS256 for asymmetric key security.",
                )

        elif env == Environment.DEVELOPMENT:
            if self.allow_unverified_dev:
                # Opt-in is active — emit a single boot-time warning.
                _logger.warning(
                    "jwt_unverified_dev_mode_active",
                    environment=env.value,
                    reason="allow_unverified_dev=True; tokens will be decoded without "
                    "signature verification when secret is absent. "
                    "NEVER enable this in production.",
                )
            _logger.info(
                "jwt_verification_policy",
                environment=env.value,
                mode="unverified_dev_opt_in"
                if self.allow_unverified_dev
                else "verified_only",
            )
        return self


@dataclass(init=False)
class PasswordConfig(BaseConfig):
    """Password complexity and validation configuration.

    Controls minimum and maximum length, required character classes, and
    patterns that are explicitly banned (e.g., common passwords).
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    min_length: int = Field(default=12, description="Minimum password length")
    max_length: int = Field(default=128, description="Maximum password length")
    require_uppercase: bool = Field(
        default=True,
        description="Require at least one uppercase letter",
    )
    require_lowercase: bool = Field(
        default=False,
        description="Require at least one lowercase letter",
    )
    require_digits: bool = Field(
        default=True,
        description="Require at least one digit",
    )
    require_special: bool = Field(
        default=False,
        description="Require at least one special character (non-alphanumeric)",
    )
    banned_patterns: list[str] = Field(
        default_factory=list,
        description=(
            "Substrings that must not appear in the password (case-insensitive). "
            "Use to reject common passwords or the user's own name."
        ),
    )


@dataclass(init=False)
class AuthMiddlewareConfig(BaseConfig):
    """Configuration for authentication middleware."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    exclude_paths: list[str] = Field(
        default_factory=list,
        description="Paths excluded from auth",
    )
    backend: str = Field(default="session", description="Auth backend type")
    header_name: str = Field(
        default="Authorization",
        description="Header name for token",
    )
    scheme: str = Field(default=const.DEFAULT_TOKEN_TYPE, description="Token scheme")
    roles_required: list[str] = Field(
        default_factory=list,
        description="Roles required",
    )
    permissions_required: list[str] = Field(
        default_factory=list,
        description="Permissions required",
    )
    optional_auth: bool = Field(
        default=False,
        description="Whether authentication is optional",
    )
    login_url: str | None = Field(default=None, description="URL to redirect for login")
    exclude_prefixes: list[str] = Field(
        default_factory=list,
        description="Path prefixes excluded",
    )
    login_rate_limit: str = Field(
        default="5/minute",
        description="Rate limit for auth endpoints",
    )


@dataclass(init=False)
class AuthConfig(BaseConfig):
    """Hierarchical root configuration for Lexigram Auth.

    Attributes:
        name: Configuration name (default: "auth")
        enabled: Whether the auth module is enabled
        users: Initial users to create
        roles: Role definitions for RBAC
        rbac: RBAC system configuration
        token: JWT configuration
        middleware: Authentication middleware configuration
        secret_key: Secret key for signing tokens
        admin_email: Initial admin email
        admin_password: Initial admin password
        login_rate_limit: Rate limit for login endpoints
        oauth2_providers: OAuth2 provider configurations
    """

    model_config = cast(
        "ConfigDict",
        {
            "env_prefix": "LEX_AUTH__",
            "env_nested_delimiter": "__",
            "extra": "ignore",
        },
    )

    config_section: ClassVar[str] = "auth"

    name: str = "auth"
    enabled: bool = True
    users: list[AuthUserConfig] = Field(
        default_factory=list,
        description="Initial users",
    )
    roles: dict[str, AuthRoleConfig] = Field(
        default_factory=dict,
        description="Role definitions",
    )
    rbac: RBACConfig = Field(default_factory=RBACConfig, description="RBAC config")
    password: PasswordConfig = Field(
        default_factory=PasswordConfig,
        description="Password complexity rules",
    )
    token: JWTConfig = Field(description="JWT Configuration")
    middleware: AuthMiddlewareConfig = Field(
        default_factory=AuthMiddlewareConfig,
        description="Middleware Configuration",
    )
    secret_key: str = Field(description="Secret key for signing")
    admin_email: str | None = Field(default=None, description="Initial admin email")
    admin_password: str | None = Field(
        default=None,
        description="Initial admin password",
    )
    login_rate_limit: str = Field(default="5/minute", description="Default rate limit")
    oauth2_providers: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="OAuth2 configs",
    )
    max_sessions_per_user: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of concurrent sessions allowed per user. "
        "``None`` (the default) means unlimited.  When a positive integer is "
        "set and the limit is exceeded, the least-recently-used session is evicted.",
    )
    relay_verification: bool = Field(
        default=False,
        description=(
            "Enable binding ``RelayAuthVerifierProtocol`` for the relay "
            "gateway's inbound API-key authentication.  When ``False`` "
            "(default) no relay binding is registered."
        ),
    )

    @model_validator(mode="after")
    def validate_security(self) -> AuthConfig:
        """Ensure secure settings in production."""
        env = self.environment
        insecure_defaults = ("change-me", "your-secret-key", "secret", "password")

        if env.value == "production":
            if self.secret_key.lower() in insecure_defaults:
                raise ValueError(
                    "CRITICAL SECURITY ERROR: Default auth secret_key in PRODUCTION.",
                )
            if self.admin_password and self.admin_password.lower() in insecure_defaults:
                raise ValueError(
                    "CRITICAL SECURITY ERROR: Default admin_password in PRODUCTION.",
                )
        return self


__all__ = [
    "AuthConfig",
    "AuthMiddlewareConfig",
    "AuthRoleConfig",
    "AuthUserConfig",
    "JWTConfig",
    "PasswordConfig",
    "RBACConfig",
]
