"""Monitor backend registry for extensible monitoring backends."""

from __future__ import annotations

from typing import Any, Protocol

from lexigram.monitor.backends.opentelemetry import OpenTelemetryBackend
from lexigram.monitor.backends.prometheus import PrometheusBackend
from lexigram.monitor.config import MonitorConfig
from lexigram.observability.core import NoOpMetricsBackend
from lexigram.primitives.registry import BackendRegistry as _CoreBackendRegistry


class MonitorBackendRegistry(Protocol):
    """Protocol for monitor backend factories."""

    def can_create(self, backend_type: Any) -> bool:
        """Check if this factory can create the requested backend type."""
        ...

    def create_backend(self, config: MonitorConfig) -> Any:
        """Create a backend instance with the given configuration."""
        ...


class PrometheusBackendRegistry:
    """Registry for Prometheus monitoring backend."""

    def can_create(self, backend_type: Any) -> bool:
        from lexigram.monitor.config import BackendType

        matched: bool = backend_type == BackendType.PROMETHEUS
        return matched

    def create_backend(self, config: MonitorConfig) -> Any:
        prom_cfg = getattr(config, "prometheus", {}) or {}
        if isinstance(prom_cfg, dict):
            port = prom_cfg.get("port", 8000)
        else:
            port = getattr(prom_cfg, "port", 8000)
        return PrometheusBackend(port=port)


class OpenTelemetryBackendRegistry:
    """Registry for OpenTelemetry monitoring backend."""

    def can_create(self, backend_type: Any) -> bool:
        from lexigram.monitor.config import BackendType

        matched: bool = backend_type == BackendType.OPENTELEMETRY
        return matched

    def create_backend(self, config: MonitorConfig) -> Any:
        otel_cfg = getattr(config, "opentelemetry", {}) or {}
        if isinstance(otel_cfg, dict):
            service_name = otel_cfg.get("service_name", "lexigram-app")
            endpoint = otel_cfg.get("endpoint")
        else:
            service_name = getattr(otel_cfg, "service_name", "lexigram-app")
            endpoint = getattr(otel_cfg, "endpoint", None)
        return OpenTelemetryBackend(service_name, endpoint)


class MemoryBackendRegistry:
    """Registry for Memory (fallback) monitoring backend."""

    def can_create(self, backend_type: Any) -> bool:
        from lexigram.monitor.config import BackendType

        matched: bool = backend_type == BackendType.MEMORY
        return matched

    def create_backend(self, config: MonitorConfig) -> Any:
        return NoOpMetricsBackend()


class MonitorBackendRegistryManager(_CoreBackendRegistry):
    """Central registry for all monitoring backends.

    Extends :class:`lexigram.primitives.registry.BackendRegistry` so that all
    backend registries share a common hierarchy.  Factories are stored
    under ``str(backend_type)`` keys (the ``StrEnum`` value, e.g.
    ``"prometheus"``, ``"opentelemetry"``).
    """

    def __init__(self) -> None:
        """Initialise an empty manager."""
        super().__init__(name="monitor.backends")

    @classmethod
    def with_defaults(cls) -> MonitorBackendRegistryManager:
        """Create a manager pre-populated with all built-in backends.

        Returns:
            A new registry instance with all default backend factories registered.
        """
        instance = cls()
        instance._register_defaults()
        return instance

    def _register_defaults(self) -> None:
        """Populate built-in factories under their backend-type string keys."""
        from lexigram.monitor.config import BackendType

        super().register(str(BackendType.PROMETHEUS), PrometheusBackendRegistry())
        super().register(str(BackendType.OPENTELEMETRY), OpenTelemetryBackendRegistry())
        super().register(str(BackendType.MEMORY), MemoryBackendRegistry())

    def register(  # type: ignore[override]
        self,
        registry: MonitorBackendRegistry | None = None,
        *,
        key: str | None = None,
        value: MonitorBackendRegistry | None = None,
    ) -> None:
        """Register a monitoring backend factory.

        Supports both legacy single-argument form ``register(factory_instance)``
        and new keyword form ``register(key=..., value=factory_instance)``.

        Args:
            registry: Factory instance (legacy one-argument form).
            key: String backend-type key (new form).
            value: Factory instance (new form).
        """
        if key is not None and value is not None:
            super().register(key, value)
            return
        if registry is not None:
            factory = registry
            from lexigram.monitor.config import BackendType

            for bt in BackendType:
                if factory.can_create(bt):
                    super().register(str(bt), factory)
                    return
            raise ValueError(
                f"Cannot infer backend type key from factory {factory!r}; "
                "use register(key=..., value=...) instead."
            )
        raise ValueError(
            "register() requires either registry= or key= + value= arguments."
        )

    def create_backend(self, backend_type: Any, config: MonitorConfig) -> Any:
        """Create a backend instance for *backend_type*.

        Args:
            backend_type: The backend type (string or ``BackendType`` enum value).
            config: Full monitor configuration.

        Returns:
            A monitoring backend instance.

        Raises:
            ValueError: If *backend_type* is not registered.
        """
        factory = self.get(str(backend_type))
        if factory is None:
            raise ValueError(f"Unknown monitoring backend: {backend_type}")
        return factory.create_backend(config)
