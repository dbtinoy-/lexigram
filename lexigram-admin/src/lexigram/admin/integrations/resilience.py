"""Resilience integration — wraps data-source calls with retry/circuit-breaker."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


@dataclass(frozen=True)
class ResilientSpec:
    """Specification for resilient data-source calls.

    Attributes:
        max_retries: Max retry attempts on transient failure.
        circuit_breaker: Whether to enable circuit breaker.
        timeout_seconds: Per-call timeout.
    """

    max_retries: int = 3
    circuit_breaker: bool = True
    timeout_seconds: float = 30.0


class _NoOpResilience:
    async def execute(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        return await func(*args, **kwargs)


class ResilienceIntegration:
    """Adapter that decorates data-source calls with retry and circuit-breaker.

    Gracefully no-ops when ``lexigram-resilience`` is not installed or the
    integration is disabled.
    """

    def __init__(self, config: Any) -> None:
        self._config = config
        self._pipeline: Any = None
        self._enabled = False

    def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.admin.config import ResilienceIntegrationConfig
        from lexigram.admin.integrations._optional import is_installed

        cfg = self._config
        if not isinstance(cfg, ResilienceIntegrationConfig):
            cfg = ResilienceIntegrationConfig()
        if not cfg.enabled:
            self._pipeline = _NoOpResilience()
            return
        if not is_installed("lexigram.resilience"):
            self._pipeline = _NoOpResilience()
            return
        self._enabled = True

    async def boot(self, container: ContainerResolverProtocol) -> None:
        if not self._enabled:
            return
        try:
            from lexigram.contracts.infra.resilience import (
                ResiliencePipelineFactoryProtocol,
            )

            self._pipeline = await container.resolve(ResiliencePipelineFactoryProtocol)
        except Exception:  # noqa: BLE001
            self._pipeline = _NoOpResilience()

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy"
            if not isinstance(self._pipeline, _NoOpResilience)
            else "noop"
        }

    async def execute(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        if hasattr(self._pipeline, "execute"):
            return await self._pipeline.execute(func, *args, **kwargs)
        return await func(*args, **kwargs)


__all__ = ["ResilienceIntegration", "ResilientSpec"]
