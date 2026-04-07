"""Hit/miss ratio widget handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.cache.admin.viewmodels import HitMissRatioViewModel
from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.result import Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.infra.cache import CacheBackendProtocol


class HitMissRatioWidgetHandler:
    """Fetches cache hit/miss ratio.

    Args:
        cache: Injected CacheBackendProtocol.
    """

    def __init__(self, cache: CacheBackendProtocol) -> None:
        self._cache = cache

    async def get_data(
        self, params: WidgetParams
    ) -> Result[HitMissRatioViewModel, AdminError]:
        """Fetch cache hit/miss stats.

        Infrastructure failures propagate.

        Args:
            params: Widget parameters.

        Returns:
            Result containing HitMissRatioViewModel or AdminError.
        """
        # Try to get stats via public method if available
        hits = 0
        misses = 0
        if hasattr(self._cache, "get_stats") and callable(self._cache.get_stats):
            stats = await self._cache.get_stats()
            hits = getattr(stats, "hits", 0)
            misses = getattr(stats, "misses", 0)

        total = hits + misses
        hit_rate = hits / total * 100 if total > 0 else 0.0

        return Ok(
            HitMissRatioViewModel(
                hits=hits,
                misses=misses,
                hit_rate_pct=round(hit_rate, 1),
                window_minutes=params.time_window_minutes,
            )
        )


__all__ = ["HitMissRatioWidgetHandler"]
