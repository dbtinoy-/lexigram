"""Retry utilities — thin re-export from lexigram.sql.resilience.core.

The canonical implementation lives in :mod:`lexigram.sql.resilience.core`.
This module is retained to avoid breaking the four database drivers that
import ``retry_call`` from here.  New code should import directly from
``lexigram.sql.resilience.core``.
"""

from __future__ import annotations

from lexigram.sql.resilience.core import retry_call as retry_call


def retry(config=None):
    """Retry decorator — delegates to resilience.core.retry_call.

    Args:
        config: :class:`~lexigram.contracts.resilience.RetryConfig` or ``None``.
    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_call(func, *args, config=config, **kwargs)

        return wrapper

    return decorator


__all__ = ["retry", "retry_call"]
