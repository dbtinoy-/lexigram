"""Monitor integration — emits metrics and OTel spans for admin operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class _NoOpMonitor:
    def increment(
        self, name: str, value: int = 1, tags: dict[str, str] | None = None
    ) -> None:
        pass

    def gauge(
        self, name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        pass

    def histogram(
        self, name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        pass


class MonitorIntegration:
    """Adapter that emits admin metrics and spans via lexigram-monitor.

    Gracefully no-ops when ``lexigram-monitor`` is not installed or the
    integration is disabled.
    """

    def __init__(self, config: Any) -> None:
        self._config = config
        # Keep metric calls and health checks safe before the DI lifecycle
        # resolves the optional recorder.
        self._recorder: Any = _NoOpMonitor()
        self._enabled = False

    def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.admin.config import MonitorIntegrationConfig
        from lexigram.admin.integrations._optional import is_installed

        cfg = self._config
        if not isinstance(cfg, MonitorIntegrationConfig):
            cfg = MonitorIntegrationConfig()
        if not cfg.enabled:
            self._recorder = _NoOpMonitor()
            return
        if not is_installed("lexigram.monitor"):
            self._recorder = _NoOpMonitor()
            return
        self._enabled = True

    async def boot(self, container: ContainerResolverProtocol) -> None:
        if not self._enabled:
            return
        try:
            from lexigram.contracts.observability.metrics import MetricsRecorderProtocol

            self._recorder = await container.resolve(MetricsRecorderProtocol)
        except Exception:  # noqa: BLE001
            self._recorder = _NoOpMonitor()

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy"
            if not isinstance(self._recorder, _NoOpMonitor)
            else "noop"
        }

    def increment(
        self, name: str, value: int = 1, tags: dict[str, str] | None = None
    ) -> None:
        if self._recorder:
            self._recorder.increment(name, value, tags)

    def gauge(
        self, name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        if self._recorder:
            self._recorder.gauge(name, value, tags)

    def histogram(
        self, name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        if self._recorder:
            self._recorder.histogram(name, value, tags)


__all__ = ["MonitorIntegration"]
