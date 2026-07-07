"""Admin configuration models and factory helpers."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, ClassVar, Literal, cast

from lexigram.admin.constants import ENV_NESTED_DELIMITER, ENV_PREFIX
from lexigram.admin.resources.config import ResourceConfig, TableConfiguration
from lexigram.config import BaseConfig
from lexigram.domain import DomainModel
from lexigram.validation import ConfigDict, Field, SecretStr, model_validator


@dataclass(init=False)
class ResourceDefaults(DomainModel):
    """Default configuration for all resources."""

    per_page: int = Field(default=20, ge=1, le=1000)
    enable_search: bool = Field(default=True)
    enable_export: bool = Field(default=True)
    enable_bulk_actions: bool = Field(default=True)
    action_layout: Literal["horizontal", "vertical", "dropdown"] = Field(
        default="horizontal",
    )
    soft_delete: bool = Field(default=True)
    timestamp_fields: bool = Field(default=True)

    model_config = {"extra": "forbid"}


@dataclass(init=False)
class TableDefaults(DomainModel):
    """Default configuration for DataTables."""

    reorderable_columns: bool = Field(default=False)
    enable_column_visibility: bool = Field(default=True)
    sticky_header: bool = Field(default=True)
    virtualized: bool = Field(default=False)
    row_height: int = Field(default=48, ge=24, le=120)
    zebra_stripes: bool = Field(default=True)
    hover_highlight: bool = Field(default=True)

    model_config = {"extra": "forbid"}


@dataclass(init=False)
class FormDefaults(DomainModel):
    """Default configuration for Forms."""

    show_required_indicator: bool = Field(default=True)
    autosave_enabled: bool = Field(default=False)
    autosave_interval_ms: int = Field(default=30000, ge=1000)
    confirm_unsaved_changes: bool = Field(default=True)
    inline_validation: bool = Field(default=True)

    model_config = {"extra": "forbid"}


@dataclass(init=False)
class ResourceYAMLConfig(DomainModel):
    """Per-resource configuration from YAML."""

    enabled: bool = Field(default=True)
    icon: str | None = None
    label: str | None = None
    label_plural: str | None = None
    per_page: int | None = Field(default=None, ge=1, le=1000)
    searchable_fields: list[str] | None = None
    default_sort: str | None = None
    default_sort_order: Literal["asc", "desc"] = "desc"
    permissions: dict[str, list[str]] | None = None

    model_config = {"extra": "allow"}


@dataclass(init=False)
class AdminNavigationGroup(DomainModel):
    """Navigation group configuration."""

    label: str
    icon: str | None = None
    order: int = Field(default=100, ge=0)
    resources: list[str] = Field(default_factory=list)
    permission: str | None = None
    collapsible: bool = Field(default=True)
    collapsed_by_default: bool = Field(default=False)

    model_config = {"extra": "forbid"}


@dataclass(init=False)
class AdminFeaturesConfig(DomainModel):
    """Feature flags for admin functionality."""

    # UI Features
    command_palette: bool = Field(default=True)
    keyboard_shortcuts: bool = Field(default=True)
    theme_toggle: bool = Field(default=True)
    search: bool = Field(default=True)

    # UX Features
    optimistic_updates: bool = Field(default=True)
    undo_redo: bool = Field(default=True)
    autosave: bool = Field(default=False)

    # Advanced Features
    audit_logging: bool = Field(default=True)
    activity_feed: bool = Field(default=False)
    notifications: bool = Field(default=True)
    webhooks: bool = Field(default=False)
    api_docs: bool = Field(default=True)

    model_config = {"extra": "allow"}


@dataclass(init=False)
class AdminRbacConfig(DomainModel):
    """RBAC editing-page configuration."""

    #: Role name granted wildcard admin rights.  Matches the role string
    #: already special-cased by settings/widgets/impersonation.
    super_admin_role: str = Field(default="superadmin")


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

    setup_token: str | None = Field(
        default=None,
        description="Optional ADMIN_SETUP_TOKEN — when set, must be provided during first-run setup.",
    )
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
            legacy = os.getenv("ADMIN_SETUP_TOKEN")
            if legacy:
                return {**data, "setup_token": legacy}
        return data

    model_config = {"extra": "forbid"}


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
            self.env == "production"
            and self.session_secret.get_secret_value().lower() in insecure_defaults
        ):
            raise ValueError(
                "CRITICAL SECURITY ERROR: Default admin session_secret detected in PRODUCTION.\n"
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


@dataclass(init=False)
class AdminAuditConfig(DomainModel):
    """Audit logging configuration."""

    read_audit_enabled: bool = Field(
        default=False,
        description="Log read operations (off by default; compliance mode only).",
    )
    redaction_field_denylist: tuple[str, ...] = Field(
        default_factory=lambda: ("email", "phone", "password_hash", "ssn"),
        description="Field names whose values are always redacted in audit payloads.",
    )
    redaction_patterns: tuple[str, ...] = Field(
        default_factory=lambda: ("email", "phone"),
        description="Pattern-based redaction strategies to apply.",
    )

    model_config = {"extra": "forbid"}


@dataclass(init=False)
class AdminUIConfig(DomainModel):
    """UI/Theme configuration."""

    theme: Literal["light", "dark", "system"] = Field(default="system")
    primary_color: str = Field(default="#6B7280")
    sidebar_width: int = Field(default=256, ge=200, le=400)
    sidebar_collapsed_width: int = Field(default=64, ge=48, le=100)
    content_max_width: int | None = Field(default=None, ge=800)
    logo_url: str | None = None
    favicon_url: str | None = None

    model_config = {"extra": "allow"}


@dataclass(init=False)
class AdminRateLimitConfig(DomainModel):
    """Rate limiting configuration."""

    enabled: bool = Field(default=True)
    requests_per_minute: int = Field(default=60, ge=1)
    requests_per_hour: int = Field(default=1000, ge=1)
    burst_size: int = Field(default=10, ge=1)

    # Per-action limits
    create_per_minute: int = Field(default=30)
    update_per_minute: int = Field(default=60)
    delete_per_minute: int = Field(default=20)
    bulk_per_minute: int = Field(default=5)

    model_config = {"extra": "forbid"}


@dataclass(init=False)
class ContributorConfig(DomainModel):
    """Per-contributor enable/disable and options."""

    enabled: bool = Field(default=True)
    options: dict[str, Any] = Field(default_factory=dict)


@dataclass(init=False)
class DashboardLayoutConfig(DomainModel):
    """Dashboard layout configuration."""

    widget_refresh_default: int = Field(default=30)
    max_widgets: int = Field(default=20)
    layout: Literal["grid", "masonry"] = Field(default="grid")


@dataclass(init=False)
class TenancyConfig(DomainModel):
    """Multi-tenancy configuration for admin.

    Controls tenant resolution, data isolation, and route scoping.

    Attributes:
        enabled: Enable multi-tenancy support.
        tenant_field: Field name used for tenant data filtering (default ``"tenant_id"``).
        header_name: HTTP header name for tenant ID resolution (default ``"x-tenant-id"``).
        cookie_name: Cookie name for tenant ID resolution (default ``"admin_tenant"``).
        default_tenant_id: Fallback tenant ID when none can be resolved.
        route_prefix_template: If set (e.g. ``"{tenant}"``), routes are prefixed
            with the resolved tenant ID. Empty means no route prefix.
    """

    enabled: bool = Field(default=False)
    tenant_field: str = Field(default="tenant_id")
    header_name: str = Field(default="x-tenant-id")
    cookie_name: str = Field(default="admin_tenant")
    default_tenant_id: str = Field(default="")
    route_prefix_template: str = Field(default="")

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Data & Observability configs
# ---------------------------------------------------------------------------


@dataclass(init=False)
class AdminDataConfig(DomainModel):
    query_timeout_seconds: int = Field(default=5, ge=1, le=120)


@dataclass(init=False)
class AdminObservabilityConfig(DomainModel):
    metrics_enabled: bool = Field(default=True)
    high_cardinality_labels_enabled: bool = Field(default=False)


# ---------------------------------------------------------------------------
# Integration configs
# ---------------------------------------------------------------------------


@dataclass(init=False)
class CacheIntegrationConfig(DomainModel):
    """Configuration for the optional cache integration.

    Controls ``lexigram-cache`` usage from admin resources.
    """

    enabled: bool = Field(default=True)
    default_ttl_seconds: int = Field(default=60, ge=1)
    key_prefix: str = Field(default="admin")


@dataclass(init=False)
class TasksIntegrationConfig(DomainModel):
    """Configuration for the optional tasks integration.

    Controls ``lexigram-tasks`` usage from admin bulk actions.
    """

    enabled: bool = Field(default=True)
    bulk_threshold: int = Field(default=25, ge=1)


@dataclass(init=False)
class SearchIntegrationConfig(DomainModel):
    """Configuration for the optional search integration."""

    enabled: bool = Field(default=True)
    fallback_to_like: bool = Field(default=True)


@dataclass(init=False)
class ResilienceIntegrationConfig(DomainModel):
    """Configuration for the optional resilience integration."""

    enabled: bool = Field(default=True)
    retry_max_attempts: int = Field(default=3, ge=1)
    circuit_failure_threshold: int = Field(default=5, ge=1)


@dataclass(init=False)
class StorageIntegrationConfig(DomainModel):
    """Configuration for the optional storage integration."""

    enabled: bool = Field(default=True)
    presigned_url_expiry: int = Field(default=3600, ge=60)


@dataclass(init=False)
class FeaturesIntegrationConfig(DomainModel):
    """Configuration for the optional feature-flags integration."""

    enabled: bool = Field(default=True)


@dataclass(init=False)
class MonitorIntegrationConfig(DomainModel):
    """Configuration for the optional monitoring integration."""

    enabled: bool = Field(default=True)


@dataclass(init=False)
class AdminIntegrationsConfig(DomainModel):
    """Aggregate configuration for all optional integrations."""

    cache: CacheIntegrationConfig = Field(default_factory=CacheIntegrationConfig)
    tasks: TasksIntegrationConfig = Field(default_factory=TasksIntegrationConfig)
    search: SearchIntegrationConfig = Field(default_factory=SearchIntegrationConfig)
    resilience: ResilienceIntegrationConfig = Field(
        default_factory=ResilienceIntegrationConfig,
    )
    storage: StorageIntegrationConfig = Field(
        default_factory=StorageIntegrationConfig,
    )
    features: FeaturesIntegrationConfig = Field(
        default_factory=FeaturesIntegrationConfig,
    )
    monitor: MonitorIntegrationConfig = Field(default_factory=MonitorIntegrationConfig)
    enabled: bool = Field(default=True)

    model_config = {"extra": "forbid"}


@dataclass(init=False)
class FrameworkPagesConfig(DomainModel):
    """Framework management pages configuration."""

    enabled: bool = Field(default=True)
    require_permission: str = Field(default="admin:framework:access")


@dataclass(init=False)
@dataclass(init=False)
class ClusterSpec(DomainModel):
    """Declarative description of an extra cluster.

    Registered clusters get a routable center at ``/admin/{slug}`` with
    its own landing page, namespaced child URLs, secondary sidebar, and
    primary-sidebar collapse — no per-cluster code required.
    """

    name: str = Field(description="Cluster key (used to derive slug/group when unset)")
    label: str = Field(description="Display label")
    icon: str | None = Field(default=None, description="Icon name")
    order: int = Field(default=0, description="Sort order in the registry")
    collapsible: bool = Field(default=True)
    collapsed_by_default: bool = Field(default=False)
    slug: str = Field(default="", description="URL segment (defaults to name)")
    group: str = Field(default="", description="Navigation group (defaults to name)")
    description: str | None = Field(default=None)


@dataclass(init=False)
class AdminClustersConfig(DomainModel):
    """Aggregate configuration for cluster centers."""

    extra: list[ClusterSpec] = Field(
        default_factory=list,
        description="Extra clusters beyond the built-in infrastructure cluster",
    )


class AdminConfig(BaseConfig):
    """Complete admin configuration - SINGLE SOURCE OF TRUTH.

    This model represents the full configuration hierarchy for lexigram-admin.
    Configuration is loaded from:
    1. Pydantic defaults (this model)
    2. application.yaml (admin: section)
    3. Environment variables (LEX_ADMIN_*)
    4. Runtime config (hot-reloadable)

    Attributes:
        name: Configuration name (default: "admin")
        enabled: Whether admin module is enabled
        title: Admin UI title
        prefix: Admin URL prefix
        htmx_prefix: HTMX endpoint prefix
        api_prefix: API endpoint prefix
        static_prefix: Static files prefix
        require_auth: Require authentication
        debug: Debug mode
        templates_dir: Templates directory path
        static_dir: Static files directory path
        auth: Authentication settings
        features: Feature toggles
    """

    model_config = cast(
        "ConfigDict",
        {
            "env_prefix": ENV_PREFIX,
            "env_nested_delimiter": ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    config_section: ClassVar[str] = "admin"

    # Section identifier (used by config discovery)
    name: str = "admin"
    enabled: bool = True

    # Core Settings
    title: str = Field(default="Lexigram Admin")
    prefix: str = Field(default="/admin")
    htmx_prefix: str = Field(default="/admin/htmx")
    api_prefix: str = Field(default="/admin/api")
    static_prefix: str = Field(default="/admin/static")

    # Security
    require_auth: bool = Field(default=True)
    debug: bool = Field(default=False)

    # Paths
    templates_dir: str | None = Field(default=None)
    static_dir: str | None = Field(default=None)

    # Sub-configs
    auth: AdminAuthConfig = Field(default_factory=AdminAuthConfig)
    features: AdminFeaturesConfig = Field(default_factory=AdminFeaturesConfig)
    rbac: AdminRbacConfig = Field(default_factory=AdminRbacConfig)
    data: AdminDataConfig = Field(default_factory=AdminDataConfig)
    clusters: AdminClustersConfig = Field(default_factory=AdminClustersConfig)
    observability: AdminObservabilityConfig = Field(
        default_factory=AdminObservabilityConfig
    )

    ui: AdminUIConfig = Field(default_factory=AdminUIConfig)
    rate_limit: AdminRateLimitConfig = Field(default_factory=AdminRateLimitConfig)
    resource_defaults: ResourceDefaults = Field(default_factory=ResourceDefaults)
    table_defaults: TableDefaults = Field(default_factory=TableDefaults)
    form_defaults: FormDefaults = Field(default_factory=FormDefaults)

    # Resource & Navigation
    resources: dict[str, ResourceYAMLConfig] = Field(default_factory=dict)
    navigation_groups: dict[str, AdminNavigationGroup] = Field(default_factory=dict)
    commands: list[dict[str, Any]] = Field(default_factory=list)
    extensions: dict[str, Any] = Field(default_factory=dict)

    # Audit
    audit: AdminAuditConfig = Field(default_factory=AdminAuditConfig)

    # Multi-tenancy
    tenancy: TenancyConfig = Field(default_factory=TenancyConfig)

    # Optional integrations
    integrations: AdminIntegrationsConfig = Field(
        default_factory=AdminIntegrationsConfig,
    )

    # Contributor system
    contributors: dict[str, ContributorConfig] = Field(default_factory=dict)
    dashboard_layout: DashboardLayoutConfig = Field(
        default_factory=DashboardLayoutConfig
    )
    framework_pages: FrameworkPagesConfig = Field(default_factory=FrameworkPagesConfig)

    contributor_collision_mode: Literal["warn", "error"] = Field(
        default="warn",
        description=(
            "How to handle name collisions when multiple contributors register "
            "widgets, pages, or routes with the same name. 'warn' (default) "
            "logs a warning and keeps the first registration; 'error' raises "
            "at boot time."
        ),
    )

    strict_resource_resolution: bool = Field(
        default=True,
        description=(
            "When True (production default), resource/controller resolution "
            "failures during AdminProvider.boot() raise immediately. "
            "When False, failures are logged and resolution continues with "
            "the remaining resources/controllers. Set to False in dev only."
        ),
    )

    def get_resource_config(self, name: str) -> ResourceYAMLConfig:
        """Get resource config with fallback to defaults."""
        return self.resources.get(name, ResourceYAMLConfig())

    def get_navigation_group(self, name: str) -> AdminNavigationGroup | None:
        """Get navigation group by name."""
        return self.navigation_groups.get(name)

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return getattr(self.features, feature, False)


@dataclass(init=False)
class AdminStorageConfig(DomainModel):
    """Configuration for admin file storage service."""

    base_path: str = Field(
        default="uploads", description="Base path for uploaded files"
    )
    max_file_size: int = Field(
        default=10 * 1024 * 1024,
        description="Maximum allowed file size in bytes (default 10 MB)",
    )
    allowed_content_types: list[str] = Field(
        default_factory=lambda: [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "application/pdf",
            "text/plain",
            "text/csv",
        ],
        description="Allowed MIME content types for uploads",
    )
    presigned_url_expiry: int = Field(
        default=3600,
        description="Default expiry for presigned URLs in seconds",
    )


@dataclass(init=False)
class AdminNotificationConfig(DomainModel):
    """Configuration for admin notification service.

    Controls email notification behaviour, delivery channels, and
    retry settings.
    """

    email_from: str = Field(
        default="admin@localhost", description="Sender email address"
    )
    email_from_name: str = Field(
        default="Admin Panel", description="Sender display name"
    )
    default_channel: str = Field(
        default="email", description="Default delivery channel"
    )
    max_retries: int = Field(default=3, description="Maximum delivery retry attempts")
    retry_delay_seconds: int = Field(default=60, description="Seconds between retries")
    enabled: bool = Field(default=True, description="Enable notification sending")


def make_admin_config(**kwargs: Any) -> AdminConfig:
    """Helper to create admin config from kwargs."""
    return AdminConfig(**kwargs)


def default_admin_config() -> AdminConfig:
    """Factory for default admin configuration."""
    return AdminConfig()


__all__ = [
    "AdminAuditConfig",
    "AdminAuthConfig",
    "AdminConfig",
    "AdminDataConfig",
    "AdminEmailOtpConfig",
    "AdminEmailVerificationConfig",
    "AdminFeaturesConfig",
    "AdminIntegrationsConfig",
    "AdminMfaConfig",
    "AdminNavigationGroup",
    "AdminNotificationConfig",
    "AdminObservabilityConfig",
    "AdminPasswordPolicyConfig",
    "AdminRateLimitConfig",
    "AdminRbacConfig",
    "AdminSecurityConfig",
    "AdminStorageConfig",
    "AdminUIConfig",
    "CacheIntegrationConfig",
    "ContributorConfig",
    "DashboardLayoutConfig",
    "FeaturesIntegrationConfig",
    "FormDefaults",
    "FrameworkPagesConfig",
    "MonitorIntegrationConfig",
    "ResilienceIntegrationConfig",
    "ResourceConfig",
    "ResourceDefaults",
    "ResourceYAMLConfig",
    "SearchIntegrationConfig",
    "StorageIntegrationConfig",
    "TableConfiguration",
    "TableDefaults",
    "TasksIntegrationConfig",
    "TenancyConfig",
    "default_admin_config",
    "make_admin_config",
]
