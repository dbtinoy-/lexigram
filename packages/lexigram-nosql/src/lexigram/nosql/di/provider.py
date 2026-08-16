"""DI provider for lexigram-nosql."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.contracts.data.nosql.nosql import DocumentStoreProtocol
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.nosql.config import NoSQLConfig

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)

# Module-level name so tests can patch "lexigram.nosql.di.provider.MongoDBDocumentStore".
# Falls back to None when the optional motor/pymongo dependency is not installed;
# production code that needs MongoDB must install lexigram-nosql[mongodb].
try:
    from lexigram.nosql.backends.mongodb.backend import MongoDBDocumentStore
except ImportError:
    MongoDBDocumentStore = None  # type: ignore[assignment,misc]


class NoSQLProvider(Provider):
    """Register NoSQL services into the DI container.

    Reads :class:`~lexigram.nosql.config.NoSQLConfig`, creates the
    appropriate driver, and registers it as ``DocumentStoreProtocol``.

    Supports single-backend and multi-backend (``NoSQLConfig.backends``)
    modes.  In multi-backend mode each entry is registered under its name
    via ``container.singleton(name=entry.name)``.  The primary backend
    (``primary=True`` or the first entry) also receives the unnamed
    bindings for backward compatibility.
    """

    name = "nosql"
    priority = ProviderPriority.INFRASTRUCTURE
    config_key: str | None = "nosql"
    config_model: type | None = NoSQLConfig

    def __init__(self, config: NoSQLConfig | None = None) -> None:
        super().__init__()
        self._requested_config = config
        self._config = config or NoSQLConfig()
        self._store: DocumentStoreProtocol | None = None
        # Multi-backend: list of (name, store) 2-tuples
        self._store_services: list[tuple[str, Any]] = []

    @classmethod
    def from_config(cls, config: NoSQLConfig, **context: Any) -> NoSQLProvider:
        """Factory method for DI container setup."""
        return cls(config)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register the NoSQL services."""
        self._config = self._requested_config or (
            self.config
            if isinstance(getattr(self, "config", None), NoSQLConfig)
            else self._config
        )
        container.singleton(NoSQLConfig, self._config)

        if not self._config.enabled:
            logger.info("nosql_disabled", reason="NoSQLConfig.enabled=False")
            return

        if self._config.backends:
            await self._register_multi_backend(container)
        else:
            await self._register_single_backend(container)

    async def _register_single_backend(
        self, container: ContainerRegistrarProtocol
    ) -> None:
        """Register a single NoSQL backend (existing behavior, preserved exactly)."""
        if self._config.driver == "mongodb":
            self._store = self._create_store(self._config)
            container.singleton(DocumentStoreProtocol, self._store)
            container.singleton(MongoDBDocumentStore, self._store)
        else:
            raise ValueError(f"Unsupported NoSQL driver: {self._config.driver}")

        logger.info("nosql_registered", driver=self._config.driver)

    async def _register_multi_backend(
        self, container: ContainerRegistrarProtocol
    ) -> None:
        """Register multiple named NoSQL backends.

        Each backend receives named DI bindings resolvable via
        ``Annotated[DocumentStoreProtocol, Named(entry.name)]``.  The primary
        backend (``primary=True`` or the first entry) also receives the unnamed
        bindings for backward compatibility.
        """
        for entry in self._config.backends:
            backend_cfg = NoSQLConfig.from_named(entry, base=self._config)
            store = self._create_store(backend_cfg)
            self._store_services.append((entry.name, store))

            # Named bindings — resolvable via Annotated[T, Named(entry.name)]
            container.singleton(
                DocumentStoreProtocol,
                factory=lambda s=store: s,
                name=entry.name,
            )
            container.singleton(
                MongoDBDocumentStore,
                factory=lambda s=store: s,
                name=entry.name,
            )

            # Unnamed bindings for primary backend (backward compat)
            if entry.primary or self._config.backends[0] is entry:
                container.singleton(DocumentStoreProtocol, factory=lambda s=store: s)
                container.singleton(MongoDBDocumentStore, factory=lambda s=store: s)

        logger.info(
            "nosql_registered",
            driver="multi",
            count=len(self._config.backends),
        )

    def _create_store(self, cfg: NoSQLConfig) -> Any:
        """Instantiate the correct store implementation for a config."""
        if cfg.driver == "mongodb":
            return MongoDBDocumentStore(cfg.mongodb)
        raise ValueError(f"Unsupported NoSQL driver: {cfg.driver}")

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot phase — connect to all document stores.

        In multi-backend mode all stores are connected in parallel via
        ``asyncio.gather``.  In single-backend mode the existing sequential
        boot is preserved.
        """
        if self._store_services:
            results = await asyncio.gather(
                *(svc.connect() for _, svc in self._store_services),
                return_exceptions=True,
            )
            errors = [r for r in results if isinstance(r, BaseException)]
            if errors:
                for (_, svc), result in zip(
                    self._store_services, results, strict=False
                ):
                    if not isinstance(result, BaseException):
                        try:
                            await svc.disconnect()
                        except Exception as e:  # noqa: BLE001 — best-effort cleanup; all stores must attempt disconnect
                            logger.warning(
                                "nosql_store_disconnect_failed_on_cleanup", error=str(e)
                            )
                raise errors[0]
            logger.info("nosql_connected", count=len(self._store_services))
        elif self._store is not None:
            await self._store.connect()
            logger.info("nosql_connected")

    async def shutdown(self) -> None:
        """Shutdown phase — disconnect from all document stores in reverse order."""
        if self._store_services:
            for _, svc in reversed(self._store_services):
                await svc.disconnect()
            logger.info("nosql_disconnected", count=len(self._store_services))
        elif self._store is not None:
            await self._store.disconnect()
            logger.info("nosql_disconnected")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check provider health across all registered backends.

        In multi-backend mode the overall status is the worst individual status.

        Args:
            timeout: Maximum seconds to wait for health check response.

        Returns:
            HealthCheckResult with status and component details.
        """
        start = time.perf_counter()

        if not self._config.enabled:
            return HealthCheckResult(
                component="nosql",
                status=HealthStatus.DEGRADED,
                message="nosql not enabled",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        if self._store_services:
            results = await asyncio.gather(
                *(svc.health_check(timeout=timeout) for _, svc in self._store_services),
                return_exceptions=True,
            )
            statuses = []
            details: dict[str, str] = {}
            for (name, _), result in zip(self._store_services, results, strict=False):
                if isinstance(result, BaseException):
                    statuses.append(HealthStatus.UNHEALTHY)
                    details[f"nosql:{name}"] = str(result)
                else:
                    statuses.append(result.status)
                    details[f"nosql:{name}"] = result.status.value

            overall = (
                HealthStatus.UNHEALTHY
                if HealthStatus.UNHEALTHY in statuses
                else HealthStatus.DEGRADED
                if HealthStatus.DEGRADED in statuses
                else HealthStatus.HEALTHY
            )
            return HealthCheckResult(
                component="nosql",
                status=overall,
                details=details,
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        if self._store is None:
            return HealthCheckResult(
                component="nosql",
                status=HealthStatus.DEGRADED,
                message="document store not initialized",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        try:
            store_result = await self._store.health_check(timeout=timeout)
            return HealthCheckResult(
                component="nosql",
                status=store_result.status,
                details=store_result.details,
                error=store_result.error,
                duration_ms=(time.perf_counter() - start) * 1000,
            )
        except (ConnectionError, TimeoutError, RuntimeError) as exc:
            return HealthCheckResult(
                component="nosql",
                status=HealthStatus.UNHEALTHY,
                error=str(exc),
                duration_ms=(time.perf_counter() - start) * 1000,
            )


__all__ = ["NoSQLProvider"]
