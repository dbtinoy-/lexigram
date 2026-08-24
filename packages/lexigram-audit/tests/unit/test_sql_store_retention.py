"""Retention / expiry tests for SqlAuditStore."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lexigram.audit.store.sql import SqlAuditStore


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


class TestSqlAuditStoreRetention:
    """Tests for SqlAuditStore delete_expired."""

    @pytest.fixture
    def mock_db(self) -> MockDb:
        return MockDb()

    @pytest.fixture
    def mock_config(self) -> MockConfig:
        return MockConfig()

    @pytest.mark.asyncio
    async def test_delete_expired_issues_single_bulk_delete(self, mock_db: MockDb, mock_config: MockConfig) -> None:
        mock_db.affected_rows = 3
        store = SqlAuditStore(db=mock_db, config=mock_config)
        cutoff = datetime.now(UTC)

        deleted = await store.delete_expired(cutoff)

        assert deleted == 3
        assert len(mock_db.executed_queries) == 1
        sql, params = mock_db.executed_queries[0]
        assert sql.startswith("DELETE FROM audit_log WHERE ")
        assert "json_extract(metadata, '$.__expires_at')" in sql
        assert params == [cutoff.isoformat()]

    @pytest.mark.asyncio
    async def test_delete_expired_uses_jsonb_dialect_for_postgres(self, mock_config: MockConfig) -> None:
        db = MockDb(url="postgresql://localhost/audit")
        db.affected_rows = 2
        store = SqlAuditStore(db=db, config=mock_config)

        deleted = await store.delete_expired(datetime.now(UTC))

        assert deleted == 2
        sql, _ = db.executed_queries[0]
        assert "metadata::jsonb->>'__expires_at'" in sql
        assert "::timestamptz" in sql

    @pytest.mark.asyncio
    async def test_delete_expired_returns_zero_on_backend_failure(self, mock_config: MockConfig) -> None:
        db = MockDb(should_fail=True)
        db.affected_rows = 5
        store = SqlAuditStore(db=db, config=mock_config)

        deleted = await store.delete_expired(datetime.now(UTC))

        assert deleted == 0
