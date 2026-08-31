"""Storage integration — delegates file field storage to a blob store."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from lexigram.contracts.infra.storage import StorageUnsupportedOperationError

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class _NoOpStorage:
    """Storage-shaped fallback with the canonical blob-store method names."""

    async def upload(
        self,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        return {"path": path, "size": len(data), "content_type": content_type}

    async def download(self, path: str) -> bytes:  # noqa: ARG002
        return b""

    async def delete(self, path: str) -> bool:  # noqa: ARG002
        return True

    async def get_url(self, path: str) -> str:  # noqa: ARG002
        return ""

    async def get_presigned_url(
        self,
        path: str,  # noqa: ARG002
        expires_in: timedelta = timedelta(hours=1),  # noqa: ARG002
        method: str = "GET",  # noqa: ARG002
    ) -> str:
        return ""


class StorageIntegration:
    """Adapter that delegates file storage to lexigram-storage.

    Gracefully no-ops when ``lexigram-storage`` is not installed or the
    integration is disabled.
    """

    def __init__(self, config: Any) -> None:
        self._config = config
        self._store: Any = _NoOpStorage()
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
        await self._store.delete(path)
        return True

    async def presigned_url(self, path: str, expires_in: int | None = None) -> str:
        """Return a temporary GET URL using the blob-store contract's timedelta API."""
        # `or` already skips 0/None from expires_in, but the config attribute
        # can itself be None, which timedelta rejects -- fall back again.
        ttl = expires_in or getattr(self._config, "presigned_url_expiry", 3600) or 3600
        try:
            return await self._store.get_presigned_url(
                path,
                expires_in=timedelta(seconds=ttl),
                method="GET",
            )
        except StorageUnsupportedOperationError:
            # Memory/local drivers may not support presigned URLs but can
            # still provide a deterministic URL for development and previews.
            return await self._store.get_url(path)


__all__ = ["StorageIntegration"]
