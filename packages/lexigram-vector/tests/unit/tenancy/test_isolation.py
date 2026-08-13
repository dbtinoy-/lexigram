"""Cross-tenant isolation tests for vector tenancy.

Verifies that two tenants using the same logical collection name resolve
to different physical collections and cannot see each other's data.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.primitives.context import TENANT_ID


@pytest.mark.asyncio
async def test_vector_tenant_isolation_memory_backend() -> None:
    """Real in-memory backend: separate collections per resolved name."""
    from lexigram.vector.backends.memory import MemoryVectorStore
    from lexigram.vector.config import MemoryConfig
    from lexigram.vector.tenancy.decorator import TenantVectorStoreDecorator
    from lexigram.vector.tenancy.resolver import (
        TemplatedTenantCollectionResolver,
    )

    inner = MemoryVectorStore(config=MemoryConfig())
    await inner.connect()

    resolver = TemplatedTenantCollectionResolver()

    ctx_a = MagicMock()
    ctx_a.get.side_effect = lambda k, d=None: "tenant_a" if k == TENANT_ID else d
    ctx_b = MagicMock()
    ctx_b.get.side_effect = lambda k, d=None: "tenant_b" if k == TENANT_ID else d

    store_a = TenantVectorStoreDecorator(inner=inner, resolver=resolver, ctx=ctx_a)
    store_b = TenantVectorStoreDecorator(inner=inner, resolver=resolver, ctx=ctx_b)

    from lexigram.contracts.data.vector.types import CollectionConfig

    # Each tenant creates "canon" → resolves to different physical names
    cfg = CollectionConfig(name="canon", dimension=4)
    await store_a.create_collection(cfg)
    await store_b.create_collection(cfg)

    coll_a = await store_a.get_collection("canon")
    coll_b = await store_b.get_collection("canon")

    # Different physical collections
    assert coll_a is not coll_b

    # Write to each
    await coll_a.add_texts(
        texts=["tenant-a data"], embeddings=[[0.1, 0.2, 0.3, 0.4]],
        metadatas=[{"owner": "a"}], ids=["a-1"],
    )
    await coll_b.add_texts(
        texts=["tenant-b data"], embeddings=[[0.5, 0.6, 0.7, 0.8]],
        metadatas=[{"owner": "b"}], ids=["b-1"],
    )

    from lexigram.contracts.data.vector.types import SearchQuery

    # Tenant B queries — should NOT see tenant A's data
    query_b = SearchQuery(vector=[0.5, 0.6, 0.7, 0.8], top_k=10)
    results_b = await coll_b.search(query_b)
    texts_b = [r.content for r in results_b]
    assert "tenant-a data" not in texts_b
    assert "tenant-b data" in texts_b

    # Tenant A queries — should NOT see tenant B's data
    query_a = SearchQuery(vector=[0.1, 0.2, 0.3, 0.4], top_k=10)
    results_a = await coll_a.search(query_a)
    texts_a = [r.content for r in results_a]
    assert "tenant-b data" not in texts_a
    assert "tenant-a data" in texts_a

    await inner.disconnect()


@pytest.mark.asyncio
async def test_vector_no_tenant_passes_through() -> None:
    """Without tenant context, collection names pass through unmodified."""
    from lexigram.vector.backends.memory import MemoryVectorStore
    from lexigram.vector.config import MemoryConfig
    from lexigram.vector.tenancy.decorator import TenantVectorStoreDecorator
    from lexigram.vector.tenancy.resolver import (
        TemplatedTenantCollectionResolver,
    )

    inner = MemoryVectorStore(config=MemoryConfig())
    await inner.connect()

    ctx_no_tenant = MagicMock()
    ctx_no_tenant.get.return_value = None

    resolver = TemplatedTenantCollectionResolver()
    store = TenantVectorStoreDecorator(inner=inner, resolver=resolver, ctx=ctx_no_tenant)

    from lexigram.contracts.data.vector.types import CollectionConfig

    cfg = CollectionConfig(name="canon", dimension=4)
    await store.create_collection(cfg)
    coll = await store.get_collection("canon")

    assert coll is not None

    await inner.disconnect()
