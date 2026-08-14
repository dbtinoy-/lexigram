"""Lazy loading and deferred field support for large data models."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class LazyField(Generic[T]):
    """
    A field that loads its value only on demand.
    Useful for heavy BLOBs, large JSON fields, or remote related data.
    """

    def __init__(self, loader: Callable[[], Awaitable[T]]):
        self._loader = loader
        self._value: T | None = None
        self._loaded = False

    async def get(self) -> T:
        """Fetch and return the value, caching it for future calls."""
        if not self._loaded:
            self._value = await self._loader()
            self._loaded = True
        return self._value  # type: ignore[return-value]

    @property
    def is_loaded(self) -> bool:
        return self._loaded


class DeferredField:
    """
    Marker for fields that should be excluded from default SELECT
    and only fetched when explicitly requested.
    """

    def __init__(self, original_type: Any):
        self.original_type = original_type
