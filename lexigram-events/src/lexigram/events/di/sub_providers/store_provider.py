"""Sub-provider for AbstractEventStore and AbstractSnapshotStore creation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerRegistrarProtocol
    from lexigram.events.config import EventsConfig
    from lexigram.events.stores.registry import EventStoreRegistry


class StoreSubProvider:
    """Focused sub-provider: creates and owns AbstractEventStore + AbstractSnapshotStore."""

    def __init__(
        self,
        config: EventsConfig,
        registry: EventStoreRegistry | None = None,
    ) -> None:
        from lexigram.events.stores.registry import EventStoreRegistry as _Registry
        from lexigram.logging import get_logger

        self._logger = get_logger(__name__)
        self._config = config
        self._registry = registry or _Registry.with_defaults()
        self.event_store: Any = None
        self.snapshot_store: Any = None
        self.snapshot_manager: Any = None

    async def setup(self, container: ContainerRegistrarProtocol | None = None) -> None:
        """Create all stores based on configuration."""
        from lexigram.events.constants import StoreType
        from lexigram.events.stores import InMemorySnapshotStore, SnapshotManager
        from lexigram.events.types import EventStoreBackend

        backend_key = self._config.event_store_backend.value

        try:
            self.event_store = self._registry.create(
                backend_key, self._config, container
            )
        except KeyError as exc:
            raise ValueError(f"Unknown event store backend: {backend_key!r}") from exc
        except Exception as exc:  # noqa: BLE001 — infrastructure init; unknown backend factory failure; logs and re-raises
            self._logger.error(
                "events.store_creation_failed",
                store_type=backend_key,
                error=str(exc),
                exc_info=True,
            )
            raise

        snapshots_config = self._config.snapshots
        if isinstance(snapshots_config, dict):
            self._logger.debug(
                "snapshots_skipped", reason="dict_config_not_fully_typed"
            )
        elif snapshots_config and snapshots_config.enabled:
            memory_snapshots_enabled = True
            if backend_key in (StoreType.MEMORY, EventStoreBackend.MEMORY.value):
                memory_snapshots_enabled = self._config.memory.enable_snapshots
            if memory_snapshots_enabled:
                self.snapshot_store = InMemorySnapshotStore()
                self.snapshot_manager = SnapshotManager(
                    event_store=self.event_store,
                    snapshot_store=self.snapshot_store,
                    config=snapshots_config,
                )

    async def teardown(self) -> None:
        """Close store connections."""
        if self.event_store and hasattr(self.event_store, "close"):
            await self.event_store.close()
        if self.snapshot_store and hasattr(self.snapshot_store, "close"):
            await self.snapshot_store.close()

    def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register stores into the DI container."""
        from typing import cast

        from lexigram.contracts.events import EventStoreProtocol
        from lexigram.events.stores import (
            AbstractEventStore,
            AbstractSnapshotStore,
            SnapshotManager,
        )

        if self.event_store:
            container.singleton(cast("Any", AbstractEventStore), self.event_store)
            container.singleton(cast("Any", EventStoreProtocol), self.event_store)
        if self.snapshot_store:
            container.singleton(cast("Any", AbstractSnapshotStore), self.snapshot_store)
        if self.snapshot_manager:
            container.singleton(cast("Any", SnapshotManager), self.snapshot_manager)


__all__ = ["StoreSubProvider"]
