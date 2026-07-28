"""Backend ping widget handler."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from lexigram.cache.admin.viewmodels import BackendPingViewModel
from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.result import Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.infra.cache import CacheBackendProtocol


class BackendPingWidgetHandler:
    """Pings the cache backend.

    Args:
        cache: Injected CacheBackendProtocol.
    """

    def __init__(self, cache: CacheBackendProtocol) -> None:
        self._cache = cache

    async def get_data(
        self, params: WidgetParams
    ) -> Result[BackendPingViewModel, AdminError]:
        """Perform a health check on the cache backend.

        Infrastructure failures (network, timeout) propagate as exceptions.

        Args:
            params: Widget parameters.

        Returns:
            Result containing BackendPingViewModel or AdminError.
        """
        start = time.monotonic()

        # Call health_check if available — infrastructure exceptions propagate
        is_reachable = True
        health_check_method = getattr(self._cache, "health_check", None)
        if health_check_method is not None and callable(health_check_method):
            result = await health_check_method()
            # HealthCheckResult has an is_healthy property or status
            is_reachable = getattr(result, "is_healthy", True)

        latency_ms = round((time.monotonic() - start) * 1000, 2)
        backend_name = getattr(self._cache, "backend_name", "cache")
        if not isinstance(backend_name, str):
            backend_name = type(self._cache).__name__

        return Ok(
            BackendPingViewModel(
                latency_ms=latency_ms,
                is_reachable=bool(is_reachable),
                backend_name=backend_name,
            )
        )


__all__ = ["BackendPingWidgetHandler"]
