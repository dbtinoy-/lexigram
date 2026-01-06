"""PlatformProvider — DI composition root for the multi-tenant SaaS platform.

Wires together:

- :class:`~lexigram_example_platform.repositories.tenant_repository.TenantRepositoryProtocol`
  → :class:`~lexigram_example_platform.repositories.tenant_repository.InMemoryTenantRepository`
- :class:`~lexigram_example_platform.repositories.membership_repository.MembershipRepositoryProtocol`
  → :class:`~lexigram_example_platform.repositories.membership_repository.InMemoryMembershipRepository`
- :class:`~lexigram.contracts.events.protocols.EventBusProtocol`
  → :class:`_StubEventBus` (replace with ``lexigram-events`` bus in production)
- :class:`~lexigram.features.manager.FlagManager` seeded with platform feature flags
- :class:`~lexigram_example_platform.services.tenant_service.TenantService`
- :class:`~lexigram_example_platform.services.membership_service.MembershipService`

Production upgrade path
-----------------------
Replace each ``_Stub*`` or ``InMemory*`` binding with a real implementation
by overriding :meth:`PlatformProvider.register`.  No service or domain code
changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.core import ProviderPriority
from lexigram.contracts.events.protocols import EventBusProtocol
from lexigram.contracts.exceptions.events import EventError
from lexigram.di.provider import Provider
from lexigram.features.backends.local import LocalProvider
from lexigram.features.manager import FlagManager
from lexigram.features.types import Flag, FlagType
from lexigram.logging import get_logger
from lexigram.result import Ok, Result

from lexigram_example_platform.admin.contributor import PlatformAdminContributor
from lexigram_example_platform.config import PlatformConfig
from lexigram_example_platform.repositories.membership_repository import (
    InMemoryMembershipRepository,
    MembershipRepositoryProtocol,
)
from lexigram_example_platform.repositories.tenant_repository import (
    InMemoryTenantRepository,
    TenantRepositoryProtocol,
)
from lexigram_example_platform.services.membership_service import MembershipService
from lexigram_example_platform.services.tenant_service import TenantService

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Development-only stubs
#
# Replace with production implementations (e.g. from lexigram-events,
# lexigram-notification) by overriding the provider bindings.
# ---------------------------------------------------------------------------


class _StubEventBus:
    """No-op event bus that logs publications instead of dispatching them.

    Replace with the real ``EventBus`` from ``lexigram-events`` in production.
    """

    async def publish(self, event: Any) -> Result[None, EventError]:
        """Log the event and return ``Ok(None)``.

        Args:
            event: Domain event to (stub-)publish.

        Returns:
            Always ``Ok(None)`` — the stub never fails.
        """
        logger.debug(
            "stub_event_bus.publish",
            event_type=type(event).__name__,
        )
        return Ok(None)

    def subscribe(self, event_type: type, handler: Any) -> None:
        """No-op subscription (stub).

        Args:
            event_type: Event class to subscribe to.
            handler: Handler to (not) register.
        """


def _build_flag_manager(enabled: bool) -> FlagManager:
    """Build a :class:`~lexigram.features.manager.FlagManager` seeded with platform flags.

    The flags are defined here as ``LocalProvider`` entries.  In production,
    layer a ``CacheBackendFlagProvider`` or a remote provider via
    ``ChainedProvider``.

    Args:
        enabled: When ``False``, all flags evaluate to ``False`` (kill-switch).

    Returns:
        A fully configured :class:`FlagManager` instance.
    """
    flags = {
        "advanced_analytics": Flag(
            name="advanced_analytics",
            type=FlagType.BOOLEAN,
            enabled=enabled,
            description="Enable advanced analytics dashboard for tenants.",
        ),
        "multi_region_support": Flag(
            name="multi_region_support",
            type=FlagType.BOOLEAN,
            enabled=False,
            description="Allow tenants to select their data residency region.",
        ),
        "self_serve_billing": Flag(
            name="self_serve_billing",
            type=FlagType.BOOLEAN,
            enabled=enabled,
            description="Enable self-serve billing portal for tenant owners.",
        ),
        "beta_api_v2": Flag(
            name="beta_api_v2",
            type=FlagType.PERCENTAGE,
            enabled=enabled,
            percentage=10,
            description="Gradual rollout of the v2 API surface (10 % of tenants).",
        ),
    }
    local_provider = LocalProvider(flags=flags)
    return FlagManager(provider=local_provider)


class PlatformProvider(Provider):
    """Composition root — registers and boots all platform services.

    Binds repository protocols to in-memory implementations (suitable for
    development and testing), wires the stub event bus, bootstraps feature
    flags, and registers application services as container singletons.

    Args:
        config: Platform configuration.  Defaults to environment-sourced values.
    """

    name = "platform"
    priority = ProviderPriority.NORMAL

    def __init__(self, config: PlatformConfig | None = None) -> None:
        super().__init__()
        self._config = config or PlatformConfig()

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind all platform services and infrastructure into the container.

        Registrations (in order):

        1. :class:`~lexigram_example_platform.config.PlatformConfig`
        2. :class:`~lexigram_example_platform.repositories.tenant_repository.TenantRepositoryProtocol`
        3. :class:`~lexigram_example_platform.repositories.membership_repository.MembershipRepositoryProtocol`
        4. :class:`~lexigram.contracts.events.protocols.EventBusProtocol` (stub)
        5. :class:`~lexigram.features.manager.FlagManager`
        6. :class:`~lexigram_example_platform.services.tenant_service.TenantService`
        7. :class:`~lexigram_example_platform.services.membership_service.MembershipService`

        Args:
            container: DI container registrar (provided by the framework).
        """
        container.singleton(PlatformConfig, self._config)

        tenant_repo = InMemoryTenantRepository()
        container.singleton(TenantRepositoryProtocol, tenant_repo)

        membership_repo = InMemoryMembershipRepository()
        container.singleton(MembershipRepositoryProtocol, membership_repo)

        event_bus = _StubEventBus()
        container.singleton(EventBusProtocol, event_bus)

        flag_manager = _build_flag_manager(
            enabled=self._config.feature_flags_enabled
        )
        container.singleton(FlagManager, flag_manager)

        tenant_service = TenantService(
            repo=tenant_repo,
            event_bus=event_bus,
        )
        container.singleton(TenantService, tenant_service)

        membership_service = MembershipService(
            repo=membership_repo,
            tenant_repo=tenant_repo,
            event_bus=event_bus,
        )
        container.singleton(MembershipService, membership_service)

        logger.info(
            "platform_provider.registered",
            event_driver=self._config.event_driver,
            feature_flags_enabled=self._config.feature_flags_enabled,
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot phase — resolve services and register the admin contributor.

        The container is frozen at this point; all resolutions are safe.

        Args:
            container: DI container resolver (provided by the framework).
        """
        contributor = PlatformAdminContributor()
        try:
            from lexigram.admin.registry import AdminContributorRegistry

            registry = await container.resolve_optional(AdminContributorRegistry)
            if registry is not None:
                registry.register(contributor)
                logger.info("platform_provider.admin_contributor_registered")
        except ImportError:
            logger.debug(
                "platform_provider.admin_registry_unavailable",
                hint="lexigram-admin not installed; skipping contributor registration.",
            )

        logger.info("platform_provider.booted")

    async def shutdown(self) -> None:
        """No-op shutdown — in-memory resources require no cleanup."""
        logger.info("platform_provider.shutdown")


__all__ = ["PlatformProvider"]
