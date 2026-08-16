"""Monitoring and observability module for dependency injection."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.observability.metrics import (
    HealthCheckRegistryProtocol,
    MetricsFactoryProtocol,
    MetricsRecorderProtocol,
)
from lexigram.contracts.observability.metrics import (
    MetricsCollectorProtocol as MetricsCollectorProtocol,
)
from lexigram.contracts.observability.tracing import TracerProtocol
from lexigram.di.module import DynamicModule, Module, module


@module()
class MonitorModule(Module):
    """Metrics collection, distributed tracing, health checks, and profiling.

    Call :meth:`configure` to configure the monitoring subsystem.

    Usage (no-op / development)::

        from lexigram.monitor.backends.noop import NoopMetricsBackend

        @module(
            imports=[MonitorModule.configure(backend=NoopMetricsBackend())]
        )
        class AppModule(Module):
            pass

    Usage (Prometheus)::

        from lexigram.monitor.backends.exporters.prometheus import PrometheusMetricsExporter
        from lexigram.monitor.backends.prometheus import PrometheusBackend

        @module(
            imports=[MonitorModule.configure(backend=PrometheusBackend())]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(cls, backend: Any = None, config: Any | None = None) -> DynamicModule:
        """Create a MonitorModule with explicit configuration.

        Args:
            backend: ``MetricsBackendProtocol`` implementation.
                Defaults to ``NoOpMetricsBackend`` when omitted.
            config: ``MonitorConfig`` for advanced tracing and profiling settings.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.monitor.di.provider import MonitorProvider
        from lexigram.monitor.health import HealthCheckerRegistry, HealthCheckRegistry
        from lexigram.monitor.services.core import ObservabilityService
        from lexigram.observability.core import NoOpMetricsBackend

        if backend is None:
            backend = NoOpMetricsBackend()

        return DynamicModule(
            module=cls,
            providers=[MonitorProvider(backend=backend, config=config)],
            exports=[
                MetricsCollectorProtocol,
                MetricsRecorderProtocol,
                MetricsFactoryProtocol,
                TracerProtocol,
                HealthCheckRegistryProtocol,
                HealthCheckerRegistry,
                HealthCheckRegistry,
                ObservabilityService,
            ],
        )

    @classmethod
    def with_slo(cls, backend: Any = None, config: Any | None = None) -> DynamicModule:
        """Return a MonitorModule that also exports SLO types.

        Args:
            backend: ``MetricsBackendProtocol`` implementation.
            config: ``MonitorConfig`` for advanced settings.
        """
        from lexigram.monitor.di.provider import MonitorProvider
        from lexigram.monitor.health import HealthCheckerRegistry, HealthCheckRegistry
        from lexigram.monitor.services.core import ObservabilityService
        from lexigram.monitor.slo.monitor import SLOMonitor
        from lexigram.monitor.slo.worker import SLOEvaluationWorker
        from lexigram.observability.core import NoOpMetricsBackend

        if backend is None:
            backend = NoOpMetricsBackend()

        return DynamicModule(
            module=cls,
            providers=[MonitorProvider(backend=backend, config=config)],
            exports=[
                MetricsCollectorProtocol,
                MetricsRecorderProtocol,
                MetricsFactoryProtocol,
                TracerProtocol,
                HealthCheckRegistryProtocol,
                HealthCheckerRegistry,
                HealthCheckRegistry,
                ObservabilityService,
                SLOMonitor,
                SLOEvaluationWorker,
            ],
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Return a no-op MonitorModule for unit testing.

        Registers a :class:`~lexigram.monitor.noop.NoOpMetricsBackend`
        that discards all metrics. No external telemetry systems are
        connected.

        Args:
            config: Optional test configuration override.

        Returns:
            A DynamicModule with noop metrics and tracing.
        """
        from lexigram.monitor.di.provider import MonitorProvider
        from lexigram.monitor.health import HealthCheckerRegistry, HealthCheckRegistry
        from lexigram.monitor.services.core import ObservabilityService
        from lexigram.observability.core import NoOpMetricsBackend

        return DynamicModule(
            module=cls,
            providers=[MonitorProvider(backend=NoOpMetricsBackend())],
            exports=[
                MetricsCollectorProtocol,
                MetricsRecorderProtocol,
                MetricsFactoryProtocol,
                TracerProtocol,
                HealthCheckRegistryProtocol,
                HealthCheckerRegistry,
                HealthCheckRegistry,
                ObservabilityService,
            ],
        )


__all__ = ["MonitorModule"]
