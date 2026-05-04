"""Hit/miss ratio widget handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
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

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch cache hit/miss stats.

        Infrastructure failures propagate.

        Args:
            params: Widget parameters.

        Returns:
            Result containing StatContent with hit-rate metrics.
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
        hit_rate_pct = round(hit_rate, 1)
        # Template statically styles the rate with text-success — mirror as SUCCESS.
        return Ok(
            StatContent(
                stats=(
                    Stat(
                        label=f"Hit Rate ({params.time_window_minutes}m)",
                        value=f"{hit_rate_pct}%",
                        tone=Tone.SUCCESS,
                    ),
                    Stat(label="Hits", value=str(hits)),
                    Stat(label="Misses", value=str(misses)),
                )
            )
        )


__all__ = ["HitMissRatioWidgetHandler"]
