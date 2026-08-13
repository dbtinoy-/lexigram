"""Tests for the TenantVectorStoreDecorator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.data.vector.types import CollectionConfig, CollectionInfo
from lexigram.contracts.data.vector.protocols import VectorStoreProtocol


@pytest.fixture
def mock_inner() -> MagicMock:
    inner = MagicMock(spec=VectorStoreProtocol)
    inner.connect = AsyncMock()
    inner.disconnect = AsyncMock()
    inner.health_check = AsyncMock()
    inner.list_collections = AsyncMock(return_value=[])
    inner.create_collection = AsyncMock()
    inner.delete_collection = AsyncMock()
    inner.collection_exists = AsyncMock(return_value=False)
    inner.get_collection = AsyncMock()
    inner.add_texts = AsyncMock()
    return inner


@pytest.fixture
def mock_ctx() -> MagicMock:
    ctx = MagicMock()
    return ctx


@pytest.fixture
def mock_resolver() -> MagicMock:
    resolver = MagicMock()
    resolver.resolve.side_effect = lambda name, tid: f"{name}_t_{tid}"
    return resolver


TENANT_ID_KEY = "tenant_id"


class TestTenantVectorStoreDecorator:
    """Tests for the tenant-ware vector store decorator."""

    def _make_decorator(self, mock_inner, mock_ctx, mock_resolver):
        from lexigram.vector.tenancy.decorator import TenantVectorStoreDecorator
        return TenantVectorStoreDecorator(
            inner=mock_inner,
            resolver=mock_resolver,
            ctx=mock_ctx,
        )

    @pytest.mark.asyncio
    async def test_connect_delegates(self, mock_inner, mock_ctx, mock_resolver) -> None:
        decorator = self._make_decorator(mock_inner, mock_ctx, mock_resolver)
        await decorator.connect()
        mock_inner.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_delegates(self, mock_inner, mock_ctx, mock_resolver) -> None:
        decorator = self._make_decorator(mock_inner, mock_ctx, mock_resolver)
        await decorator.disconnect()
        mock_inner.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_health_check_delegates(self, mock_inner, mock_ctx, mock_resolver) -> None:
        decorator = self._make_decorator(mock_inner, mock_ctx, mock_resolver)
        await decorator.health_check()
        mock_inner.health_check.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_collection_resolves_name(self, mock_inner, mock_ctx, mock_resolver) -> None:
        mock_ctx.get.return_value = "tenant_abc"
        decorator = self._make_decorator(mock_inner, mock_ctx, mock_resolver)
        config = CollectionConfig(name="my_collection", dimension=128)
        await decorator.create_collection(config)
        mock_resolver.resolve.assert_called_once_with("my_collection", "tenant_abc")
        # The resolved name should be passed as the collection config name
        called_config = mock_inner.create_collection.call_args[0][0]
        assert called_config.name == "my_collection_t_tenant_abc"

    @pytest.mark.asyncio
    async def test_get_collection_resolves_name(self, mock_inner, mock_ctx, mock_resolver) -> None:
        mock_ctx.get.return_value = "tenant_abc"
        decorator = self._make_decorator(mock_inner, mock_ctx, mock_resolver)
        await decorator.get_collection("my_collection")
        mock_resolver.resolve.assert_called_once_with("my_collection", "tenant_abc")
        mock_inner.get_collection.assert_awaited_once_with("my_collection_t_tenant_abc")

    @pytest.mark.asyncio
    async def test_delete_collection_resolves_name(self, mock_inner, mock_ctx, mock_resolver) -> None:
        mock_ctx.get.return_value = "tenant_abc"
        decorator = self._make_decorator(mock_inner, mock_ctx, mock_resolver)
        await decorator.delete_collection("my_collection")
        mock_resolver.resolve.assert_called_once_with("my_collection", "tenant_abc")
        mock_inner.delete_collection.assert_awaited_once_with("my_collection_t_tenant_abc")

    @pytest.mark.asyncio
    async def test_collection_exists_resolves_name(self, mock_inner, mock_ctx, mock_resolver) -> None:
        mock_ctx.get.return_value = "tenant_abc"
        decorator = self._make_decorator(mock_inner, mock_ctx, mock_resolver)
        await decorator.collection_exists("my_collection")
        mock_resolver.resolve.assert_called_once_with("my_collection", "tenant_abc")
        mock_inner.collection_exists.assert_awaited_once_with("my_collection_t_tenant_abc")

    @pytest.mark.asyncio
    async def test_add_texts_resolves_collection_name(
        self, mock_inner, mock_ctx, mock_resolver
    ) -> None:
        mock_ctx.get.return_value = "tenant_abc"
        decorator = self._make_decorator(mock_inner, mock_ctx, mock_resolver)
        await decorator.add_texts(
            texts=["hello"], embeddings=[[0.1]], metadatas=[{}],
            collection_name="my_collection",
        )
        mock_resolver.resolve.assert_called_once_with("my_collection", "tenant_abc")
        mock_inner.add_texts.assert_awaited_once_with(
            texts=["hello"], embeddings=[[0.1]], metadatas=[{}],
            collection_name="my_collection_t_tenant_abc",
        )

    @pytest.mark.asyncio
    async def test_list_collections_delegates_without_resolving(
        self, mock_inner, mock_ctx, mock_resolver
    ) -> None:
        mock_ctx.get.return_value = "tenant_abc"
        decorator = self._make_decorator(mock_inner, mock_ctx, mock_resolver)
        await decorator.list_collections()
        mock_resolver.resolve.assert_not_called()
        mock_inner.list_collections.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_tenant_passes_original_name(
        self, mock_inner, mock_ctx, mock_resolver
    ) -> None:
        mock_ctx.get.return_value = None
        decorator = self._make_decorator(mock_inner, mock_ctx, mock_resolver)
        await decorator.get_collection("my_collection")
        mock_resolver.resolve.assert_not_called()
        mock_inner.get_collection.assert_awaited_once_with("my_collection")

    @pytest.mark.asyncio
    async def test_different_tenants_different_collections(
        self, mock_inner, mock_ctx, mock_resolver
    ) -> None:
        mock_ctx.get.side_effect = ["tenant_a", "tenant_b"]
        decorator = self._make_decorator(mock_inner, mock_ctx, mock_resolver)
        await decorator.get_collection("col")
        await decorator.get_collection("col")
        assert mock_inner.get_collection.call_args_list[0][0][0] != \
               mock_inner.get_collection.call_args_list[1][0][0]

    def test_implements_vector_store_protocol(
        self, mock_inner, mock_ctx, mock_resolver
    ) -> None:
        from lexigram.vector.tenancy.decorator import TenantVectorStoreDecorator
        decorator = self._make_decorator(mock_inner, mock_ctx, mock_resolver)
        assert isinstance(decorator, VectorStoreProtocol)

    @pytest.mark.asyncio
    async def test_create_collection_preserves_other_config_fields(
        self, mock_inner, mock_ctx, mock_resolver
    ) -> None:
        mock_ctx.get.return_value = "t1"
        decorator = self._make_decorator(mock_inner, mock_ctx, mock_resolver)
        config = CollectionConfig(
            name="docs", dimension=768, distance_metric="cosine",
        )
        await decorator.create_collection(config)
        called_config: CollectionConfig = mock_inner.create_collection.call_args[0][0]
        assert called_config.dimension == 768
        assert called_config.distance_metric == "cosine"
        assert called_config.name == "docs_t_t1"
