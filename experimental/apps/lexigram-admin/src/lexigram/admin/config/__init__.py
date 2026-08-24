"""Admin configuration package — re-exports the full public surface."""

from __future__ import annotations

from lexigram.admin.config.app import AdminConfig as AdminConfig
from lexigram.admin.config.app import default_admin_config as default_admin_config
from lexigram.admin.config.app import make_admin_config as make_admin_config
from lexigram.admin.config.auth import AdminAuthConfig as AdminAuthConfig
from lexigram.admin.config.auth import AdminEmailOtpConfig as AdminEmailOtpConfig
from lexigram.admin.config.auth import (
    AdminEmailVerificationConfig as AdminEmailVerificationConfig,
)
from lexigram.admin.config.auth import AdminMfaConfig as AdminMfaConfig
from lexigram.admin.config.auth import (
    AdminRegistrationConfig as AdminRegistrationConfig,
)
from lexigram.admin.config.defaults import AdminNavigationGroup as AdminNavigationGroup
from lexigram.admin.config.defaults import FormDefaults as FormDefaults
from lexigram.admin.config.defaults import ResourceDefaults as ResourceDefaults
from lexigram.admin.config.defaults import ResourceYAMLConfig as ResourceYAMLConfig
from lexigram.admin.config.defaults import TableDefaults as TableDefaults
from lexigram.admin.config.features import AdminFeaturesConfig as AdminFeaturesConfig
from lexigram.admin.config.features import ContributorConfig as ContributorConfig
from lexigram.admin.config.features import FrameworkPagesConfig as FrameworkPagesConfig
from lexigram.admin.config.integrations import (
    AdminIntegrationsConfig as AdminIntegrationsConfig,
)
from lexigram.admin.config.integrations import (
    CacheIntegrationConfig as CacheIntegrationConfig,
)
from lexigram.admin.config.integrations import (
    FeaturesIntegrationConfig as FeaturesIntegrationConfig,
)
from lexigram.admin.config.integrations import (
    MonitorIntegrationConfig as MonitorIntegrationConfig,
)
from lexigram.admin.config.integrations import (
    ResilienceIntegrationConfig as ResilienceIntegrationConfig,
)
from lexigram.admin.config.integrations import (
    SearchIntegrationConfig as SearchIntegrationConfig,
)
from lexigram.admin.config.integrations import (
    StorageIntegrationConfig as StorageIntegrationConfig,
)
from lexigram.admin.config.integrations import (
    TasksIntegrationConfig as TasksIntegrationConfig,
)
from lexigram.admin.config.observability import (
    AdminNotificationConfig as AdminNotificationConfig,
)
from lexigram.admin.config.observability import (
    AdminObservabilityConfig as AdminObservabilityConfig,
)
from lexigram.admin.config.observability import AdminStorageConfig as AdminStorageConfig
from lexigram.admin.config.security import AdminAuditConfig as AdminAuditConfig
from lexigram.admin.config.security import (
    AdminPasswordPolicyConfig as AdminPasswordPolicyConfig,
)
from lexigram.admin.config.security import AdminRateLimitConfig as AdminRateLimitConfig
from lexigram.admin.config.security import AdminRbacConfig as AdminRbacConfig
from lexigram.admin.config.security import AdminSecurityConfig as AdminSecurityConfig
from lexigram.admin.config.tenancy import TenancyConfig as TenancyConfig
from lexigram.admin.config.ui import AdminClustersConfig as AdminClustersConfig
from lexigram.admin.config.ui import AdminDataConfig as AdminDataConfig
from lexigram.admin.config.ui import AdminUIConfig as AdminUIConfig
from lexigram.admin.config.ui import ClusterSpec as ClusterSpec
from lexigram.admin.config.ui import DashboardLayoutConfig as DashboardLayoutConfig
from lexigram.admin.resources.config import ResourceConfig as ResourceConfig
from lexigram.admin.resources.config import TableConfiguration as TableConfiguration

__all__ = [
    "AdminAuditConfig",
    "AdminAuthConfig",
    "AdminClustersConfig",
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
    "AdminRegistrationConfig",
    "AdminSecurityConfig",
    "AdminStorageConfig",
    "AdminUIConfig",
    "CacheIntegrationConfig",
    "ClusterSpec",
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
