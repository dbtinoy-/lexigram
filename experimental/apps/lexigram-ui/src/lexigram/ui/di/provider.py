"""UIProvider — registers the UI component system in the DI container."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.di.provider import Provider
from lexigram.ui.config import (
    BaseLayoutConfig,
    FooterConfig,
    HeadConfig,
    HTMLDocumentConfig,
    ToastConfig,
    UIConfig,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class UIProvider(Provider):
    """Registers the lexigram-ui component system.

    Bind into your application bootstrap::

        from lexigram.ui.di import UIProvider

        app.add_provider(UIProvider())

    Configuration (``application.yaml``)::

        ui:
          default_theme: my-theme
          debug_components: true

    Registered services:

    - ``UIConfig`` (singleton) — resolved UI configuration.
    - ``MetricsCollector`` (singleton) — in-memory UI metrics collection.
    - ``ResponseOptimizer`` (singleton) — ETag-based HTMX response optimization.
    - ``RenderCache`` (singleton) — LRU cache for rendered component fragments.
    """

    name = "ui"
    priority = ProviderPriority.PRESENTATION
    config_key: str | None = "ui"
    config_model: type | None = UIConfig

    def __init__(self, config: UIConfig | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._requested_config = config
        if config is not None:
            self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register UI services in the DI container.

        Args:
            container: The DI container registrar.
        """
        self._config = self._requested_config or (
            self.config
            if isinstance(getattr(self, "config", None), UIConfig)
            else self._config
        )
        config: UIConfig = (
            self._config if isinstance(self._config, UIConfig) else UIConfig()
        )
        container.singleton(UIConfig, config)

        # Layout config singletons
        container.singleton(HTMLDocumentConfig, HTMLDocumentConfig())
        container.singleton(BaseLayoutConfig, BaseLayoutConfig())
        container.singleton(HeadConfig, HeadConfig())
        container.singleton(FooterConfig, FooterConfig())
        container.singleton(ToastConfig, ToastConfig())

        # Monitoring services — explicitly registered for DI traceability
        from lexigram.ui.performance.observability import MetricsCollector
        from lexigram.ui.performance.performance import RenderCache, ResponseOptimizer

        container.singleton(MetricsCollector, MetricsCollector)
        container.singleton(ResponseOptimizer, ResponseOptimizer)
        container.singleton(RenderCache, RenderCache)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No boot-time initialisation required for the UI module."""

    async def shutdown(self) -> None:
        """No shutdown work required for the UI module."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check provider health.

        Args:
            timeout: Maximum seconds to wait for health check response.

        Returns:
            HealthCheckResult with status and component details.
        """
        start = time.perf_counter()
        return HealthCheckResult(
            component="ui",
            status=HealthStatus.HEALTHY,
            details={"components": {"ui": {"status": "healthy"}}},
            duration_ms=(time.perf_counter() - start) * 1000,
        )


__all__ = ["UIProvider"]
