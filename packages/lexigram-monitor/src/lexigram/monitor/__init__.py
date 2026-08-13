"""Lexigram Monitor Package - Observability and monitoring"""

from __future__ import annotations

import importlib.metadata

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from typing import TYPE_CHECKING, Any

from lexigram.monitor.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.contracts.observability.metrics import (
        AlertDispatcherProtocol,
        MetricProtocol,
        MetricsBackendProtocol,
    )
    from lexigram.contracts.observability.tracing import TracerProtocol
    from lexigram.contracts.observability.tracing import (
        TracerProtocol as TraceProvider,
    )
    from lexigram.logging import (
        Logger,
        configure_logging,
        get_logger,
    )
    from lexigram.monitor.alerts import LoggingAlertDispatcher
    from lexigram.monitor.backends import (
        OpenTelemetryBackend,
        PrometheusBackend,
    )
    from lexigram.monitor.backends.exporters import PrometheusMetricsExporter
    from lexigram.monitor.backends.exporters.otel_registry import (
        ConsoleMetricsExporterHandler,
        ConsoleTracingExporterHandler,
        MetricsExporterRegistry,
        OTLPMetricsExporterHandler,
        OTLPTracingExporterHandler,
        TracingExporterRegistry,
    )
    from lexigram.monitor.config import (
        BackendType,
        ErrorTrackingConfig,
        HealthCheckConfig,
        LoggingConfig,
        MetricsConfig,
        MonitorConfig,
        OpenTelemetryConfig,
        PrometheusConfig,
        SamplerType,
        TracingConfig,
    )
    from lexigram.monitor.decorators import monitor
    from lexigram.monitor.di.factories import (
        create_opentelemetry_provider,
        create_prometheus_provider,
        create_provider_from_config,
    )
    from lexigram.monitor.di.provider import (
        MonitorProvider,
    )
    from lexigram.monitor.di.sub_providers.observability import ObservabilityProvider
    from lexigram.monitor.error_tracking import (
        ErrorTrackerProtocol,
        NullErrorTracker,
        SentryErrorTracker,
        setup_error_tracking,
    )
    from lexigram.monitor.exceptions import (
        BackendNotAvailableError,
        InvalidMetricError,
        MetricNotFoundError,
        MonitorError,
        SpanError,
    )
    from lexigram.monitor.health import (
        FunctionHealthCheck,
        HealthCheck,
        HealthCheckCategory,
        HealthChecker,
        HealthCheckerRegistry,
        HealthCheckRegistry,
        HealthCheckResult,
        HealthStatus,
        health_checker,
    )
    from lexigram.monitor.instrumentation.database import instrument_database
    from lexigram.monitor.instrumentation.decorators import (
        metered,
        traced,
    )
    from lexigram.monitor.instrumentation.http import OTelMiddleware
    from lexigram.monitor.instrumentation.messaging import (
        inject_trace_context,
        trace_consume,
        trace_publish,
    )
    from lexigram.monitor.metrics import (
        BufferedMetricEntry,
        BufferedMetricRecorder,
        Counter,
        Gauge,
        Histogram,
        MetricsCollectorProtocol,
        Summary,
    )
    from lexigram.monitor.middleware import (
        HealthCheckProvider,
        PrometheusMiddleware,
    )
    from lexigram.monitor.profiling import (
        FunctionProfileResult,
        PerformanceMetrics,
        PerformanceMonitor,
        PerformanceMonitorConfig,
        PerformanceMonitorError,
        PerformanceMonitorState,
        PerformanceSnapshot,
        get_performance_summary,
        monitor_async_operation,
        profile_async_function,
    )
    from lexigram.monitor.services.core import (
        MetricProxy,
        ObservabilityService,
    )
    from lexigram.monitor.slo.monitor import SLOMonitor
    from lexigram.monitor.slo.objective import (
        SLO,
        SLOViolation,
    )
    from lexigram.monitor.tracing import (
        ConsoleSpanExporter,
        InMemoryTraceProvider,
        Span,
        SpanContext,
        SpanExporter,
        SpanKind,
        SpanStatus,
        Tracer,
    )
    from lexigram.monitor.types import HealthCheckerProtocol, MetricValue
    from lexigram.observability.core import (
        NoOpHealthCheckRegistry,
        NoOpMetricsCollector,
        NoOpSpan,
        NoOpTracer,
    )


