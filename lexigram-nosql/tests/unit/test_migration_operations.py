from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.nosql.migration.operations import (
    AddField,
    CreateIndex,
    DropCollection,
    DropIndex,
    RenameField,
)


class TestCreateIndex:
    def test_init(self) -> None:
        op = CreateIndex(collection="users", keys=[("email", 1)], unique=True, name="idx_email")
        assert op.collection == "users"
        assert op.keys == [("email", 1)]
        assert op.unique is True
        assert op.name == "idx_email"

    @pytest.mark.asyncio
    async def test_execute_creates_index(self) -> None:
        store = MagicMock()
        col = MagicMock()
        col.create_index = AsyncMock(return_value="idx_email")
        store.collection = MagicMock(return_value=col)

        op = CreateIndex(collection="users", keys=[("email", 1)], name="idx_email")
        await op.execute(store)

        col.create_index.assert_awaited_once_with([("email", 1)], unique=False, name="idx_email")


class TestDropIndex:
    def test_init(self) -> None:
        op = DropIndex(collection="users", name="idx_email")
        assert op.collection == "users"
        assert op.name == "idx_email"

    @pytest.mark.asyncio
    async def test_execute_drops_index(self) -> None:
        store = MagicMock()
        col = MagicMock()
        col._col = MagicMock()
        col._col.drop_index = AsyncMock()
        store.collection = MagicMock(return_value=col)

        op = DropIndex(collection="users", name="idx_email")
        await op.execute(store)

        col._col.drop_index.assert_awaited_once_with("idx_email")

    @pytest.mark.asyncio
    async def test_execute_skips_when_no_raw_collection(self) -> None:
        store = MagicMock()
        col = MagicMock()
        del col._col
        store.collection = MagicMock(return_value=col)

        op = DropIndex(collection="users", name="idx_email")
        await op.execute(store)  # should not raise


class TestRenameField:
    def test_init(self) -> None:
        op = RenameField(collection="users", old_name="username", new_name="name")
        assert op.collection == "users"
        assert op.old_name == "username"
        assert op.new_name == "name"

    @pytest.mark.asyncio
    async def test_execute_renames_field(self) -> None:
        store = MagicMock()
        col = MagicMock()
        col.update_many = AsyncMock()
        store.collection = MagicMock(return_value=col)

        op = RenameField(collection="users", old_name="username", new_name="name")
        await op.execute(store)

        col.update_many.assert_awaited_once_with(
            {"username": {"$exists": True}},
            {"$rename": {"username": "name"}},
        )


class TestAddField:
    def test_init(self) -> None:
        op = AddField(collection="users", field="is_active", default_value=True)
        assert op.collection == "users"
        assert op.field == "is_active"
        assert op.default_value is True

    @pytest.mark.asyncio
    async def test_execute_adds_field(self) -> None:
        store = MagicMock()
        col = MagicMock()
        col.update_many = AsyncMock()
        store.collection = MagicMock(return_value=col)

        op = AddField(collection="users", field="is_active", default_value=True)
        await op.execute(store)

        col.update_many.assert_awaited_once_with(
            {"is_active": {"$exists": False}},
            {"$set": {"is_active": True}},
        )


class TestDropCollection:
    def test_init(self) -> None:
        op = DropCollection(collection="legacy_events")
        assert op.collection == "legacy_events"

    @pytest.mark.asyncio
    async def test_execute_drops_collection(self) -> None:
        store = MagicMock()
        store.drop_collection = AsyncMock()

        op = DropCollection(collection="legacy_events")
        await op.execute(store)

        store.drop_collection.assert_awaited_once_with("legacy_events")
