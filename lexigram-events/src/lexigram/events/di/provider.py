"""EventsProvider implementation (M-01).

Thin orchestrator that coordinates Events sub-providers.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts.core import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
    ProviderPriority,
)
from lexigram.di.provider import Provider
from lexigram.events.config import EventsConfig
from lexigram.events.di.sub_providers.bus_provider import BusSubProvider
from lexigram.events.di.sub_providers.handler_provider import HandlerSubProvider
from lexigram.events.di.sub_providers.manager_provider import ManagerSubProvider
from lexigram.events.di.sub_providers.store_provider import StoreSubProvider
from lexigram.events.types import EventStoreBackend
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class EventsProvider(Provider):
    """Thin orchestrator that coordinates Events sub-providers (M-01).

    Delegates all setup, lifecycle, and container-registration work to:

    - :class:`StoreSubProvider`
    - :class:`BusSubProvider`
    - :class:`HandlerSubProvider`
    - :class:`ManagerSubProvider`

    Public API is unchanged from the monolithic version.
    """

    name = "events"
    priority = ProviderPriority.INFRASTRUCTURE
    config_key: str | None = "events"
    config_model: type | None = EventsConfig

    def __init__(
        self,
        config: EventsConfig | dict[str, Any] | None = None,
        handler_modules: list[str] | None = None,
    ) -> None:
        super().__init__()

        if isinstance(config, dict):
            config = EventsConfig(**config)

        self._config: EventsConfig = config or EventsConfig(
            event_store_backend=EventStoreBackend.MEMORY,
            debug=False,
        )
        self._handler_modules = handler_modules or []

        self._stores = StoreSubProvider(self._config)
        self._buses = BusSubProvider(self._config)
        self._managers: ManagerSubProvider | None = None

    @classmethod
    def from_config(cls, config: EventsConfig, **context: Any) -> EventsProvider:
        """Create EventsProvider from config."""
        return cls(config=config, handler_modules=context.get("handler_modules"))

    @property
    def config(self) -> EventsConfig:
        return self._config

    @config.setter
    def config(self, value: EventsConfig) -> None:
        """Allow orchestrator to auto-inject config from LexigramConfig."""
        if isinstance(value, dict):
            value = EventsConfig(**value)
        self._config = value
        self._stores = StoreSubProvider(self._config)
        self._buses = BusSubProvider(self._config)

    @property
    def event_store(self) -> Any:
        return self._stores.event_store

    @property
    def snapshot_manager(self) -> Any:
        return self._stores.snapshot_manager

    @property
    def command_bus(self) -> Any:
        return self._buses.command_bus

    @property
    def query_bus(self) -> Any:
        return self._buses.query_bus

    @property
    def event_bus(self) -> Any:
        return self._buses.event_bus

    @property
    def projection_manager(self) -> Any:
        return self._managers.projection_manager if self._managers else None

    @property
    def saga_manager(self) -> Any:
        return self._managers.saga_manager if self._managers else None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register all events components with the DI container."""
        await self._stores.setup(container)
        self._stores.register(container)

        await self._buses.setup()
        self._buses.register(container)

        handlers = HandlerSubProvider(
            config=self._config,
            handler_modules=self._handler_modules,
            command_bus=self._buses.command_bus,
            query_bus=self._buses.query_bus,
            event_bus=self._buses.event_bus,
        )
        await handlers.setup(container)  # type: ignore[arg-type]

        self._managers = ManagerSubProvider(
            config=self._config,
            event_store=self._stores.event_store,
        )
        await self._managers.setup(container)
        self._managers.register(container)

        self._register_admin(cast("BootContainerProtocol", container))

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Start buses, managers, and wire optional tracer."""
        from lexigram.contracts.core import HookRegistryProtocol
        from lexigram.contracts.observability.tracing import TracerProtocol

        tracer = await container.resolve_optional(TracerProtocol)
        hooks = await container.resolve_optional(HookRegistryProtocol)
        self._buses.set_tracer(tracer)
        self._buses.set_hook_registry(hooks)

        await self._buses.boot()
        if self._managers:
            await self._managers.boot()
        if self._stores.snapshot_manager and hasattr(
            self._stores.snapshot_manager, "start"
        ):
            await self._stores.snapshot_manager.start()

        await self._wire_adapters(container)

        from lexigram.events.admin.contributor import EventsAdminContributor

        try:
            contributor = await container.resolve(EventsAdminContributor)
            if hasattr(contributor, "on_admin_boot"):
                await contributor.on_admin_boot(container)
        except Exception as exc:  # noqa: BLE001
            logger.warning("events_admin_contributor_boot_failed", error=str(exc))

    async def _wire_adapters(self, container: ContainerResolverProtocol) -> None:
        """Connect registered adapters to the EventBusProtocol when configured."""
        from lexigram.contracts.events import EventBusProtocol
        from lexigram.events.adapters.registry import AdapterRegistry

        event_bus = await container.resolve(EventBusProtocol)
        if event_bus is None:
            return

        registry = AdapterRegistry.with_defaults()
        await registry.wire_all(self._config, event_bus, container)

    async def shutdown(self) -> None:
        """Shutdown all components."""
        await self._stores.teardown()
        if self._managers:
            await self._managers.teardown()

    def _register_admin(self, container: BootContainerProtocol) -> None:
        """Register admin widget handlers and renderer."""
        from lexigram.contracts.admin.protocols import AdminContributorProtocol
        from lexigram.contracts.events import EventBusProtocol
        from lexigram.events.admin.contributor import EventsAdminContributor
        from lexigram.events.admin.handlers.dead_letter_count import (
            DeadLetterCountWidgetHandler,
        )
        from lexigram.events.admin.handlers.events_throughput import (
            EventsThroughputWidgetHandler,
        )
        from lexigram.events.admin.renderer import PackageWidgetRenderer

        container.singleton(
            PackageWidgetRenderer,
            PackageWidgetRenderer,
        )

        async def _create_events_throughput_handler() -> EventsThroughputWidgetHandler:
            event_bus = await container.resolve(EventBusProtocol)
            return EventsThroughputWidgetHandler(event_bus=event_bus)

        async def _create_dead_letter_handler() -> DeadLetterCountWidgetHandler:
            event_bus = await container.resolve(EventBusProtocol)
            return DeadLetterCountWidgetHandler(event_bus=event_bus)

        container.transient(
            EventsThroughputWidgetHandler,
            _create_events_throughput_handler,
        )
        container.transient(
            DeadLetterCountWidgetHandler,
            _create_dead_letter_handler,
        )
        container.singleton(EventsAdminContributor, EventsAdminContributor)
        container.singleton(
            AdminContributorProtocol,
            EventsAdminContributor,
        )

    async def _create_stores(
        self, container: ContainerRegistrarProtocol | None = None
    ) -> None:
        """Compat: delegates to StoreSubProvider.setup()."""
        await self._stores.setup(container)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Aggregate health across stores and buses."""
        start = time.time()
        overall = HealthStatus.HEALTHY
        details: dict[str, Any] = {"components": {}}
        errors: list[str] = []

        bus_health = await self._buses.health_check()
        details["components"].update(bus_health)

        if self._stores.event_store and hasattr(
            self._stores.event_store, "health_check"
        ):
            try:
                sh = await self._stores.event_store.health_check()
                details["components"]["event_store"] = (
                    sh.model_dump() if hasattr(sh, "model_dump") else sh
                )
                if hasattr(sh, "status") and sh.status != HealthStatus.HEALTHY:
                    overall = HealthStatus.DEGRADED
            except (RuntimeError, OSError, AttributeError, LookupError) as exc:
                details["components"]["event_store"] = {
                    "status": "unhealthy",
                    "error": str(exc),
                }
                overall = HealthStatus.DEGRADED
                errors.append(f"EventStoreProtocol: {exc}")
        elif self._stores.event_store:
            details["components"]["event_store"] = {"status": "unknown"}

        return HealthCheckResult(
            component="events",
            status=overall,
            details=details,
            error=" | ".join(errors) if errors else None,
            duration_ms=(time.time() - start) * 1000,
            category=HealthCheckCategory.READINESS,
        )


__all__ = ["EventsProvider"]
