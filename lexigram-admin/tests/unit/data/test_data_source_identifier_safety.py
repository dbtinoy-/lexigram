"""Identifier-safety regression tests for SqlDataSource (Round 7 finding 31).

Verifies the §33 closure: every identifier position in
``find_many``/``create``/``update`` routes through ``_quote_identifier``,
hostile names raise ``ValueError`` before any SQL text reaches the
database, and benign names still produce double-quoted identifiers.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from lexigram.admin.data.data_source import SqlDataSource

HOSTILE_FIELD = "email) VALUES ('x',"
HOSTILE_TABLE = "users; DROP TABLE"
HOSTILE_FILTER = "x = 1 OR 1=1 --"
HOSTILE_ID = "id; DROP TABLE"


class FakeDb:
    """Recording fake for the database provider surface used by SqlDataSource."""

    def __init__(self) -> None:
        self.fetch_one = AsyncMock(return_value={"id": 1})
        self.fetch_all = AsyncMock(return_value=[])
        self.execute = AsyncMock(return_value=1)

    def assert_untouched(self) -> None:
        """Assert no SQL call ever reached the provider."""
        self.fetch_one.assert_not_awaited()
        self.fetch_all.assert_not_awaited()
        self.execute.assert_not_awaited()


def make_source(
    table_name: str = "users", id_field: str = "id", db: FakeDb | None = None
) -> SqlDataSource[Any]:
    """Build a SqlDataSource over a recording fake provider."""
    return SqlDataSource(db=db or FakeDb(), table_name=table_name, id_field=id_field)  # type: ignore[arg-type]


class TestFindManyIdentifierSafety:
    """find_many filter-field interpolation is guarded."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "hostile",
        [HOSTILE_FIELD, HOSTILE_FILTER, "users; DROP TABLE", "name--"],
    )
    async def test_hostile_filter_key_raises_and_never_reaches_db(
        self, hostile: str
    ) -> None:
        db = FakeDb()
        source = make_source(db=db)
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            await source.find_many(**{hostile: "value"})
        db.assert_untouched()

    @pytest.mark.asyncio
    async def test_benign_filters_produce_quoted_identifiers(self) -> None:
        db = FakeDb()
        db.fetch_one.return_value = (5,)
        source = make_source(db=db)
        await source.find_many(name="Ada", page=1, per_page=20)
        select_sql = db.fetch_all.await_args.args[0]
        count_sql = db.fetch_one.await_args.args[0]
        assert '"name" = $1' in select_sql
        assert '"name" = $1' in count_sql
        assert 'FROM "users"' in select_sql
        assert db.fetch_all.await_args.args[1] == ["Ada"]


class TestCreateIdentifierSafety:
    """create column-list and table-name interpolation are guarded."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "entity",
        [
            {HOSTILE_FIELD: "value"},
            {"ok": 1, "b; DROP": 2},
            {"ok": 1, HOSTILE_FILTER: 2},
        ],
    )
    async def test_hostile_field_name_raises_and_never_reaches_db(
        self, entity: dict[str, Any]
    ) -> None:
        db = FakeDb()
        source = make_source(db=db)
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            await source.create(entity)
        db.assert_untouched()

    @pytest.mark.asyncio
    async def test_hostile_table_name_raises_and_never_reaches_db(self) -> None:
        db = FakeDb()
        source = make_source(table_name=HOSTILE_TABLE, db=db)
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            await source.create({"ok": 1})
        db.assert_untouched()

    @pytest.mark.asyncio
    async def test_benign_create_produces_quoted_identifiers(self) -> None:
        db = FakeDb()
        source = make_source(db=db)
        await source.create({"name": "Ada", "email": "ada@example.com"})
        sql = db.fetch_one.await_args.args[0]
        assert 'INSERT INTO "users" ("name", "email")' in sql
        assert db.fetch_one.await_args.args[1] == ["Ada", "ada@example.com"]


class TestUpdateIdentifierSafety:
    """update set-clause, table, and id-field interpolation are guarded."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "data",
        [
            {HOSTILE_FIELD: "value"},
            {"email": "x", "b = 1 --": "y"},
            {"ok": 1, HOSTILE_FILTER: 2},
        ],
    )
    async def test_hostile_field_name_raises_and_never_reaches_db(
        self, data: dict[str, Any]
    ) -> None:
        db = FakeDb()
        source = make_source(db=db)
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            await source.update(1, data)
        db.assert_untouched()

    @pytest.mark.asyncio
    async def test_hostile_table_name_raises_and_never_reaches_db(self) -> None:
        db = FakeDb()
        source = make_source(table_name=HOSTILE_TABLE, db=db)
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            await source.update(1, {"ok": 2})
        db.assert_untouched()

    @pytest.mark.asyncio
    async def test_hostile_id_field_raises_and_never_reaches_db(self) -> None:
        db = FakeDb()
        source = make_source(id_field=HOSTILE_ID, db=db)
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            await source.update(1, {"ok": 2})
        db.assert_untouched()

    @pytest.mark.asyncio
    async def test_benign_update_produces_quoted_identifiers(self) -> None:
        db = FakeDb()
        source = make_source(db=db)
        await source.update(7, {"name": "Ada", "id": "ignored"})
        sql = db.fetch_one.await_args.args[0]
        assert 'UPDATE "users"' in sql
        assert '"name" = $1' in sql
        assert '"id" = $2' in sql
        assert db.fetch_one.await_args.args[1] == ["Ada", 7]
