from __future__ import annotations

"""PostgreSQL repository compliance test."""

import pytest
from datetime import UTC, datetime

pytestmark = [pytest.mark.integration, pytest.mark.requires_postgres]


class TestPostgresRepositoryCompliance:
    """Verify PostgreSQL repository satisfies RepositoryCompliance."""

    @pytest.fixture
    def sample_entity(self) -> dict:
        """Create a sample entity for testing."""
        return {
            "id": "test-123",
            "name": "Test Entity",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

    async def test_save_and_find(
        self,
        postgres_pool: object,
        postgres_conn: object,
        sample_entity: dict,
    ) -> None:
        """save() and find_by_id() round-trip an entity."""
        from lexigram.sql.repositories import SqlRepository

        repo = SqlRepository(pool=postgres_pool)

        await repo.save("entities", sample_entity)

        found = await repo.find_by_id("entities", sample_entity["id"])

        assert found is not None
        assert found["id"] == sample_entity["id"]
        assert found["name"] == sample_entity["name"]

    async def test_delete_removes_entity(
        self,
        postgres_pool: object,
        postgres_conn: object,
        sample_entity: dict,
    ) -> None:
        """delete() removes entity from storage."""
        from lexigram.sql.repositories import SqlRepository

        repo = SqlRepository(pool=postgres_pool)

        await repo.save("entities", sample_entity)

        deleted = await repo.delete("entities", sample_entity["id"])
        assert deleted is True

        found = await repo.find_by_id("entities", sample_entity["id"])
        assert found is None

    async def test_find_all_returns_list(
        self,
        postgres_pool: object,
        sample_entity: dict,
    ) -> None:
        """find_all() returns all saved entities."""
        from lexigram.sql.repositories import SqlRepository

        repo = SqlRepository(pool=postgres_pool)

        entity1 = {**sample_entity, "id": "test-1"}
        entity2 = {**sample_entity, "id": "test-2"}

        await repo.save("entities", entity1)
        await repo.save("entities", entity2)

        all_entities = await repo.find_all("entities")

        assert len(all_entities) >= 2
        ids = [e["id"] for e in all_entities]
        assert "test-1" in ids
        assert "test-2" in ids