"""Factory functions for creating MonitorProvider instances.

Convenience constructors for the most common monitoring backend configurations.
Import through ``lexigram.monitor.di`` — the public API is re-exported there.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.monitor.config import MonitorConfig
    from lexigram.monitor.di.provider import MonitorProvider


def create_opentelemetry_provider(
    service_name: str = "lexigram-app",
    endpoint: str | None = None,
) -> MonitorProvider:
    """Create a MonitorProvider backed by OpenTelemetry.

    Args:
        service_name: Logical service name reported to the OTel collector.
        endpoint: Optional OTLP exporter endpoint URL.

    Returns:
        MonitorProvider configured with :class:`~lexigram.monitor.OpenTelemetryBackend`.
    """
    from lexigram.monitor import OpenTelemetryBackend
    from lexigram.monitor.di.provider import MonitorProvider

    backend = OpenTelemetryBackend(service_name, endpoint)
    return MonitorProvider(backend)


def create_prometheus_provider(port: int = 8000) -> MonitorProvider:
    """Create a MonitorProvider backed by Prometheus.

    Args:
        port: Port on which the Prometheus HTTP metrics endpoint is exposed.

    Returns:
        MonitorProvider configured with :class:`~lexigram.monitor.PrometheusBackend`.
    """
    from lexigram.monitor import PrometheusBackend
    from lexigram.monitor.di.provider import MonitorProvider

    backend = PrometheusBackend(port)
    return MonitorProvider(backend)


def create_provider_from_config(config: MonitorConfig) -> MonitorProvider:
    """Create a MonitorProvider from a ``MonitorConfig`` object or mapping.

    Selects the appropriate monitoring backend and, when available,
    wires an async ``MetricsExporter`` for tasks and background jobs.

    Args:
        config: A ``MonitorConfig`` instance, dict, or compatible mapping.
            A plain ``dict`` is coerced into ``MonitorConfig`` automatically.

    Returns:
        Fully configured MonitorProvider.

    Raises:
        ValueError: When *config* is ``None``.
    """
    from lexigram.monitor.config import BackendType
    from lexigram.monitor.config import MonitorConfig as _MonitorCfg
    from lexigram.monitor.di.provider import MonitorProvider

    if config is None:
        raise ValueError("Monitor provider config is required")

    # Accept mapping/dict or already-constructed pydantic model.
    if not isinstance(config, _MonitorCfg):
        try:
            if isinstance(config, dict):
                config = _MonitorCfg(**config)
            else:
                config = _MonitorCfg.parse_obj(config)
        except (ValueError, TypeError):
            pass

    # Get backend_type robustly (support enum or string values).
    backend_type = getattr(config, "backend_type", None)
    if isinstance(backend_type, str):
        try:
            backend_type = BackendType(backend_type)
        except (ValueError, TypeError):
            backend_type = BackendType.MEMORY

    from lexigram.monitor.backends.registry import MonitorBackendRegistryManager

    registry = MonitorBackendRegistryManager.with_defaults()
    backend = registry.create_backend(backend_type, config)

    exporter = None
    if backend_type == BackendType.PROMETHEUS:
        try:
            from lexigram.monitor.backends.exporters import PrometheusMetricsExporter

            exporter = PrometheusMetricsExporter()
        except (ImportError, RuntimeError, TypeError):
            exporter = None

    return MonitorProvider(backend, exporter, config)


__all__ = [
    "create_opentelemetry_provider",
    "create_prometheus_provider",
    "create_provider_from_config",
]
