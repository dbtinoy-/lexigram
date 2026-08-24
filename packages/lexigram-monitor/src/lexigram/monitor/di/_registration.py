"""Registration-phase methods."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.observability.metrics import (
    MetricsBackendProtocol as MonitoringBackend,
)
from lexigram.contracts.observability.metrics import (
    MetricsCollectorProtocol as MetricsCollectorProtocol,
)
from lexigram.contracts.observability.metrics import (
    MetricsFactoryProtocol,
    MetricsRecorderProtocol,
)
from lexigram.contracts.observability.tracing import (
    TracerProtocol as TracerProtocol,
)
from lexigram.logging import get_logger
from lexigram.monitor.backends.exporters.otel_registry import (
    MetricsExporterRegistry,
    TracingExporterRegistry,
)
from lexigram.monitor.di._attrs import _MonitorAttrsMixin
from lexigram.monitor.health import HealthCheckerRegistry, HealthCheckRegistry
from lexigram.monitor.metrics.collector import (
    MetricsCollectorProtocol as _ConcreteMetricsCollector,
)
from lexigram.monitor.profiling import ProfilingRegistry
from lexigram.monitor.tracing import Tracer

if TYPE_CHECKING:
    from lexigram.contracts import ContainerRegistrarProtocol

logger = get_logger(__name__)

_HOOK_PACKAGE_BY_NAME = {
    "cache.hit": "cache",
    "cache.miss": "cache",
    "cache.evicted": "cache",
    "event.published": "events",
    "event.handled": "events",
    "connection.acquired": "sql",
    "transaction.begin": "sql",
    "transaction.end": "sql",
    "request.received": "web",
    "response.prepared": "web",
    "server.started": "web",
    "server.stopped": "web",
    "auth.login": "auth",
    "auth.logout": "auth",
    "token.refreshed": "auth",
    "message.published": "queue",
    "message.consumed": "queue",
    "task.queued": "tasks",
    "task.completed": "tasks",
    "task.failed": "tasks",
}
_HOOK_EVENT_COUNTER_NAME = "lexigram_hook_events_total"


class _MonitorRegistrationMixin(_MonitorAttrsMixin):
    """See :class:`MonitorProvider`."""

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register monitoring services with the container.

        Binds all monitoring singletons into the DI container. DB-backed
        exporter wiring is deferred to ``boot()`` where the full container
        graph is available.
        """
        from lexigram.monitor.di.provider import (
            MonitorProvider,  # noqa: PLC0415 — breaks provider<->mixin cycle
        )

        container.singleton(MonitorProvider, lambda: self)
        container.singleton(MetricsCollectorProtocol, lambda: self.metrics_collector)
        container.singleton(_ConcreteMetricsCollector, lambda: self.metrics_collector)
        container.singleton(MetricsRecorderProtocol, lambda: self.metrics_collector)
        container.singleton(MetricsFactoryProtocol, lambda: self.metrics_collector)
        container.singleton(
            TracingExporterRegistry, lambda: self._tracing_exporter_registry
        )
        container.singleton(
            MetricsExporterRegistry, lambda: self._metrics_exporter_registry
        )
        container.singleton(TracerProtocol, lambda: self.tracer)
        container.singleton(Tracer, lambda: self.tracer)
        container.singleton(MonitoringBackend, lambda: self.backend)

        # Register ObservabilityService so @traced/@metered decorators resolve
        # the real tracer and metrics collector through the container.
        from lexigram.monitor.services.core import ObservabilityService

        container.singleton(
            ObservabilityService,
            lambda: ObservabilityService(
                tracer=self.tracer,
                meter=self.metrics_collector,
            ),
        )

        # Register health infrastructure singletons.
        from lexigram.contracts.observability.metrics import HealthCheckRegistryProtocol

        container.singleton(HealthCheckRegistry, HealthCheckRegistry)
        container.singleton("HealthCheckRegistry", HealthCheckRegistry)
        container.singleton(HealthCheckRegistryProtocol, HealthCheckRegistry)

        container.singleton(HealthCheckerRegistry, HealthCheckerRegistry())
        container.singleton(ProfilingRegistry, ProfilingRegistry())

        await self._discover_backends(container)

        await self._discover_backends(container)

        # Register optional metrics exporter provided at construction time.
        if self.metrics_exporter is not None:
            container.singleton("MetricsExporter", lambda: self.metrics_exporter)

            # If it is a PrometheusMetricsExporter, also expose the ASGI
            # /metrics endpoint so web layers can mount it without importing
            # lexigram-monitor directly.
            from lexigram.monitor.backends.exporters.prometheus import (
                HAS_PROMETHEUS,
                PrometheusMetricsExporter,
            )

            if HAS_PROMETHEUS and isinstance(
                self.metrics_exporter, PrometheusMetricsExporter
            ):
                _exporter_ref = self.metrics_exporter
                container.singleton(
                    "prometheus_metrics_app",
                    lambda: _exporter_ref.metrics_app,
                )

    async def _discover_backends(self, container: ContainerRegistrarProtocol) -> None:
        """Scan the ``lexigram.monitoring.backends`` entry-point group.

        Any entry point that resolves to a
        :class:`~lexigram.di.provider.Provider` subclass is instantiated
        and its :meth:`~lexigram.di.provider.Provider.register` method is
        called, allowing third-party monitoring backend packages to
        self-register.

        Args:
            container: The DI container registrar.
        """
        import importlib.metadata as _meta

        from lexigram.di.provider import Provider as _Provider

        eps = _meta.entry_points(group="lexigram.monitoring.backends")
        for ep in eps:
            try:
                candidate = ep.load()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "monitor_ep_load_failed",
                    entry_point=ep.name,
                    error=str(exc),
                )
                continue
            if not (isinstance(candidate, type) and issubclass(candidate, _Provider)):
                logger.debug(
                    "monitor_ep_skipped",
                    entry_point=ep.name,
                    reason="not a Provider subclass",
                )
                continue
            logger.debug(
                "monitor_ep_found",
                entry_point=ep.name,
                provider=candidate.__name__,
            )
            try:
                await candidate().register(container)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "monitor_ep_register_failed",
                    entry_point=ep.name,
                    provider=candidate.__name__,
                    error=str(exc),
                )
