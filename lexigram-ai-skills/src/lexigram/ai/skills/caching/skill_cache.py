"""SkillResultCache — two-tier in-memory and optional backend result caching."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from lexigram.contracts.ai.skills import SkillResult
from lexigram.logging import (
    get_logger,
)
from lexigram.serialization.backends.json import dumps_str, loads

if TYPE_CHECKING:
    from lexigram.contracts.infra.cache import CacheBackendProtocol

logger = get_logger(__name__)

_SENTINEL = object()


def _cache_key(skill_name: str, params: dict[str, Any]) -> str:
    """Build a deterministic cache key from skill name and parameters.

    Args:
        skill_name: The name of the skill.
        params: Parameters dict (must be JSON-serialisable).

    Returns:
        A hex-digest string suitable for use as a dict key or cache key.
    """
    serialised = dumps_str({"skill": skill_name, "params": params}, sort_keys=True)
    return hashlib.sha256(serialised.encode()).hexdigest()


class SkillResultCache:
    """Two-tier result cache for skill executions.

    The first tier is an in-process ``dict``; the second tier is an optional
    :class:`CacheBackendProtocol` (e.g. Redis).  Lookups check the in-process dict
    first; on a miss they query the backend and populate the in-process dict.

    Args:
        backend: Optional async cache backend for cross-process caching.
        ttl_seconds: Time-to-live for backend entries in seconds.
    """

    def __init__(
        self,
        backend: CacheBackendProtocol | None = None,
        ttl_seconds: int = 3600,
    ) -> None:
        """Initialise the cache.

        Args:
            backend: Optional CacheBackendProtocol for distributed caching.
            ttl_seconds: TTL for backend cache entries.
        """
        self._local: dict[str, SkillResult] = {}
        self._backend = backend
        self._ttl = ttl_seconds

    async def get(self, skill_name: str, params: dict[str, Any]) -> SkillResult | None:
        """Return a cached result for the given skill invocation.

        Args:
            skill_name: Name of the skill.
            params: Parameters the skill was called with.

        Returns:
            The cached :class:`SkillResult` or ``None`` when not cached.
        """
        key = _cache_key(skill_name, params)

        hit = self._local.get(key)
        if hit is not None:
            logger.debug("skill_cache_local_hit", skill=skill_name, key=key[:8])
            return hit

        if self._backend is not None:
            raw = await self._backend.get(key)
            if raw is not None:
                try:
                    data = loads(raw)  # type: ignore[arg-type]
                    result = SkillResult(**data)
                    self._local[key] = result
                    logger.debug(
                        "skill_cache_backend_hit", skill=skill_name, key=key[:8]
                    )
                    return result
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "skill_cache_deserialise_error",
                        key=key[:8],
                        error=str(exc),
                    )

        return None

    async def set(
        self, skill_name: str, params: dict[str, Any], result: SkillResult
    ) -> None:
        """Store a skill result in both cache tiers.

        Args:
            skill_name: Name of the skill.
            params: Parameters the skill was called with.
            result: The :class:`SkillResult` to cache.
        """
        key = _cache_key(skill_name, params)
        self._local[key] = result

        if self._backend is not None:
            try:
                serialised = dumps_str(
                    {
                        "skill_name": result.skill_name,
                        "success": result.success,
                        "output": result.output,
                        "error": result.error,
                        "metadata": result.metadata,
                    }
                )
                await self._backend.set(key, serialised, ttl=self._ttl)
            except Exception as exc:  # noqa: BLE001
                logger.warning("skill_cache_store_error", key=key[:8], error=str(exc))

    def invalidate(self, skill_name: str, params: dict[str, Any]) -> None:
        """Remove a single entry from the local in-process cache.

        Args:
            skill_name: Name of the skill.
            params: Parameters identifying the entry to remove.
        """
        key = _cache_key(skill_name, params)
        self._local.pop(key, None)

    def clear(self) -> None:
        """Remove all entries from the local in-process cache."""
        self._local.clear()
