"""Tenant-aware VectorStoreProtocol decorator.

Auto-resolves collection names using the current tenant context so
that each tenant operates on an isolated set of collections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.primitives.context import TENANT_ID, Context

if TYPE_CHECKING:
    from lexigram.contracts.core.health import HealthCheckResult
    from lexigram.contracts.data.vector.protocols import (
        VectorCollectionProtocol,
        VectorStoreProtocol,
    )
    from lexigram.contracts.data.vector.tenancy import TenantCollectionResolver
    from lexigram.contracts.data.vector.types import (
        CollectionConfig,
        CollectionInfo,
        UpsertResult,
    )


class TenantVectorStoreDecorator:
    """Wraps a ``VectorStoreProtocol``, automatically resolving collection
    names to tenant-scoped names before delegating.

    Lifecycle methods (``connect``, ``disconnect``, ``health_check``) and
    ``list_collections`` pass through without name resolution.

    Usage::

        from lexigram.vector.tenancy.decorator import TenantVectorStoreDecorator
        store = TenantVectorStoreDecorator(inner=backend, resolver=resolver, ctx=ctx)
        await store.get_collection("canon")  # → inner.get_collection("canon_t_{tid}")
    """

    def __init__(
        self,
        inner: VectorStoreProtocol,
        resolver: TenantCollectionResolver,
        ctx: Context,
    ) -> None:
        self._inner = inner
        self._resolver = resolver
        self._ctx = ctx

    def _resolve(self, name: str) -> str:
        tenant_id = self._ctx.get(TENANT_ID)
        if tenant_id is None:
            return name
        return self._resolver.resolve(name, tenant_id)

    async def connect(self) -> None:
        """Establish connection (delegates to inner)."""
        await self._inner.connect()

    async def disconnect(self) -> None:
        """Close connection (delegates to inner)."""
        await self._inner.disconnect()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check store health (delegates to inner)."""
        return await self._inner.health_check(timeout)  # type: ignore[return-value]

    async def list_collections(self) -> list[CollectionInfo]:
        """List all collections (pass-through, no name resolution)."""
        return await self._inner.list_collections()  # type: ignore[return-value]

    async def create_collection(self, config: CollectionConfig) -> None:
        """Create a collection with tenant-scoped name."""
        resolved = self._resolve(config.name)
        from dataclasses import replace

        tenant_config = replace(config, name=resolved)
        await self._inner.create_collection(tenant_config)

    async def delete_collection(self, name: str) -> None:
        """Delete a tenant-scoped collection."""
        await self._inner.delete_collection(self._resolve(name))

    async def collection_exists(self, name: str) -> bool:
        """Check if a tenant-scoped collection exists."""
        return await self._inner.collection_exists(self._resolve(name))  # type: ignore[return-value]

    async def get_collection(self, name: str) -> VectorCollectionProtocol:
        """Get a tenant-scoped collection handle."""
        return await self._inner.get_collection(self._resolve(name))  # type: ignore[return-value]

    async def add_texts(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        collection_name: str,
    ) -> UpsertResult:
        """Add texts to a tenant-scoped collection."""
        resolved = self._resolve(collection_name)
        return await self._inner.add_texts(  # type: ignore[return-value]
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            collection_name=resolved,
        )


__all__ = ["TenantVectorStoreDecorator"]
