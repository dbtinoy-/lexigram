from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.container import (
        ContainerResolverProtocol,
    )
    from lexigram.events.config import EventsConfig
    from lexigram.events.stores.base import AbstractEventStore

logger = get_logger(__name__)

# Type alias for store factory callables
_StoreFactoryCallable = Callable[..., Any]


class EventStoreRegistry:
    """Registry that maps EventStoreBackend keys to store factory callables.

    Provides a clean alternative to if/elif chains for store dispatch.
    Factories are callables that accept (config, container) and return an EventStoreBase.

    Usage::

        registry = EventStoreRegistry.with_defaults()
        store = registry.create("postgres", config, container)
    """

    def __init__(self) -> None:
        """Initialize with an empty registry."""
        self._factories: dict[str, _StoreFactoryCallable] = {}

    @classmethod
    def with_defaults(cls) -> EventStoreRegistry:
        """Create a registry pre-populated with all built-in store factories."""
        from lexigram.events.stores.registry_factories import (
            create_inmemory_store,
            create_mongodb_store,
            create_postgres_store,
            create_sqlite_store,
        )

        registry = cls()
        registry.register("memory", create_inmemory_store)
        registry.register("postgres", create_postgres_store)
        registry.register("mongodb", create_mongodb_store)
        registry.register("sqlite", create_sqlite_store)
        return registry

    def register(self, key: str, factory: _StoreFactoryCallable) -> None:
        """Register a store factory under the given backend key.

        Args:
            key: The EventStoreBackend value string (e.g., 'postgres').
            factory: Callable(config, container) -> AbstractEventStore.
        """
        self._factories[key] = factory

    def create(
        self,
        key: str,
        config: EventsConfig,
        container: ContainerResolverProtocol,
    ) -> AbstractEventStore:
        """Create a store for the given backend key.

        Args:
            key: The EventStoreBackend value string.
            config: The EventsConfig instance.
            container: The DI container resolver.

        Returns:
            An AbstractEventStore instance.

        Raises:
            KeyError: If no factory is registered for the given key.
        """
        factory = self._factories.get(key)
        if factory is None:
            available = list(self._factories.keys())
            raise KeyError(
                f"No store factory registered for backend '{key}'. "
                f"Available: {available}"
            )
        logger.debug("creating_event_store", backend=key)
        store: AbstractEventStore = factory(config, container)
        return store

    def keys(self) -> list[str]:
        """Return all registered backend keys.

        Returns:
            List of registered backend key strings.
        """
        return list(self._factories.keys())
