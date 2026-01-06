from __future__ import annotations

"""Qdrant vector store provider lifecycle integration tests."""

import pytest

from lexigram.testing.integration.fixtures import qdrant_client  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.requires_qdrant]


class TestQdrantProviderLifecycle:
    """Verify QdrantStore connects, operates, and disconnects with real Qdrant.

    Skipped automatically when the Qdrant instance is unavailable.
    """

    async def test_client_is_reachable(self, qdrant_client: object) -> None:
        """Qdrant client fixture is connected and the server responds.

        Args:
            qdrant_client: Session-scoped AsyncQdrantClient.
        """
        collections = await qdrant_client.get_collections()
        assert collections is not None

    async def test_create_and_delete_collection_round_trip(
        self, qdrant_client: object
    ) -> None:
        """Collection creation and deletion complete without errors.

        Creates a temporary collection, asserts it appears in the listing,
        then deletes it to leave the server clean.

        Args:
            qdrant_client: Session-scoped AsyncQdrantClient.
        """
        from qdrant_client.models import Distance, VectorParams

        collection_name = "lifecycle_test_collection"

        await qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=4, distance=Distance.COSINE),
        )

        collections_response = await qdrant_client.get_collections()
        collection_names = [c.name for c in collections_response.collections]
        assert collection_name in collection_names

        await qdrant_client.delete_collection(collection_name=collection_name)

        collections_response = await qdrant_client.get_collections()
        collection_names_after = [c.name for c in collections_response.collections]
        assert collection_name not in collection_names_after

    async def test_vector_provider_can_be_created(self) -> None:
        """VectorProvider can be instantiated with Qdrant backend config.

        Exercises the provider constructor path for the qdrant backend without
        requiring a live connection.
        """
        from lexigram.vector.config import QdrantConfig, VectorConfig
        from lexigram.vector.di.provider import VectorProvider

        config = VectorConfig(backend="qdrant", qdrant=QdrantConfig())
        provider = VectorProvider(config=config)
        assert provider is not None
        assert provider.name == "vector"
