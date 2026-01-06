"""Admin module for dependency injection."""

from __future__ import annotations

from typing import Any

from lexigram.di.module import DynamicModule, Module, module


@module()
class AdminModule(Module):
    """Lexigram admin panel module.

    Call :meth:`configure` to register the admin panel with its bundle
    provider and contributor system.

    Usage::

        from lexigram.admin.config import AdminConfig

        app.add_modules([
            AdminModule.configure(
                config=AdminConfig(title="My Admin"),
                resources=[UserResource, ProductResource],
            ),
        ])
    """

    @classmethod
    def configure(
        cls,
        config: Any | None = None,
        auth_provider: Any | None = None,
        resources: list[type] | None = None,
        controllers: list[type] | None = None,
        **kwargs: Any,
    ) -> DynamicModule:
        """Create an AdminModule with explicit configuration.

        Args:
            config: AdminConfig or None for defaults.
            auth_provider: Optional AuthProviderProtocol for auth integration.
            resources: List of Resource classes to register.
            controllers: List of controller classes to register.
            **kwargs: Forwarded to AdminProvider.

        Returns:
            A DynamicModule descriptor.
        """
        from lexigram.admin.di.bundle_provider import AdminProvider
        from lexigram.contracts.admin.protocols import (
            AdminContributorRegistryProtocol,
            AdminDashboardProtocol,
        )

        return DynamicModule(
            module=cls,
            providers=[
                AdminProvider(
                    config=config,
                    auth_provider=auth_provider,
                    resources=resources,
                    controllers=controllers,
                    **kwargs,
                ),
            ],
            exports=[AdminContributorRegistryProtocol, AdminDashboardProtocol],
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Return a no-op AdminModule for testing.

        Returns:
            A DynamicModule with default admin configuration.
        """
        from lexigram.admin.di.bundle_provider import AdminProvider
        from lexigram.contracts.admin.protocols import (
            AdminContributorRegistryProtocol,
            AdminDashboardProtocol,
        )

        return DynamicModule(
            module=cls,
            providers=[AdminProvider()],
            exports=[AdminContributorRegistryProtocol, AdminDashboardProtocol],
        )


__all__ = ["AdminModule"]
