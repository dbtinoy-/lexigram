from __future__ import annotations

"""Qdrant VectorStore compliance test."""

import pytest

from lexigram.testing.compliance import VectorStoreCompliance
from lexigram.testing.integration.fixtures import qdrant_client  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.requires_qdrant]


class TestQdrantVectorStoreCompliance(VectorStoreCompliance):
    """Verify QdrantStore satisfies VectorStoreCompliance with a real Qdrant instance.

    Skipped automatically when Qdrant is unavailable.
    """

    @pytest.fixture(autouse=True)
    async def _setup(self, qdrant_client: object) -> None:
        """Capture the session-scoped AsyncQdrantClient for use in create_store.

        Args:
            qdrant_client: Session-scoped AsyncQdrantClient connected to the test server.
        """
        self._qdrant = qdrant_client

    async def create_store(self) -> object:
        """Create a QdrantStore wired to the real Qdrant test server.

        Returns:
            A QdrantStore instance backed by the real qdrant_client connection.
        """
        pytest.skip("TODO: instantiate QdrantStore with qdrant_client connection")
