"""TenancyModule — DI/IoC entry point for lexigram-tenancy."""

from __future__ import annotations

from lexigram.contracts.tenancy.protocols import (
    TenantConfigProviderProtocol,
    TenantProviderProtocol,
)
from lexigram.di.module import DynamicModule, Module, module
from lexigram.tenancy.config import (
    IntegrationConfig,
    LifecycleConfig,
    ResolutionConfig,
    TenancyConfig,
)
from lexigram.tenancy.config_overrides.service import TenantConfigService
from lexigram.tenancy.di.provider import TenancyProvider
from lexigram.tenancy.enforcement.validator import TenantValidator
from lexigram.tenancy.isolation.registry import IsolationStrategyRegistry
from lexigram.tenancy.lifecycle.service import TenantLifecycleService
from lexigram.tenancy.migration.service import TenantMigrationService
from lexigram.tenancy.resolution.chain import CompositeResolver


@module()
class TenancyModule(Module):
    """Multi-tenant resolution, lifecycle, isolation, and configuration.

    Use :meth:`configure` to register a fully configured tenancy stack.
    Use :meth:`stub` for test environments (in-memory store, header resolver
    only, no isolation provisioning).

    Usage::

        app.add_module(TenancyModule.configure(
            config=TenancyConfig(
                resolution=ResolutionConfig(resolvers=["header"]),
            )
        ))
    """

    @classmethod
    def configure(
        cls,
        config: TenancyConfig | None = None,
    ) -> DynamicModule:
        """Create a configured tenancy module.

        Args:
            config: :class:`~lexigram.tenancy.config.TenancyConfig` or
                ``None`` for framework defaults.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        provider = TenancyProvider(config)
        return DynamicModule(
            module=cls,
            providers=[provider],
            exports=[
                TenantProviderProtocol,
                TenantConfigProviderProtocol,
                CompositeResolver,
                TenantValidator,
                TenantLifecycleService,
                TenantConfigService,
                TenantMigrationService,
                IsolationStrategyRegistry,
            ],
        )

    @classmethod
    def stub(cls, config: object = None) -> DynamicModule:
        """Create a test-friendly tenancy module.

        Uses an in-memory store, header resolver only, no isolation
        provisioning, and no cache key prefix or SQL bridge.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` for testing.
        """
        config = TenancyConfig(
            resolution=ResolutionConfig(resolvers=["header"]),
            lifecycle=LifecycleConfig(auto_provision_isolation=False),
            integration=IntegrationConfig(
                cache_key_prefix=False,
                sql_context_bridge=False,
            ),
        )
        return DynamicModule(
            module=cls,
            providers=[TenancyProvider(config)],
            exports=[
                TenantProviderProtocol,
                TenantConfigProviderProtocol,
            ],
        )


__all__ = ["TenancyModule"]
