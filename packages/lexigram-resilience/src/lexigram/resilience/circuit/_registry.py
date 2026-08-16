"""Circuit breaker registry for managing named circuit breakers."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.models import CircuitBreakerConfig
    from lexigram.contracts.observability.metrics import MetricsRecorderProtocol
    from lexigram.resilience.circuit._metrics import CircuitBreakerMetrics
    from lexigram.resilience.circuit.breaker import CircuitBreaker


class CircuitBreakerRegistry:
    """Registry for managing named circuit breakers."""

    def __init__(self) -> None:
        """Initialize the circuit breaker registry.

        Creates an empty registry for managing named circuit breakers.
        """
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
        self._metrics_collector: MetricsRecorderProtocol | None = None
        self._backend: Any | None = None

    def set_metrics_collector(self, collector: MetricsRecorderProtocol) -> None:
        """Set metrics collector for all breakers in registry."""
        self._metrics_collector = collector
        for breaker in self._breakers.values():
            breaker._metrics_collector = collector

    def set_backend(self, backend: Any) -> None:
        """Set distributed state backend for all current and future breakers.

        Args:
            backend: A :class:`CircuitBreakerBackend` implementation enabling
                distributed state sharing across processes.
        """
        self._backend = backend
        for breaker in self._breakers.values():
            breaker._backend = backend

    def get(self, name: str) -> CircuitBreaker | None:
        """Get circuit breaker by name."""
        return self._breakers.get(name)

    async def get_or_create(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        """Get or create a named circuit breaker."""
        from lexigram.contracts.infra.resilience.models import (
            CircuitBreakerConfig as _Config,
        )
        from lexigram.resilience.circuit.breaker import CircuitBreaker

        async with self._lock:
            if name not in self._breakers:
                cfg = config or _Config(name=name)
                self._breakers[name] = CircuitBreaker(
                    config=cfg,
                    metrics_collector=self._metrics_collector,
                    backend=self._backend,
                )
            return self._breakers[name]

    def reset_breaker(self, name: str) -> None:
        """Reset a named circuit breaker to closed state."""
        if name in self._breakers:
            self._breakers[name].reset()

    def force_open_breaker(self, name: str) -> None:
        """Force a named circuit breaker to open state."""
        if name in self._breakers:
            self._breakers[name].force_open()

    def get_breaker_metrics(self, name: str) -> CircuitBreakerMetrics | None:
        """Get metrics for a named circuit breaker."""
        breaker = self._breakers.get(name)
        return breaker.metrics if breaker else None

    def list_breakers(self) -> dict[str, dict[str, Any]]:
        """List all circuit breakers with their state and metrics."""
        return {
            name: {
                "state": breaker.state.value,
                "metrics": {
                    "total_calls": breaker.metrics.total_calls,
                    "successful_calls": breaker.metrics.successful_calls,
                    "failed_calls": breaker.metrics.failed_calls,
                    "consecutive_failures": breaker.metrics.consecutive_failures,
                    "consecutive_successes": breaker.metrics.consecutive_successes,
                },
            }
            for name, breaker in self._breakers.items()
        }

    def cleanup(self) -> None:
        """Clean up all circuit breakers."""
        self._breakers.clear()


__all__ = ["CircuitBreakerRegistry"]
