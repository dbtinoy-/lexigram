"""DI provider for lexigram-queue."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts.admin.contributor_boot import (
    summarize_contributor_boot_failure,
)
from lexigram.contracts.core import (
    HealthCheckResult,
    HealthStatus,
    HookRegistryProtocol,
    ProviderPriority,
)
from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.queue.admin.contributor import QueueAdminContributor
from lexigram.queue.admin.handlers.consumer_lag import ConsumerLagWidgetHandler
from lexigram.queue.admin.handlers.failed_messages import FailedMessagesWidgetHandler
from lexigram.queue.admin.handlers.queue_depth import QueueDepthWidgetHandler
from lexigram.queue.config import NamedQueueConfig, QueueConfig
from lexigram.queue.core.dlq import DeadLetterQueue
from lexigram.queue.drivers.registry import QueueDriverRegistry

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )

logger = get_logger(__name__)


class QueueProvider(Provider):
    """Register queue backends into the DI container.

    Reads :class:`~lexigram.queue.config.QueueConfig`, creates the
    appropriate backends, and registers them as ``QueueProtocol``.

    Supports multi-backend (``QueueConfig.backends``) mode. Each entry is
    registered under its name via ``container.singleton(name=entry.name)``.
    The primary backend (``primary=True`` or the first entry) also receives
    the unnamed bindings for backward compatibility.

    Dual-mode configuration: an explicit ``config`` wins; otherwise the
    typed ``queue`` yaml section injected by the orchestrator (via
    ``config_key``) is used; otherwise defaults apply.
    """

    name = "queue"
    priority = ProviderPriority.INFRASTRUCTURE
    config_key: str | None = "queue"
    config_model: type | None = QueueConfig

    def __init__(self, config: QueueConfig | None = None) -> None:
        """Initialize QueueProvider.

        Args:
            config: QueueConfig instance or None for defaults.
        """
        super().__init__()
        self._requested_config = config
        # Kept ``None`` for zero-config construction so the orchestrator can
        # inject the yaml section before register() resolves it.
        self._config: QueueConfig | None = config
        self._queue_services: list[tuple[str, Any]] = []

    @classmethod
    def from_config(cls, config: QueueConfig, **context: Any) -> QueueProvider:
        """Factory method for DI container setup.

        Args:
            config: QueueConfig instance.
            **context: Additional context (unused).

        Returns:
            A new QueueProvider instance.
        """
        return cls(config)

    def _create_backend(self, entry: NamedQueueConfig) -> Any:
        """Instantiate the correct queue backend for a config.

        Args:
            entry: NamedQueueConfig entry.

        Returns:
            Instantiated queue backend.

        Raises:
            ValueError: If driver is unsupported.
        """
        registry = QueueDriverRegistry.with_defaults()
        return registry.create_backend(entry.driver, entry)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind all queue backends into the container.

        Args:
            container: DI container registrar.
        """
        injected = self.config if isinstance(self.config, QueueConfig) else None
        self._config = self._requested_config or injected or QueueConfig()
        container.singleton(QueueConfig, self._config)

        if not self._config.backends:
            logger.info("queue_no_backends_configured")
            # Still register admin components even with no backends
            self._register_admin_components(cast("BootContainerProtocol", container))
        for entry in self._config.backends:
            backend = self._create_backend(entry)
            self._queue_services.append((entry.name, backend))

            # Named bindings — resolvable via Annotated[QueueProtocol, Named(entry.name)]
            container.singleton(
                QueueProtocol,
                factory=lambda *_, b=backend: b,
                name=entry.name,
            )

            # Unnamed bindings for primary backend (backward compat)
            # Primary = entry.primary is True OR (no backend has primary=True and entry is first)
            is_primary = entry.primary or (
                not any(b.primary for b in self._config.backends)
                and self._config.backends[0] is entry
            )
            if is_primary:
                container.singleton(QueueProtocol, factory=lambda *_, b=backend: b)

        logger.info("queue_registered", count=len(self._config.backends))

        # Register admin widget components
        self._register_admin_components(cast("BootContainerProtocol", container))

    def _register_admin_components(self, container: BootContainerProtocol) -> None:
        """Register admin handlers and contributor.

        Args:
            container: The DI container registrar.
        """

        # Check if container supports transient registration (skip for test mocks)
        if not hasattr(container, "transient"):
            return

        # Register handlers as transient — they fetch fresh data each time
        # Factories use async functions to resolve dependencies at runtime
        async def _create_queue_depth_handler() -> QueueDepthWidgetHandler:
            queue = await container.resolve_optional(QueueProtocol)
            return QueueDepthWidgetHandler(queue=queue)

        async def _create_consumer_lag_handler() -> ConsumerLagWidgetHandler:
            queue = await container.resolve_optional(QueueProtocol)
            return ConsumerLagWidgetHandler(queue=queue)

        async def _create_failed_messages_handler() -> FailedMessagesWidgetHandler:
            queue = await container.resolve_optional(QueueProtocol)
            return FailedMessagesWidgetHandler(queue=queue)

        container.transient(
            QueueDepthWidgetHandler,
            _create_queue_depth_handler,
        )
        container.transient(
            ConsumerLagWidgetHandler,
            _create_consumer_lag_handler,
        )
        container.transient(
            FailedMessagesWidgetHandler,
            _create_failed_messages_handler,
        )

        # Shared in-process dead letter queue for failed-message tracking
        container.singleton(DeadLetterQueue, DeadLetterQueue())

        # Register the contributor under AdminContributorProtocol for discovery
        container.singleton(
            QueueAdminContributor,
            QueueAdminContributor,
        )

        logger.debug("Registered queue admin widget components")

    async def boot(self, container: BootContainerProtocol) -> None:
        """Boot phase — connect all queue backends and wire optional tracer.

        Args:
            container: DI container resolver.
        """
        from lexigram.contracts.observability.tracing import TracerProtocol

        tracer = await container.resolve_optional(TracerProtocol)
        hooks = await container.resolve_optional(HookRegistryProtocol)

        for _name, backend in self._queue_services:
            if hasattr(backend, "set_tracer"):
                backend.set_tracer(tracer)
            if hasattr(backend, "set_hook_registry"):
                backend.set_hook_registry(hooks)

        if not self._queue_services:
            return

        results = await asyncio.gather(
            *[
                self._connect_backend(name, backend)
                for name, backend in self._queue_services
            ],
            return_exceptions=True,
        )

        for (name, _), result in zip(self._queue_services, results, strict=False):
            if isinstance(result, Exception):
                logger.warning("queue_boot_unhealthy", backend=name, error=str(result))

        try:
            contributor = await container.resolve(QueueAdminContributor)
            await contributor.on_admin_boot(container)
        except Exception as exc:  # noqa: BLE001
            failure = summarize_contributor_boot_failure(exc)
            if failure.expected:
                logger.info(
                    "admin.contributor_disabled",
                    contributor="queue",
                    feature="admin contributor",
                    reason=failure.reason,
                    missing=failure.summary,
                )
            else:
                logger.warning(
                    "queue_admin_contributor_boot_failed",
                    error=failure.summary,
                    error_type=type(exc).__name__,
                    exc_info=True,
                )

    async def shutdown(self) -> None:
        """Shutdown phase — close all queue backends in reverse order."""
        for name, backend in reversed(self._queue_services):
            try:
                await backend.close()
                logger.info("queue_shutdown", backend=name)
            except Exception as exc:  # noqa: BLE001 — infrastructure cleanup
                logger.warning("queue_shutdown_error", backend=name, error=str(exc))
        self._queue_services.clear()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Aggregate health across all registered queue backends.

        Args:
            timeout: Timeout in seconds.

        Returns:
            HealthCheckResult with aggregated status.
        """
        start = time.perf_counter()

        if not self._queue_services:
            return HealthCheckResult(
                component="queue",
                status=HealthStatus.HEALTHY,
                details={"backends": []},
            )

        results = await asyncio.gather(
            *[
                self._health_check_backend(name, backend, timeout)
                for name, backend in self._queue_services
            ],
            return_exceptions=True,
        )

        worst = HealthStatus.HEALTHY
        details: dict[str, Any] = {}
        for (name, _), result in zip(self._queue_services, results, strict=False):
            if isinstance(result, Exception):
                worst = HealthStatus.UNHEALTHY
                details[name] = {"status": "error", "error": str(result)}
            elif isinstance(result, HealthCheckResult):
                details[name] = {"status": result.status.value}
                if result.status == HealthStatus.UNHEALTHY:
                    worst = HealthStatus.UNHEALTHY
                elif (
                    result.status == HealthStatus.DEGRADED
                    and worst == HealthStatus.HEALTHY
                ):
                    worst = HealthStatus.DEGRADED

        return HealthCheckResult(
            component="queue",
            status=worst,
            details=details,
            duration_ms=(time.perf_counter() - start) * 1000,
        )

    @staticmethod
    async def _connect_backend(_name: str, backend: Any) -> None:
        """Connect a single backend.

        Args:
            _name: Backend name (unused).
            backend: Backend instance.
        """
        await backend.connect()

    @staticmethod
    async def _health_check_backend(
        _name: str, backend: Any, timeout: float = 5.0
    ) -> HealthCheckResult:
        """Health check for a single backend.

        Args:
            _name: Backend name (unused).
            backend: Backend instance.
            timeout: Timeout in seconds.

        Returns:
            HealthCheckResult from backend or error.
        """
        health: HealthCheckResult = await backend.health_check(timeout=timeout)
        return health


__all__ = ["QueueProvider"]
