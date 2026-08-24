"""Schema and query-building tests for SqlAuditStore."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lexigram.audit.store.sql import SqlAuditStore
from lexigram.contracts.audit import AuditQuery


class MockResult:
    """Mock query result."""
    def __init__(self, success: bool = True, rows: list = None):
        self.success = success
        self.rows = rows or []


class MockDeleteResult:
    """Mock delete result."""
    def __init__(self, success: bool = True, affected_rows: int = 0):
        self.success = success
        self.affected_rows = affected_rows


class MockConfig:
    """Mock audit config."""
    def __init__(self, table_name: str = "audit_log", hmac_key: str | None = None):
        self.table_name = table_name
        self.hmac_key = hmac_key.encode() if hmac_key else None


class MockDb:
    """Mock database provider."""
    def __init__(self, url: str = "sqlite://", should_fail: bool = False):
        self.url = url
        self.should_fail = should_fail
        self.executed_queries = []
        self.rows = []
        self.affected_rows = 0

    async def execute_query(self, sql: str, params: list = None):
        self.executed_queries.append((sql, params))
        if self.should_fail:
            return MockResult(success=False)
        return MockResult(success=True, rows=self.rows)

    async def execute_delete(self, table: str, where_clause: str, where_params: list = None):
        self.executed_queries.append((f"DELETE FROM {table} WHERE {where_clause}", where_params))
        if self.should_fail:
            return MockDeleteResult(success=False, affected_rows=0)
        return MockDeleteResult(success=True, affected_rows=self.affected_rows)


class TestSqlAuditStoreSchema:
    """Tests for SqlAuditStore schema creation."""

    @pytest.fixture
    def mock_db(self) -> MockDb:
        return MockDb()

    @pytest.fixture
    def mock_config(self) -> MockConfig:
        return MockConfig()

    @pytest.mark.asyncio
    async def test_store_creation(self, mock_db: MockDb, mock_config: MockConfig) -> None:
        store = SqlAuditStore(db=mock_db, config=mock_config)
        assert store._db is mock_db
        assert store._table == "audit_log"

    @pytest.mark.asyncio
    async def test_initialize_creates_table(self, mock_db: MockDb, mock_config: MockConfig) -> None:
        store = SqlAuditStore(db=mock_db, config=mock_config)
        await store.initialize()

        assert len(mock_db.executed_queries) > 0
        create_queries = [q for q in mock_db.executed_queries if "CREATE TABLE" in q[0]]
        assert len(create_queries) > 0


class TestSqlAuditStoreBuildWhere:
    """Tests for _build_where method."""

    @pytest.fixture
    def store(self) -> SqlAuditStore:
        db = MockDb()
        config = MockConfig()
        return SqlAuditStore(db=db, config=config)

    def test_build_where_empty_query(self, store: SqlAuditStore) -> None:
        query = AuditQuery(limit=10, offset=0)
        conditions, params = store._build_where(query)
        assert conditions == []
        assert params == []

    def test_build_where_actor_id(self, store: SqlAuditStore) -> None:
        query = AuditQuery(actor_id="user-1", limit=10, offset=0)
        conditions, params = store._build_where(query)
        assert "changed_by = ?" in conditions
        assert "user-1" in params

    def test_build_where_action(self, store: SqlAuditStore) -> None:
        query = AuditQuery(action="user.login", limit=10, offset=0)
        conditions, params = store._build_where(query)
        assert "action = ?" in conditions
        assert "user.login" in params

    def test_build_where_resource_type(self, store: SqlAuditStore) -> None:
        query = AuditQuery(resource_type="User", limit=10, offset=0)
        conditions, params = store._build_where(query)
        assert "table_name = ?" in conditions
        assert "User" in params

    def test_build_where_multiple_filters(self, store: SqlAuditStore) -> None:
        query = AuditQuery(
            actor_id="user-1",
            action="user.login",
            resource_type="User",
            limit=10,
            offset=0,
        )
        conditions, params = store._build_where(query)
        assert len(conditions) == 3


class TestSqlAuditStoreRowToEntry:
    """Tests for _row_to_entry method."""

    @pytest.fixture
    def store(self) -> SqlAuditStore:
        db = MockDb()
        config = MockConfig()
        return SqlAuditStore(db=db, config=config)

    def test_row_to_entry_basic(self, store: SqlAuditStore) -> None:
        row = {
            "action": "user.login",
            "changed_by": "user-1",
            "table_name": "User",
            "entity_id": "user-1",
            "outcome": "success",
            "severity": "high",
            "changed_at": datetime.now(UTC).isoformat(),
            "metadata": "{}",
            "old_values": None,
            "new_values": None,
            "source": "api",
            "tenant_id": "tenant-1",
        }
        entry = store._row_to_entry(row)
        assert entry.action == "user.login"
        assert entry.actor_id == "user-1"
        assert entry.resource_type == "User"

    def test_row_to_entry_with_json_metadata(self, store: SqlAuditStore) -> None:
        row = {
            "action": "test",
            "changed_by": "user",
            "table_name": "",
            "entity_id": "",
            "outcome": "success",
            "severity": "medium",
            "changed_at": datetime.now(UTC).isoformat(),
            "metadata": '{"key": "value"}',
            "old_values": '{"old": "value"}',
            "new_values": '{"new": "value"}',
            "source": None,
            "tenant_id": None,
        }
        entry = store._row_to_entry(row)
        assert entry.metadata == {"key": "value"}
        assert entry.old_values == {"old": "value"}
        assert entry.new_values == {"new": "value"}

    def test_row_to_entry_default_severity(self, store: SqlAuditStore) -> None:
        row = {
            "action": "test",
            "changed_by": "user",
            "table_name": "",
            "entity_id": "",
            "outcome": "success",
            "severity": None,
            "changed_at": datetime.now(UTC).isoformat(),
            "metadata": "{}",
            "old_values": None,
            "new_values": None,
            "source": None,
            "tenant_id": None,
        }
        entry = store._row_to_entry(row)
        assert entry.severity is not None

    def test_row_to_entry_preserves_checksum(self, store: SqlAuditStore) -> None:
        row = {
            "action": "user.login",
            "changed_by": "user-1",
            "table_name": "User",
            "entity_id": "user-1",
            "outcome": "success",
            "severity": "medium",
            "changed_at": datetime.now(UTC).isoformat(),
            "metadata": "{}",
            "old_values": None,
            "new_values": None,
            "source": None,
            "tenant_id": None,
            "checksum": "abcd1234ef567890",
        }
        entry = store._row_to_entry(row)
        assert entry.checksum == "abcd1234ef567890"
