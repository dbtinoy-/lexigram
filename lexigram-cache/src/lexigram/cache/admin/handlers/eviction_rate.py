"""Eviction rate widget handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.cache.admin.viewmodels import EvictionRateViewModel
from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.result import Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.infra.cache import CacheBackendProtocol


class EvictionRateWidgetHandler:
    """Fetches cache eviction rate.

    Args:
        cache: Injected CacheBackendProtocol.
    """

    def __init__(self, cache: CacheBackendProtocol) -> None:
        self._cache = cache

    async def get_data(
        self, params: WidgetParams
    ) -> Result[EvictionRateViewModel, AdminError]:
        """Fetch cache eviction stats.

        Args:
            params: Widget parameters.

        Returns:
            Result containing EvictionRateViewModel or AdminError.
        """
        # Try to get metrics from backend, fallback to defaults
        store = getattr(self._cache, "_store", None)

        total_evictions = 0
        if store is not None:
            # MemoryStateStore tracks evictions
            total_evictions = getattr(store, "eviction_count", 0)

        # Compute evictions per second (simplified: assume per 60 second window)
        window_seconds = params.time_window_minutes * 60
        evictions_per_second = (
            total_evictions / window_seconds if window_seconds > 0 else 0.0
        )

        return Ok(
            EvictionRateViewModel(
                evictions_per_second=round(evictions_per_second, 2),
                total_evictions=total_evictions,
            )
        )


__all__ = ["EvictionRateWidgetHandler"]
