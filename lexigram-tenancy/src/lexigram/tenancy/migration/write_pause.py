"""Write-pause coordination for tenant tier migration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.cache.protocols import CacheBackendProtocol


class WritePauseRegistry:
    """Coordinates write-pausing during tenant tier migration.

    Uses an optional :class:`~lexigram.contracts.cache.protocols.CacheBackendProtocol`
    for distributed deployments; falls back to an in-memory dict.

    Services check :meth:`is_paused` before accepting write operations for a
    tenant undergoing migration.
    """

    def __init__(self, backend: CacheBackendProtocol | None = None) -> None:
        """Initialise the registry.

        Args:
            backend: Optional distributed cache backend.
        """
        self._backend = backend
        self._local: dict[str, str] = {}

    async def pause(self, tenant_id: str, reason: str = "migration") -> None:
        """Pause writes for a tenant.

        Args:
            tenant_id: The tenant to pause.
            reason: Human-readable reason for the pause.
        """
        if self._backend is not None:
            await self._backend.set(f"w:p:{tenant_id}", reason, ttl=3600)
        self._local[tenant_id] = reason

    async def resume(self, tenant_id: str) -> None:
        """Resume writes for a tenant.

        Args:
            tenant_id: The tenant to resume.
        """
        if self._backend is not None:
            await self._backend.delete(f"w:p:{tenant_id}")
        self._local.pop(tenant_id, None)

    async def is_paused(self, tenant_id: str) -> bool:
        """Check whether writes are paused for a tenant.

        Args:
            tenant_id: The tenant to check.

        Returns:
            ``True`` if writes are paused.
        """
        if tenant_id in self._local:
            return True
        if self._backend is not None:
            val = await self._backend.get(f"w:p:{tenant_id}")
            if val is not None:
                self._local[tenant_id] = val
                return True
        return False

    async def pause_reason(self, tenant_id: str) -> str | None:
        """Return the reason writes are paused, or ``None``.

        Args:
            tenant_id: The tenant to check.
        """
        reason = self._local.get(tenant_id)
        if reason is None and self._backend is not None:
            val = await self._backend.get(f"w:p:{tenant_id}")
            if val is not None:
                self._local[tenant_id] = val
                reason = val
        return reason


__all__ = ["WritePauseRegistry"]
