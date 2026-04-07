"""Storage integration — delegates file field storage to a blob store."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class _NoOpStorage:
    async def put(
        self, path: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> dict[str, Any]:
        return {"path": path, "size": len(data)}

    async def get(self, path: str) -> bytes:
        return b""

    async def delete(self, path: str) -> bool:
        return True

    async def presigned_url(self, path: str, expires_in: int = 3600) -> str:
        return ""


class StorageIntegration:
    """Adapter that delegates file storage to lexigram-storage.

    Gracefully no-ops when ``lexigram-storage`` is not installed or the
    integration is disabled.
    """

    def __init__(self, config: Any) -> None:
        self._config = config
        self._store: Any = None
        self._enabled = False

    def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.admin.config import StorageIntegrationConfig
        from lexigram.admin.integrations._optional import is_installed

        cfg = self._config
        if not isinstance(cfg, StorageIntegrationConfig):
            cfg = StorageIntegrationConfig()
        if not cfg.enabled:
            self._store = _NoOpStorage()
            return
        if not is_installed("lexigram.storage"):
            self._store = _NoOpStorage()
            return
        self._enabled = True

    async def boot(self, container: ContainerResolverProtocol) -> None:
        if not self._enabled:
            return
        try:
            from lexigram.contracts.infra.storage import BlobStoreProtocol

            self._store = await container.resolve(BlobStoreProtocol)
        except Exception:  # noqa: BLE001
            self._store = _NoOpStorage()

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy" if not isinstance(self._store, _NoOpStorage) else "noop"
        }

    async def put(
        self, path: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> dict[str, Any]:
        return await self._store.upload(path, data, content_type=content_type)

    async def get(self, path: str) -> bytes:
        return await self._store.download(path)

    async def delete(self, path: str) -> bool:
        return await self._store.delete(path)

    async def presigned_url(self, path: str, expires_in: int | None = None) -> str:
        ttl = expires_in or getattr(self._config, "presigned_url_expiry", 3600)
        return await self._store.get_presigned_url(path, expires_in=ttl, method="get")


__all__ = ["StorageIntegration"]
