"""Cache-backed feature flag provider.

Stores flag definitions in a :class:`~lexigram.contracts.cache.protocols.CacheBackendProtocol`
(e.g. Redis, Memcached, or in-memory).  Each flag is serialised as JSON under a
namespaced key so that multiple applications can share the same cache without
key collisions.

Limitations
-----------
* :meth:`CacheBackendFlagProvider.list_flags` returns an empty list because
  most cache backends (including Redis ``CacheBackendProtocol`` implementations) do not
  expose a key-scan API through the standard protocol.  Applications that need
  to list all flags should maintain a separate index or use a provider that
  supports enumeration (e.g. :class:`~lexigram.features.backends.local.LocalProvider`).
"""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING, Any

from lexigram import serialization as json
from lexigram.features.exceptions import FlagNotFoundError
from lexigram.features.types import Flag, FlagType
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol

logger = get_logger(__name__)


class CacheBackendFlagProvider:
    """Feature-flag provider backed by a :class:`CacheBackendProtocol`.

    Flags are stored as JSON-encoded objects in the cache under keys of the
    form ``{prefix}{name}``.  Each entry is given an independent TTL so that
    flags expire and are treated as absent after the TTL elapses.

    Args:
        cache: The cache backend to use for flag storage and retrieval.
        ttl: Time-to-live in seconds for each cached flag entry.  Defaults
            to 3 600 seconds (1 hour).
        prefix: Key prefix applied to every flag name to avoid collisions
            with other cache users.  Defaults to ``"lexigram:features:flag:"``.
    """

    def __init__(
        self,
        cache: CacheBackendProtocol,
        ttl: int = 3600,
        prefix: str = "lexigram:features:flag:",
    ) -> None:
        self._cache = cache
        self._ttl = ttl
        self._prefix = prefix

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _key(self, name: str) -> str:
        """Build the namespaced cache key for *name*."""
        return f"{self._prefix}{name}"

    @staticmethod
    def _flag_to_dict(flag: Flag) -> dict[str, Any]:
        """Serialise a :class:`Flag` to a JSON-compatible dict."""
        return {
            "name": flag.name,
            "type": flag.type.value,
            "enabled": flag.enabled,
            "description": flag.description,
            "percentage": flag.percentage,
            "user_list": flag.user_list,
            "user_attributes": flag.user_attributes,
            "start_time": flag.start_time.isoformat() if flag.start_time else None,
            "end_time": flag.end_time.isoformat() if flag.end_time else None,
            "variants": flag.variants,
            "default_variant": flag.default_variant,
            "metadata": flag.metadata,
        }

    @staticmethod
    def _dict_to_flag(data: dict[str, Any]) -> Flag:
        """Deserialise a dict produced by :meth:`_flag_to_dict` into a :class:`Flag`."""
        from datetime import datetime

        def _parse_dt(value: str | None) -> datetime | None:
            if value is None:
                return None
            return datetime.fromisoformat(value).replace(tzinfo=UTC)

        return Flag(
            name=data["name"],
            type=FlagType(data.get("type", FlagType.BOOLEAN)),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
            percentage=data.get("percentage", 0),
            user_list=data.get("user_list", []),
            user_attributes=data.get("user_attributes", {}),
            start_time=_parse_dt(data.get("start_time")),
            end_time=_parse_dt(data.get("end_time")),
            variants=data.get("variants", {}),
            default_variant=data.get("default_variant", ""),
            metadata=data.get("metadata", {}),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_flag(self, name: str) -> Flag:
        """Return the :class:`Flag` definition stored under *name*.

        Args:
            name: The flag name to look up.

        Returns:
            The :class:`Flag` stored in the cache.

        Raises:
            FlagNotFoundError: If no flag with *name* exists in the cache.
        """
        raw_result = await self._cache.get(self._key(name))
        if not raw_result.is_ok():
            raise FlagNotFoundError(name)
        raw = raw_result.unwrap()
        if raw is None:
            raise FlagNotFoundError(name)
        data: dict[str, Any] = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
        return self._dict_to_flag(data)

    async def add_flag(self, flag: Flag) -> None:
        """Write *flag* to the cache with the configured TTL.

        Args:
            flag: The :class:`Flag` definition to persist.
        """
        payload = json.dumps(self._flag_to_dict(flag))
        await self._cache.set(self._key(flag.name), payload, ttl=self._ttl)
        logger.debug("cache_flag_added", flag=flag.name, ttl=self._ttl)

    async def remove_flag(self, name: str) -> None:
        """Delete the flag with *name* from the cache.

        A no-op if the flag does not exist (the cache backend returns False
        from ``delete``, which is silently ignored here).

        Args:
            name: The flag name to remove.
        """
        await self._cache.delete(self._key(name))
        logger.debug("cache_flag_removed", flag=name)

    async def list_flags(self) -> list[Flag]:
        """Return all known flags.

        .. note::
            This method always returns an **empty list** because the standard
            :class:`~lexigram.contracts.cache.protocols.CacheBackendProtocol` protocol
            does not expose a key-scan or key-enumeration operation (e.g. Redis
            ``SCAN``).  If you need to enumerate flags, maintain a separate
            index in the cache (a set under a dedicated key) or use a provider
            that natively supports enumeration such as
            :class:`~lexigram.features.backends.local.LocalProvider`.

        Returns:
            Always an empty :class:`list`.
        """
        logger.debug(
            "cache_flag_list_unsupported",
            message=(
                "CacheBackendFlagProvider.list_flags() returns [] — "
                "key enumeration is not part of the CacheBackendProtocol protocol."
            ),
        )
        return []

    async def evaluate(self, name: str, context: dict[str, Any] | None = None) -> bool:
        """Evaluate whether the flag *name* is enabled.

        Fetches the flag from the cache and returns its ``enabled`` field.
        This is a simple boolean check; for richer evaluation (percentage
        rollout, user-list, variant, etc.) use a full
        :class:`~lexigram.features.backends.base.AbstractFlagProvider`.

        Args:
            name: The flag to evaluate.
            context: Optional context dict (not used by this provider; included
                for API consistency with other providers).

        Returns:
            ``True`` if the flag exists and is enabled; ``False`` if the flag
            is disabled.

        Raises:
            FlagNotFoundError: If the flag does not exist in the cache.
        """
        flag = await self.get_flag(name)
        return flag.enabled


__all__ = ["CacheBackendFlagProvider"]
