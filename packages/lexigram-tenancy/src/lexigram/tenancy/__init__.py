"""lexigram-tenancy — Multi-tenant resolution, lifecycle, and isolation.

Public surface (lazy-loaded on first access)::

    from lexigram.tenancy import (
        TenancyModule,
        TenancyConfig,
        TenancyProvider,
        TenantLifecycleService,
        TenantConfigService,
        TenantValidator,
        CompositeResolver,
        InMemoryTenantProvider,
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.tenancy.config import (
        ConfigOverridesConfig,
        IntegrationConfig,
        LifecycleConfig,
        ResolutionConfig,
        TenancyConfig,
    )
    from lexigram.tenancy.config_overrides.cache import CachedTenantConfigProvider
    from lexigram.tenancy.config_overrides.service import TenantConfigService
    from lexigram.tenancy.di.provider import TenancyProvider
    from lexigram.tenancy.enforcement.guard import TenantGuard
    from lexigram.tenancy.enforcement.middleware import TenantContextMiddleware
    from lexigram.tenancy.enforcement.validator import TenantValidator
    from lexigram.tenancy.isolation.database import DatabaseIsolationStrategy
    from lexigram.tenancy.isolation.registry import IsolationStrategyRegistry
    from lexigram.tenancy.isolation.row_level import RowLevelIsolationStrategy
    from lexigram.tenancy.lifecycle.provisioner import TenantProvisioner
    from lexigram.tenancy.lifecycle.service import TenantLifecycleService
    from lexigram.tenancy.migration.service import (
        MigrationResult,
        MigrationServiceConfig,
    )
    from lexigram.tenancy.migration.write_pause import WritePauseRegistry
    from lexigram.tenancy.module import TenancyModule
    from lexigram.tenancy.resolution.chain import CompositeResolver
    from lexigram.tenancy.resolution.registry import ResolverRegistry
    from lexigram.tenancy.stores.memory import InMemoryTenantProvider

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "TenancyConfig": ("lexigram.tenancy.config", "TenancyConfig"),
    "ResolutionConfig": ("lexigram.tenancy.config", "ResolutionConfig"),
    "LifecycleConfig": ("lexigram.tenancy.config", "LifecycleConfig"),
    "ConfigOverridesConfig": ("lexigram.tenancy.config", "ConfigOverridesConfig"),
    "IntegrationConfig": ("lexigram.tenancy.config", "IntegrationConfig"),
    "TenancyProvider": ("lexigram.tenancy.di.provider", "TenancyProvider"),
    "TenantConfigService": (
        "lexigram.tenancy.config_overrides.service",
        "TenantConfigService",
    ),
    "CachedTenantConfigProvider": (
        "lexigram.tenancy.config_overrides.cache",
        "CachedTenantConfigProvider",
    ),
    "TenantGuard": ("lexigram.tenancy.enforcement.guard", "TenantGuard"),
    "TenantContextMiddleware": (
        "lexigram.tenancy.enforcement.middleware",
        "TenantContextMiddleware",
    ),
    "TenantValidator": ("lexigram.tenancy.enforcement.validator", "TenantValidator"),
    "DatabaseIsolationStrategy": (
        "lexigram.tenancy.isolation.database",
        "DatabaseIsolationStrategy",
    ),
    "IsolationStrategyRegistry": (
        "lexigram.tenancy.isolation.registry",
        "IsolationStrategyRegistry",
    ),
    "RowLevelIsolationStrategy": (
        "lexigram.tenancy.isolation.row_level",
        "RowLevelIsolationStrategy",
    ),
    "SchemaIsolationStrategy": (
        "lexigram.tenancy.isolation.schema",
        "SchemaIsolationStrategy",
    ),
    "TenantProvisioner": (
        "lexigram.tenancy.lifecycle.provisioner",
        "TenantProvisioner",
    ),
    "TenantLifecycleService": (
        "lexigram.tenancy.lifecycle.service",
        "TenantLifecycleService",
    ),
    "MigrationResult": ("lexigram.tenancy.migration.service", "MigrationResult"),
    "MigrationServiceConfig": (
        "lexigram.tenancy.migration.service",
        "MigrationServiceConfig",
    ),
    "TenancyModule": ("lexigram.tenancy.module", "TenancyModule"),
    "TenantMigrationService": (
        "lexigram.tenancy.migration.service",
        "TenantMigrationService",
    ),
    "WritePauseRegistry": (
        "lexigram.tenancy.migration.write_pause",
        "WritePauseRegistry",
    ),
    "CompositeResolver": ("lexigram.tenancy.resolution.chain", "CompositeResolver"),
    "ResolverRegistry": ("lexigram.tenancy.resolution.registry", "ResolverRegistry"),
    "InMemoryTenantProvider": (
        "lexigram.tenancy.stores.memory",
        "InMemoryTenantProvider",
    ),
}


def __getattr__(name: str) -> Any:
    """Lazy-load public symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = list(_LAZY_IMPORTS.keys())
