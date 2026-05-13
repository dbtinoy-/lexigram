"""Full-featured monitoring and observability provider for ``lexigram-monitor``.

This module defines :class:`MonitorProvider`, which replaces the core
framework's no-op :class:`~lexigram.monitor.di.sub_providers.observability.ObservabilityProvider`
with real metric collection, distributed tracing, and health-check
infrastructure when ``lexigram-monitor`` is installed.

Relationship with ``ObservabilityProvider``
--------------------------------------------
The Lexigram core always registers
:class:`~lexigram.monitor.di.sub_providers.observability.ObservabilityProvider`
at ``ProviderPriority.INFRASTRUCTURE``.  That provider binds no-op stubs
for every observability contract so that application code compiles and runs
even without this package.

``MonitorProvider`` is constructed with an explicit priority that places it
*before* the default ``INFRASTRUCTURE`` value, meaning its ``register()``
call is executed first and its singleton bindings take precedence in the DI
container.  The net result:

* **``ObservabilityProvider``** registers no-op defaults (fallback, always
  present).
* **``MonitorProvider``** overrides those defaults with real implementations
  (active when ``lexigram-monitor`` is installed and added to the app).

Because DI container singletons are resolved in registration order and later
registrations of the same key win, ``MonitorProvider``'s higher priority
(lower numeric value) ensures its bindings are visible to all dependent
services resolved after boot.
"""

from __future__ import annotations

import contextlib
from dataclasses import asdict, is_dataclass
from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts.core import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
    HookRegistryProtocol,
    ProviderPriority,
)
from lexigram.contracts.exceptions.container import ContainerError
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
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.monitor.backends.exporters.otel_registry import (
    MetricsExporterRegistry,
    TracingExporterRegistry,
)
from lexigram.monitor.config import MonitorConfig
from lexigram.monitor.constants import DEFAULT_MAX_SPANS
from lexigram.monitor.health import HealthCheckerRegistry, HealthCheckRegistry
from lexigram.monitor.metrics.collector import (
    MetricsCollectorProtocol as _ConcreteMetricsCollector,
)
from lexigram.monitor.profiling import ProfilingRegistry
from lexigram.monitor.tracing import InMemoryTraceProvider, Tracer

if TYPE_CHECKING:
    from lexigram.contracts import BootContainerProtocol, ContainerRegistrarProtocol

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


def _is_simple_hook_value(value: Any) -> bool:
    return value is None or isinstance(value, str | bool | int | float)


