"""Tests for data/admin_repository.py — AdminUserRepository in-memory implementation."""

from __future__ import annotations

import pytest

from lexigram.admin.data.admin_repository import AdminUserRepository
from lexigram.admin.domain.aggregate import AdminUserAggregate


class ConcreteAdminUserRepository(AdminUserRepository):
    """Concrete subclass implementing abstract methods for testing."""

    async def delete_many(self, entity_ids: list) -> int:
        count = 0
        for eid in entity_ids:
            if await self._delete(eid):
                count += 1
        return count

    async def save_many(self, entities: list) -> list:
        results = []
        for entity in entities:
            results.append(await self._save(entity))
        return results


def make_aggregate(
    user_id: str = "user-1",
    username: str = "alice",
    email: str = "alice@example.com",
    roles: list[str] | None = None,
    is_active: bool = True,
) -> AdminUserAggregate:
    """Helper to create a test AdminUserAggregate."""
    return AdminUserAggregate.create(
        user_id=user_id,
        username=username,
        email=email,
        hashed_password="hashed",
        roles=roles or ["viewer"],
        actor_id="test-actor",
    )


class TestAdminUserRepository:
    """Tests for AdminUserRepository."""

    @pytest.mark.asyncio
    async def test_fetch_by_id_returns_none_when_empty(self) -> None:
        repo = ConcreteAdminUserRepository()
        result = await repo._fetch_by_id("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_and_fetch_by_id(self) -> None:
        repo = ConcreteAdminUserRepository()
        agg = make_aggregate("user-1")
        await repo._save(agg)

        result = await repo._fetch_by_id("user-1")
        assert result is agg

    @pytest.mark.asyncio
    async def test_save_overwrites_existing(self) -> None:
        repo = ConcreteAdminUserRepository()
        agg1 = make_aggregate("user-1", username="alice")
        agg2 = make_aggregate("user-1", username="alice-v2")
        await repo._save(agg1)
        await repo._save(agg2)

        result = await repo._fetch_by_id("user-1")
        assert result is agg2

    @pytest.mark.asyncio
    async def test_delete_existing_returns_true(self) -> None:
        repo = ConcreteAdminUserRepository()
        agg = make_aggregate("user-1")
        await repo._save(agg)

        deleted = await repo._delete("user-1")
        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self) -> None:
        repo = ConcreteAdminUserRepository()
        deleted = await repo._delete("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_removes_from_store(self) -> None:
        repo = ConcreteAdminUserRepository()
        agg = make_aggregate("user-1")
        await repo._save(agg)
        await repo._delete("user-1")

        result = await repo._fetch_by_id("user-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_many_returns_all(self) -> None:
        repo = ConcreteAdminUserRepository()
        agg1 = make_aggregate("u1", email="a@x.com")
        agg2 = make_aggregate("u2", email="b@x.com")
        await repo._save(agg1)
        await repo._save(agg2)

        results = await repo._fetch_many(skip=0, limit=10, filters={})
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_fetch_many_with_pagination(self) -> None:
        repo = ConcreteAdminUserRepository()
        for i in range(5):
            await repo._save(make_aggregate(f"u{i}", email=f"u{i}@x.com"))

        page1 = await repo._fetch_many(skip=0, limit=2, filters={})
        page2 = await repo._fetch_many(skip=2, limit=2, filters={})
        assert len(page1) == 2
        assert len(page2) == 2

    @pytest.mark.asyncio
    async def test_fetch_many_with_filter(self) -> None:
        repo = ConcreteAdminUserRepository()
        agg1 = make_aggregate("u1", is_active=True)
        agg2 = make_aggregate("u2", is_active=False)
        agg2.is_active = False
        await repo._save(agg1)
        await repo._save(agg2)

        results = await repo._fetch_many(skip=0, limit=10, filters={"is_active": True})
        assert len(results) == 1
        assert results[0] is agg1

    @pytest.mark.asyncio
    async def test_count_empty(self) -> None:
        repo = ConcreteAdminUserRepository()
        count = await repo._count(filters={})
        assert count == 0

    @pytest.mark.asyncio
    async def test_count_with_items(self) -> None:
        repo = ConcreteAdminUserRepository()
        for i in range(3):
            await repo._save(make_aggregate(f"u{i}", email=f"u{i}@x.com"))

        count = await repo._count(filters={})
        assert count == 3

    @pytest.mark.asyncio
    async def test_find_by_spec(self) -> None:
        from unittest.mock import MagicMock

        repo = ConcreteAdminUserRepository()
        agg1 = make_aggregate("u1", username="alice")
        agg2 = make_aggregate("u2", username="bob")
        await repo._save(agg1)
        await repo._save(agg2)

        # Spec that only accepts alice
        spec = MagicMock()
        spec.is_satisfied_by = lambda item: item.username == "alice"

        results = await repo.find_by_spec(spec)
        assert len(results) == 1
        assert results[0] is agg1
