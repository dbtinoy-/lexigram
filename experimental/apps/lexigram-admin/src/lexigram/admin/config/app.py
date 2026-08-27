"""Top-level AdminConfig and factory helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal, cast

from lexigram.admin.config.auth import AdminAuthConfig
from lexigram.admin.config.defaults import (
    AdminNavigationGroup,
    FormDefaults,
    ResourceDefaults,
    ResourceYAMLConfig,
    TableDefaults,
)
from lexigram.admin.config.features import (
    AdminFeaturesConfig,
    ContributorConfig,
    FrameworkPagesConfig,
)
from lexigram.admin.config.integrations import AdminIntegrationsConfig
from lexigram.admin.config.observability import AdminObservabilityConfig
from lexigram.admin.config.security import (
    AdminAuditConfig,
    AdminRateLimitConfig,
    AdminRbacConfig,
)
from lexigram.admin.config.tenancy import TenancyConfig
from lexigram.admin.config.ui import (
    AdminClustersConfig,
    AdminDataConfig,
    AdminUIConfig,
    DashboardLayoutConfig,
)
from lexigram.admin.constants import ENV_NESTED_DELIMITER, ENV_PREFIX
from lexigram.config import BaseConfig
from lexigram.contracts.core.config import Environment
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
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
    env: Environment | None = Field(None, description="Deployment environment")

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


def make_admin_config(**kwargs: Any) -> AdminConfig:
    """Helper to create admin config from kwargs."""
    return AdminConfig(**kwargs)


def default_admin_config() -> AdminConfig:
    """Factory for default admin configuration."""
    return AdminConfig()