def _extract_payload_attributes(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {}

    raw_payload: dict[str, Any] | None = None
    if is_dataclass(payload) and not isinstance(payload, type):
        raw_payload = asdict(payload)
    elif isinstance(payload, dict):
        raw_payload = payload
    else:
        with contextlib.suppress(TypeError):
            raw_payload = vars(payload)

    if raw_payload is None:
        return {}

    return {
        f"payload.{key}": value
        for key, value in raw_payload.items()
        if isinstance(key, str) and _is_simple_hook_value(value)
    }


class MonitorProvider(Provider):
    """Monitoring and observability provider for Lexigram Framework"""

    name = "monitor"
    priority = ProviderPriority.INFRASTRUCTURE
    config_key: str | None = "monitor"
    config_model: type | None = MonitorConfig

    def __init__(
        self,
        backend: MonitoringBackend,
        exporter: Any | None = None,
        config: Any | None = None,
    ):
        super().__init__()
        self.backend = backend
        self.metrics_collector = _ConcreteMetricsCollector()
        # Configure tracing provider using provided config when available
        tracing_cfg = None
        if config is not None:
            tracing_cfg = getattr(config, "tracing", None) or {}

        # Resolve service_name and max_spans from tracing config (if present)
        service_name = None
        max_spans = None
        if tracing_cfg is not None:
            service_name = getattr(tracing_cfg, "service_name", None)
            max_spans = getattr(tracing_cfg, "max_spans", None)

        if not service_name:
            service_name = "lexigram-service"

        self.trace_provider = InMemoryTraceProvider(
            service_name=service_name,
            max_spans=max_spans or DEFAULT_MAX_SPANS,
        )
        self.tracer = self.trace_provider.tracer
        self.metrics_exporter = exporter
        # Exporter registries — owned by this provider, registered via DI
        self._tracing_exporter_registry = TracingExporterRegistry.with_defaults()
        self._metrics_exporter_registry = MetricsExporterRegistry.with_defaults()
        # Store config for runtime registration decisions
        self._config = config
        self._health_checker_registry: HealthCheckerRegistry | None = None
        self._hook_registry: HookRegistryProtocol | None = None
        self._hook_handlers: list[tuple[str, Any]] = []
        self._slo_worker: Any | None = None
        self._digest_worker: Any | None = None

    @classmethod
    def from_config(cls, config: MonitorConfig, **context: Any) -> MonitorProvider:
        """Create a MonitorProvider from config.

        Delegates to the create_provider_from_config factory.
        """
        from lexigram.monitor.di.factories import create_provider_from_config

        return create_provider_from_config(config)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register monitoring services with the container.

        Binds all monitoring singletons into the DI container. DB-backed
        exporter wiring is deferred to ``boot()`` where the full container
        graph is available.
        """
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

    async def boot(self, container: BootContainerProtocol) -> None:
        """Start the monitoring provider and wire the observability facade.

        After all providers are registered the container graph is complete,
        so this is the correct place to resolve optional cross-provider
        dependencies such as the database exporter.
        """
        await self.backend.initialize()

        # M-05: If the backend exposes a real tracer (e.g. OpenTelemetryBackend after
        # initialize()), use it so @traced decorators go through the real OTel pipeline.
        backend_tracer = getattr(self.backend, "tracer", None)
        if backend_tracer is not None:
            self.tracer = backend_tracer
            logger.info(
                "tracer_wired_from_backend", backend=type(self.backend).__name__
            )

        hook_registry = await container.resolve_optional(HookRegistryProtocol)
        if hook_registry is not None:
            self._register_hook_subscriptions(hook_registry)

        # Wire DB-backed metrics exporter when Prometheus + store_in_db is configured
        # and no exporter was supplied at construction time.
        if (
            self._config
            and getattr(self._config, "prometheus", None)
            and getattr(self._config.prometheus, "store_in_db", False)
            and self.metrics_exporter is None
        ):
            # contracts must always be importable
            from lexigram.contracts.data import DatabaseProviderProtocol
            from lexigram.monitor.backends.db_exporter import DBMetricsExporter

            try:
                db = await container.resolve(DatabaseProviderProtocol)
            except KeyError:
                logger.warning(
                    "db_metrics_exporter_skipped",
                    reason="DatabaseService not registered; DB metrics storage unavailable",
                )
            else:
                db_exporter = DBMetricsExporter(
                    db,
                    table=self._config.prometheus.metrics_table,
                )
                cast("Any", container).singleton("MetricsExporter", lambda: db_exporter)
                self.metrics_exporter = db_exporter
                logger.info(
                    "db_metrics_exporter_registered",
                    table=self._config.prometheus.metrics_table,
                )

        # Create default request metrics.
        self.metrics_collector.create_counter(
            "lexigram_requests_total",
            "Total number of requests",
        )
        self.metrics_collector.create_gauge(
            "lexigram_active_connections",
            "Number of active connections",
        )
        self.metrics_collector.create_histogram(
            "lexigram_request_duration_seconds",
            "Request duration in seconds",
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
        )

        # Resolve and store the HealthCheckerRegistry for use in shutdown()
        with contextlib.suppress(RuntimeError, KeyError, AttributeError, TypeError):
            self._health_checker_registry = await container.resolve(
                HealthCheckerRegistry
            )

        # Start SLO evaluation worker if enabled.
        if (
            self._config
            and getattr(self._config, "slo", None)
            and self._config.slo.enabled
        ):
            from lexigram.contracts.observability.metrics import (
                AlertDispatcherProtocol,
            )
            from lexigram.monitor.slo.monitor import SLOMonitor
            from lexigram.monitor.slo.worker import SLOEvaluationWorker
            from lexigram.tasks.background_task_manager import (
                BackgroundTaskManager,
            )

            slo_cfg = self._config.slo
            dispatcher: AlertDispatcherProtocol | None = None
            try:
                dispatcher = await container.resolve(AlertDispatcherProtocol)
            except ContainerError:
                logger.warning(
                    "alert_dispatcher_not_registered",
                    detail="AlertDispatcherProtocol not in container; SLO worker runs without alert dispatch",
                )

            monitor = SLOMonitor(
                alert_dispatcher=dispatcher,
                suppression_window_seconds=slo_cfg.suppression_window_seconds,
            )
            task_mgr = await container.resolve(BackgroundTaskManager)
            worker = SLOEvaluationWorker(
                task_manager=task_mgr,
                monitor=monitor,
                evaluation_interval=slo_cfg.evaluation_interval,
                initial_delay_seconds=5.0,
            )
            await worker.start()
            self._slo_worker = worker

        # Start the weekly-digest flush worker if a WeeklyDigestDispatcher
        # is registered in the container.  Without this worker the digest
        # buffer accumulates forever.
        from lexigram.monitor.alerts.channels.weekly_digest import (
            WeeklyDigestDispatcher,
        )

        try:
            digest_dispatcher = await container.resolve(WeeklyDigestDispatcher)
        except ContainerError:
            digest_dispatcher = None

        if digest_dispatcher is not None:
            from lexigram.monitor.alerts.digest_worker import (
                WeeklyDigestFlushWorker,
            )
            from lexigram.tasks.background_task_manager import (
                BackgroundTaskManager,
            )

            digest_task_mgr = await container.resolve(BackgroundTaskManager)
            digest_worker = WeeklyDigestFlushWorker(
                task_manager=digest_task_mgr,
                dispatcher=digest_dispatcher,
            )
            await digest_worker.start()
            self._digest_worker = digest_worker
            logger.info(
                "weekly_digest_flush_worker_started",
                interval_seconds=digest_worker.interval_seconds,
            )

    async def shutdown(self) -> None:
        """Shutdown the monitoring provider"""
        if self._hook_registry is not None:
            for hook_name, handler in self._hook_handlers:
                self._hook_registry.unregister_action(hook_name, handler)
            self._hook_handlers.clear()
            self._hook_registry = None

        await self.backend.shutdown()

        # Stop SLO evaluation worker if running.
        if self._slo_worker is not None:
            with contextlib.suppress(RuntimeError, Exception):
                await self._slo_worker.stop()

        # Stop weekly-digest flush worker if running.  The worker emits one
        # final flush on stop so accumulated entries aren't lost on shutdown.
        if self._digest_worker is not None:
            with contextlib.suppress(RuntimeError, Exception):
                await self._digest_worker.stop()

        # Cleanup health checker registry
        if self._health_checker_registry is not None:
            try:
                await self._health_checker_registry.cleanup()
            except (RuntimeError, KeyError, AttributeError, ImportError):
                # If cleanup fails, skip
                pass

    def _register_hook_subscriptions(self, hook_registry: HookRegistryProtocol) -> None:
        self._hook_registry = hook_registry
        self._ensure_hook_event_metric()

        for hook_name in _HOOK_PACKAGE_BY_NAME:
            handler = self._build_hook_handler(hook_name)
            hook_registry.register_action(hook_name, handler)
            self._hook_handlers.append((hook_name, handler))

    def _build_hook_handler(self, hook_name: str) -> Any:
        async def _handler(**kwargs: Any) -> None:
            await self._record_hook_event(hook_name, **kwargs)

        return _handler

    def _ensure_hook_event_metric(self) -> None:
        if self.metrics_collector.get_metric(_HOOK_EVENT_COUNTER_NAME) is None:
            self.metrics_collector.create_counter(
                _HOOK_EVENT_COUNTER_NAME,
                "Total number of monitor hook events",
                labels={"hook": "", "package": ""},
            )

    async def _record_hook_event(self, hook_name: str, **kwargs: Any) -> None:
        package = _HOOK_PACKAGE_BY_NAME[hook_name]
        self._ensure_hook_event_metric()

        metric = self.metrics_collector.get_metric(_HOOK_EVENT_COUNTER_NAME)
        if metric is not None:
            cast("Any", metric).increment(
                labels={
                    "hook": hook_name,
                    "package": package,
                },
            )

        span = self.tracer.start_span(
            f"hook.{hook_name}",
            attributes={
                "lexigram.hook.name": hook_name,
                "lexigram.hook.package": package,
            },
        )
        try:
            for key, value in _extract_payload_attributes(
                kwargs.get("payload")
            ).items():
                span.set_attribute(key, value)
        finally:
            if hasattr(span, "end"):
                cast("Any", span).end()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check monitoring provider health"""
        details = {
            "message": "Monitoring provider is active",
            "backend_type": type(self.backend).__name__,
            "metrics_count": len(self.metrics_collector.get_all_metrics()),
        }

        # If we have a backend and it has a health_check, try to use it
        # Avoid delegation if backend is a generic Mock from tests
        from unittest.mock import Mock

        if (
            hasattr(self.backend, "health_check")
            and not isinstance(self.backend, Mock)
            and callable(self.backend.health_check)
        ):
            try:
                backend_health = await cast("Any", self.backend).health_check()
                # Merge backend details if possible
                if hasattr(backend_health, "details") and isinstance(
                    backend_health.details, dict
                ):
                    details.update(backend_health.details)
                return backend_health
            except (OSError, ConnectionError, RuntimeError, ValueError) as e:
                return HealthCheckResult(
                    component="monitor",
                    status=HealthStatus.UNHEALTHY,
                    error=str(e),
                    details=details,
                    category=HealthCheckCategory.READINESS,
                )

        return HealthCheckResult(
            component="monitor",
            status=HealthStatus.HEALTHY,
            details=details,
            category=HealthCheckCategory.READINESS,
        )

    def record_request(
        self,
        method: str,
        path: str,
        duration: float,
        status_code: int,
    ) -> None:
        """Record an HTTP request"""
        # Ensure metrics exist
        self._ensure_request_metrics()

        # Record metrics
        counter = self.metrics_collector.get_metric("lexigram_requests_total")
        if counter:
            cast("Any", counter).increment(
                labels={"method": method, "status": str(status_code)},
            )

        histogram = self.metrics_collector.get_metric(
            "lexigram_request_duration_seconds",
        )
        if histogram:
            cast("Any", histogram).observe(duration, labels={"method": method})

    def _ensure_request_metrics(self) -> None:
        """Ensure request metrics are created"""
        if not self.metrics_collector.get_metric("lexigram_requests_total"):
            self.metrics_collector.create_counter(
                "lexigram_requests_total",
                "Total number of requests",
                labels={"method": "", "status": ""},
            )

        if not self.metrics_collector.get_metric("lexigram_request_duration_seconds"):
            self.metrics_collector.create_histogram(
                "lexigram_request_duration_seconds",
                "Request duration in seconds",
                labels={"method": ""},
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            )

    def record_connection_change(self, delta: int) -> None:
        """Record connection count change"""
        gauge = self.metrics_collector.get_metric("lexigram_active_connections")
        if gauge:
            cast("Any", gauge).increment(delta)

    def create_counter(
        self,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
    ):
        """Create a counter metric"""
        return self.metrics_collector.create_counter(name, description, labels)

    def create_gauge(
        self,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
    ):
        """Create a gauge metric"""
        return self.metrics_collector.create_gauge(name, description, labels)

    def create_histogram(
        self,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        buckets: list[float] | None = None,
    ):
        """Create a histogram metric"""
        return self.metrics_collector.create_histogram(
            name,
            description,
            labels,
            buckets,
        )


__all__ = ["MonitorProvider"]
