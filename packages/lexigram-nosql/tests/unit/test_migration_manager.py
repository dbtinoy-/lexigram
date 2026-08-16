"""Tests for MigrationManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.nosql.migration.manager import MigrationManager, MigrationOperation


class FakeOperation(MigrationOperation):
    """Fake migration operation for testing."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def execute(self, store: MagicMock) -> None:
        pass


class AsyncIterWrapper:
    """Wrapper to make async iterator from sync iterable."""

    def __init__(self, items: list[dict]) -> None:
        self._items = iter(items)

    def __aiter__(self) -> AsyncIterWrapper:
        return self

    async def __anext__(self) -> dict:
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration


class TestMigrationManager:
    """Tests for the MigrationManager class."""

    def test_add_registers_migration(self) -> None:
        store = MagicMock()
        manager = MigrationManager(store)
        manager.add("001", "Test migration", FakeOperation("test"))
        assert len(manager._pending) == 1
        version, description, _ = manager._pending[0]
        assert version == "001"
        assert description == "Test migration"

    def test_add_returns_self_for_chaining(self) -> None:
        store = MagicMock()
        manager = MigrationManager(store)
        result = manager.add("001", "First", FakeOperation("op1"))
        result = result.add("002", "Second", FakeOperation("op2"))
        assert len(manager._pending) == 2

    @pytest.mark.asyncio
    async def test_migrate_applies_pending_migrations(self) -> None:
        store = MagicMock()
        mock_collection = MagicMock()
        store.collection = MagicMock(return_value=mock_collection)
        mock_collection.find = MagicMock(return_value=AsyncIterWrapper([]))
        mock_collection.insert_one = AsyncMock()

        manager = MigrationManager(store)
        manager.add("001", "Test migration", FakeOperation("test"))

        result = await manager.migrate()

        assert len(result) == 1
        assert result[0] == "001"

    @pytest.mark.asyncio
    async def test_migrate_skips_applied_migrations(self) -> None:
        store = MagicMock()
        mock_collection = MagicMock()
        store.collection = MagicMock(return_value=mock_collection)
        mock_collection.find = MagicMock(
            return_value=AsyncIterWrapper([{"version": "001"}])
        )
        mock_collection.insert_one = AsyncMock()

        manager = MigrationManager(store)
        manager.add("001", "First", FakeOperation("first"))
        manager.add("002", "Second", FakeOperation("second"))

        result = await manager.migrate()

        assert len(result) == 1
        assert result[0] == "002"

    @pytest.mark.asyncio
    async def test_status_returns_all_migrations(self) -> None:
        store = MagicMock()
        mock_collection = MagicMock()
        store.collection = MagicMock(return_value=mock_collection)
        mock_collection.find = MagicMock(
            return_value=AsyncIterWrapper([{"version": "001"}])
        )

        manager = MigrationManager(store)
        manager.add("001", "First", FakeOperation("first"))
        manager.add("002", "Second", FakeOperation("second"))

        status = await manager.status()

        assert len(status) == 2
        assert status[0]["version"] == "001"
        assert status[0]["applied"] is True
        assert status[1]["version"] == "002"
        assert status[1]["applied"] is False

    @pytest.mark.asyncio
    async def test_get_applied_versions_returns_set(self) -> None:
        store = MagicMock()
        mock_collection = MagicMock()
        store.collection = MagicMock(return_value=mock_collection)
        mock_collection.find = MagicMock(
            return_value=AsyncIterWrapper([
                {"version": "001"},
                {"version": "002"},
            ])
        )

        manager = MigrationManager(store)

        result = await manager.get_applied_versions()

        assert result == {"001", "002"}


class TestMigrationIdempotence:
    """Tests for migration idempotence - running same migration twice is safe."""

    @pytest.mark.asyncio
    async def test_running_migration_twice_only_applies_once(self) -> None:
        store = MagicMock()
        mock_collection = MagicMock()
        store.collection = MagicMock(return_value=mock_collection)

        call_count = 0

        def mock_find(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return AsyncIterWrapper([])
            return AsyncIterWrapper([{"version": "001"}])

        mock_collection.find = mock_find
        mock_collection.insert_one = AsyncMock()

        manager = MigrationManager(store)
        manager.add("001", "Test migration", FakeOperation("test"))

        result1 = await manager.migrate()
        result2 = await manager.migrate()

        assert len(result1) == 1
        assert result1[0] == "001"
        assert len(result2) == 0
        assert mock_collection.insert_one.call_count == 1

    @pytest.mark.asyncio
    async def test_migration_sorted_by_version(self) -> None:
        store = MagicMock()
        mock_collection = MagicMock()
        store.collection = MagicMock(return_value=mock_collection)
        mock_collection.find = MagicMock(return_value=AsyncIterWrapper([]))
        mock_collection.insert_one = AsyncMock()

        manager = MigrationManager(store)
        manager.add("002", "Second", FakeOperation("second"))
        manager.add("001", "First", FakeOperation("first"))
        manager.add("003", "Third", FakeOperation("third"))

        result = await manager.migrate()

        assert result == ["001", "002", "003"]

    @pytest.mark.asyncio
    async def test_migration_applies_in_version_order(self) -> None:
        store = MagicMock()
        mock_collection = MagicMock()
        store.collection = MagicMock(return_value=mock_collection)
        mock_collection.find = MagicMock(return_value=AsyncIterWrapper([]))
        mock_collection.insert_one = AsyncMock()

        applied_order: list[str] = []

        class TrackingOperation(MigrationOperation):
            def __init__(self, version: str) -> None:
                self.version = version

            async def execute(self, store: MagicMock) -> None:
                applied_order.append(self.version)

        manager = MigrationManager(store)
        manager.add("002", "Second", TrackingOperation("002"))
        manager.add("001", "First", TrackingOperation("001"))
        manager.add("003", "Third", TrackingOperation("003"))

        await manager.migrate()

        assert applied_order == ["001", "002", "003"]
