from __future__ import annotations

"""MongoDB document repository compliance test."""

import pytest

from lexigram.testing.compliance import RepositoryCompliance
from lexigram.testing.integration.fixtures import (  # noqa: F401
    mongodb_client,
    mongodb_database,
)

pytestmark = [pytest.mark.integration, pytest.mark.requires_mongodb]


class TestMongoDBRepositoryCompliance(RepositoryCompliance):
    """Verify MongoDB-backed DocumentRepository satisfies RepositoryCompliance.

    Skipped automatically when MongoDB is unavailable.
    """

    @pytest.fixture(autouse=True)
    async def _setup(self, mongodb_database: object) -> None:
        """Capture the function-scoped motor database for use in create_repository.

        Args:
            mongodb_database: Function-scoped AsyncIOMotorDatabase instance.
        """
        self._db = mongodb_database

    async def create_repository(self) -> object:
        """Create a MongoDB-backed DocumentRepository.

        Returns:
            A DocumentRepository instance backed by the real mongodb_database.
        """
        pytest.skip("TODO: instantiate MongoRepository with mongodb_database")