_LAZY_IMPORTS = {
    # Module
    "MonitorModule": "lexigram.monitor.module",
    # Config
    "BackendType": "lexigram.monitor.config",
    "SamplerType": "lexigram.monitor.config",
    "MetricsConfig": "lexigram.monitor.config",
    "TracingConfig": "lexigram.monitor.config",
    "HealthCheckConfig": "lexigram.monitor.config",
    "LoggingConfig": "lexigram.monitor.config",
    "OpenTelemetryConfig": "lexigram.monitor.config",
    "PrometheusConfig": "lexigram.monitor.config",
    "MonitorConfig": "lexigram.monitor.config",
    "ErrorTrackingConfig": "lexigram.monitor.config",
    # Error tracking
    "ErrorTrackerProtocol": "lexigram.monitor.error_tracking",
    "NullErrorTracker": "lexigram.monitor.error_tracking",
    "SentryErrorTracker": "lexigram.monitor.error_tracking",
    "setup_error_tracking": "lexigram.monitor.error_tracking",
    # Protocols
    "MetricProtocol": "lexigram.contracts.observability",
    "TraceProvider": "lexigram.contracts.observability",
    "MetricsBackendProtocol": "lexigram.contracts.observability",
    "AlertDispatcherProtocol": "lexigram.contracts.observability",
    # Types
    "MetricValue": "lexigram.monitor.types",
    "HealthCheckerProtocol": "lexigram.monitor.types",
    "SpanKind": "lexigram.monitor.tracing",
    "SpanStatus": "lexigram.monitor.tracing",
    # Exceptions
    "MonitorError": "lexigram.monitor.exceptions",
    "BackendNotAvailableError": "lexigram.monitor.exceptions",
    "MetricNotFoundError": "lexigram.monitor.exceptions",
    "InvalidMetricError": "lexigram.monitor.exceptions",
    "SpanError": "lexigram.monitor.exceptions",
    # Metrics
    "MetricsCollectorProtocol": "lexigram.monitor.metrics",
    "Counter": "lexigram.monitor.metrics",
    "Gauge": "lexigram.monitor.metrics",
    "Histogram": "lexigram.monitor.metrics",
    "Summary": "lexigram.monitor.metrics",
    "BufferedMetricEntry": "lexigram.monitor.metrics",
    "BufferedMetricRecorder": "lexigram.monitor.metrics",
    # Tracing
    "Tracer": "lexigram.monitor.tracing",
    "Span": "lexigram.monitor.tracing",
    "SpanContext": "lexigram.monitor.tracing",
    "SpanExporter": "lexigram.monitor.tracing",
    "ConsoleSpanExporter": "lexigram.monitor.tracing",
    "InMemoryTraceProvider": "lexigram.monitor.tracing",
    # Logging
    "Logger": "lexigram.logging",
    "get_logger": "lexigram.logging",
    "configure_logging": "lexigram.logging",
    # Backends
    "OpenTelemetryBackend": "lexigram.monitor.backends",
    "PrometheusBackend": "lexigram.monitor.backends",
    # Middleware
    "PrometheusMiddleware": "lexigram.monitor.middleware",
    "HealthCheckProvider": "lexigram.monitor.middleware",
    # Health
    "HealthStatus": "lexigram.monitor.health",
    "HealthCheck": "lexigram.monitor.health",
    "HealthCheckCategory": "lexigram.monitor.health",
    "HealthCheckResult": "lexigram.monitor.health",
    "HealthCheckRegistry": "lexigram.monitor.health",
    "HealthChecker": "lexigram.monitor.health",
    "HealthCheckerRegistry": "lexigram.monitor.health",
    "FunctionHealthCheck": "lexigram.monitor.health",
    "health_checker": "lexigram.monitor.health",
    # NoOp stubs
    "NoOpSpan": "lexigram.observability.core",
    "NoOpTracer": "lexigram.observability.core",
    "NoOpMetricsCollector": "lexigram.observability.core",
    "NoOpHealthCheckRegistry": "lexigram.observability.core",
    # Observability service
    "ObservabilityService": "lexigram.monitor.services.core",
    "MetricProxy": "lexigram.monitor.services.core",
    # Decorators
    "metered": "lexigram.monitor.instrumentation.decorators",
    "traced": "lexigram.monitor.instrumentation.decorators",
    "monitor": "lexigram.monitor.decorators",
    # Provider
    "ObservabilityProvider": "lexigram.monitor.di.sub_providers.observability",
    "MonitorProvider": "lexigram.monitor.di.provider",
    "create_opentelemetry_provider": "lexigram.monitor.di.provider",
    "create_prometheus_provider": "lexigram.monitor.di.provider",
    "create_provider_from_config": "lexigram.monitor.di.provider",
    "PrometheusMetricsExporter": "lexigram.monitor.backends.exporters",
    "ConsoleTracingExporterHandler": "lexigram.monitor.backends.exporters.otel_registry",
    "OTLPTracingExporterHandler": "lexigram.monitor.backends.exporters.otel_registry",
    "ConsoleMetricsExporterHandler": "lexigram.monitor.backends.exporters.otel_registry",
    "OTLPMetricsExporterHandler": "lexigram.monitor.backends.exporters.otel_registry",
    "TracingExporterRegistry": "lexigram.monitor.backends.exporters.otel_registry",
    "MetricsExporterRegistry": "lexigram.monitor.backends.exporters.otel_registry",
    # Instrumentation
    "instrument_database": "lexigram.monitor.instrumentation.database",
    "OTelMiddleware": "lexigram.monitor.instrumentation.http",
    "trace_publish": "lexigram.monitor.instrumentation.messaging",
    "trace_consume": "lexigram.monitor.instrumentation.messaging",
    "inject_trace_context": "lexigram.monitor.instrumentation.messaging",
    # Profiling
    "PerformanceMonitor": "lexigram.monitor.profiling",
    "PerformanceMonitorConfig": "lexigram.monitor.profiling",
    "PerformanceMonitorError": "lexigram.monitor.profiling",
    "PerformanceMonitorState": "lexigram.monitor.profiling",
    "PerformanceMetrics": "lexigram.monitor.profiling",
    "PerformanceSnapshot": "lexigram.monitor.profiling",
    "FunctionProfileResult": "lexigram.monitor.profiling",
    "get_performance_summary": "lexigram.monitor.profiling",
    "monitor_async_operation": "lexigram.monitor.profiling",
    "profile_async_function": "lexigram.monitor.profiling",
    # SLO
    "SLO": "lexigram.monitor.slo.objective",
    "SLOViolation": "lexigram.monitor.slo.objective",
    "SLOMonitor": "lexigram.monitor.slo.monitor",
    # Alerts
    "LoggingAlertDispatcher": "lexigram.monitor.alerts",
    # Hooks
    "AlertFiredHook": "lexigram.monitor.hooks",
    "HealthCheckRunHook": "lexigram.monitor.hooks",
    "MetricRecordedHook": "lexigram.monitor.hooks",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module_path = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__} has no attribute {name}")


def __dir__() -> list[str]:
    return [*list(_LAZY_IMPORTS.keys()), "__version__"]


__all__ = list(_LAZY_IMPORTS.keys())
