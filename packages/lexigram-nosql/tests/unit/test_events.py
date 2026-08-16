from __future__ import annotations

import pytest

from lexigram.nosql.events import (
    MigrationAppliedEvent,
    MigrationFailedEvent,
    NoSQLConnectedEvent,
    NoSQLDisconnectedEvent,
)


class TestMigrationAppliedEvent:
    def test_creation(self) -> None:
        event = MigrationAppliedEvent(migration_name="v1", database="mydb")
        assert event.migration_name == "v1"
        assert event.database == "mydb"

    def test_is_frozen(self) -> None:
        event = MigrationAppliedEvent(migration_name="v2", database="mydb")
        with pytest.raises(AttributeError):
            event.migration_name = "v3"  # type: ignore[misc]


class TestMigrationFailedEvent:
    def test_creation(self) -> None:
        event = MigrationFailedEvent(migration_name="v1", database="mydb", error="timeout")
        assert event.migration_name == "v1"
        assert event.database == "mydb"
        assert event.error == "timeout"


class TestNoSQLConnectedEvent:
    def test_creation(self) -> None:
        event = NoSQLConnectedEvent(database="mydb", host="localhost")
        assert event.database == "mydb"
        assert event.host == "localhost"


class TestNoSQLDisconnectedEvent:
    def test_creation(self) -> None:
        event = NoSQLDisconnectedEvent(database="mydb")
        assert event.database == "mydb"
