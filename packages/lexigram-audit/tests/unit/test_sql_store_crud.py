"""CRUD, redaction and checksum tests for SqlAuditStore."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from lexigram import serialization as json
from lexigram.audit.store.sql import SqlAuditStore, _as_utc_naive
from lexigram.audit.verification.checksum import compute_audit_checksum
from lexigram.contracts.audit import AuditQuery
from lexigram.logging.redaction import DefaultRedactor, get_redactor, set_redactor


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


def _make_entry(**overrides: object) -> MagicMock:
    """Build a MagicMock AuditEntry with sensible defaults."""
    entry = MagicMock()
    entry.resource_type = "User"
    entry.resource_id = "user-1"
    entry.action = "user.update"
    entry.old_values = None
    entry.new_values = None
    entry.actor_id = "admin-1"
    entry.occurred_at = datetime.now(UTC)
    entry.metadata = {}
    entry.severity = "medium"
    entry.source = None
    entry.outcome = "success"
    entry.tenant_id = None
    for k, v in overrides.items():
        setattr(entry, k, v)
    return entry


class TestSqlAuditStoreCRUD:
    """Tests for SqlAuditStore CRUD operations."""

    @pytest.fixture
    def mock_db(self) -> MockDb:
        return MockDb()

    @pytest.fixture
    def mock_config(self) -> MockConfig:
        return MockConfig()

    @pytest.mark.asyncio
    async def test_append_inserts_row(self, mock_db: MockDb, mock_config: MockConfig) -> None:
        store = SqlAuditStore(db=mock_db, config=mock_config)
        entry = MagicMock()
        entry.resource_type = "User"
        entry.resource_id = "user-1"
        entry.action = "user.login"
        entry.old_values = None
        entry.new_values = None
        entry.actor_id = "user-1"
        entry.occurred_at = datetime.now(UTC)
        entry.metadata = {}
        entry.severity = "medium"
        entry.source = None
        entry.outcome = "success"
        entry.tenant_id = None

        await store.append(entry)

        insert_queries = [q for q in mock_db.executed_queries if "INSERT INTO" in q[0]]
        assert len(insert_queries) > 0

    @pytest.mark.asyncio
    async def test_append_computes_checksum_when_key_set(self) -> None:
        db = MockDb()
        config = MockConfig(hmac_key="secret-key")
        store = SqlAuditStore(db=db, config=config)

        entry = MagicMock()
        entry.resource_type = "User"
        entry.resource_id = "user-1"
        entry.action = "user.login"
        entry.old_values = None
        entry.new_values = None
        entry.actor_id = "user-1"
        entry.occurred_at = datetime.now(UTC)
        entry.metadata = {}
        entry.severity = "medium"
        entry.source = None
        entry.outcome = "success"
        entry.tenant_id = None

        await store.append(entry)

        assert db.executed_queries

    @pytest.mark.asyncio
    async def test_query_returns_entries(self) -> None:
        db = MockDb()
        config = MockConfig()
        store = SqlAuditStore(db=db, config=config)

        db.rows = [
            {
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
            }
        ]

        results = await store.query(AuditQuery(limit=10))
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_count_returns_number(self) -> None:
        db = MockDb()
        config = MockConfig()
        store = SqlAuditStore(db=db, config=config)

        db.rows = [{"count": 42}]

        count = await store.count(AuditQuery(limit=10))
        assert count == 42

    @pytest.mark.asyncio
    async def test_count_handles_failure(self) -> None:
        db = MockDb(should_fail=True)
        config = MockConfig()
        store = SqlAuditStore(db=db, config=config)

        count = await store.count(AuditQuery(limit=10))
        assert count == 0


class TestSqlAuditStoreRedaction:
    """Write-path redaction: SqlAuditStore.append redacts through get_redactor()."""

    @pytest.fixture
    def mock_db(self) -> MockDb:
        return MockDb()

    @pytest.fixture
    def mock_config(self) -> MockConfig:
        return MockConfig()

    @pytest.fixture(autouse=True)
    def _framework_redactor(self) -> None:
        from lexigram.logging.redaction import _redactor_var

        token = set_redactor(DefaultRedactor())
        try:
            yield
        finally:
            _redactor_var.reset(token)

    def _persisted_payloads(self, db: MockDb) -> tuple[str, str, str]:
        """Return (old_values, new_values, metadata) JSON from the INSERT."""
        insert_queries = [
            q for q in db.executed_queries if "INSERT INTO" in q[0]
        ]
        assert insert_queries, "no INSERT executed"
        sql, params = insert_queries[0]
        return params[3], params[4], params[7]

    @pytest.mark.asyncio
    async def test_append_redacts_denylisted_keys(
        self, mock_db: MockDb, mock_config: MockConfig
    ) -> None:
        store = SqlAuditStore(db=mock_db, config=mock_config)
        entry = _make_entry(
            new_values={"password": "hunter2", "email": "a@b.c"},
            metadata={"token": "tok-1", "user": "bob"},
            old_values={"cleartext": "keep", "api_key": "k-xyz"},
        )

        await store.append(entry)

        old_persisted, new_persisted, meta_persisted = self._persisted_payloads(mock_db)
        assert '"<redacted>"' in new_persisted
        assert "hunter2" not in new_persisted
        assert "a@b.c" in new_persisted
        assert "tok-1" not in meta_persisted
        assert '"<redacted>"' in old_persisted
        assert "k-xyz" not in old_persisted

    @pytest.mark.asyncio
    async def test_append_checksum_validates_redacted_row(
        self, mock_db: MockDb, mock_config: MockConfig
    ) -> None:
        store = SqlAuditStore(db=mock_db, config=MockConfig(hmac_key="secret"))
        entry = _make_entry(
            new_values={"password": "hunter2", "email": "a@b.c"},
            old_values={"api_key": "k-1"},
            metadata={"user": "bob"},
        )
        await store.append(entry)

        insert_queries = [q for q in mock_db.executed_queries if "INSERT INTO" in q[0]]
        assert insert_queries
        sql, params = insert_queries[0]

        redactor = get_redactor()
        redacted_row = {
            "table_name": entry.resource_type,
            "entity_id": str(entry.resource_id),
            "action": entry.action,
            "old_values": json.dumps_str(redactor.redact_dict(entry.old_values)),
            "new_values": json.dumps_str(redactor.redact_dict(entry.new_values)),
            "changed_by": entry.actor_id,
            "changed_at": _as_utc_naive(entry.occurred_at),
            "metadata": json.dumps_str(redactor.redact_dict(entry.metadata)),
            "severity": str(entry.severity) if entry.severity else None,
            "source": None,
            "outcome": "success",
            "tenant_id": None,
            "correlation_id": None,
            "causation_id": None,
            "command_payload_hash": None,
            "payload_size_bytes": None,
            "entry_schema_version": 1,
        }
        expected = compute_audit_checksum(redacted_row, b"secret")
        assert params[8] == expected
        assert "<redacted>" in params[4]
        assert "hunter2" not in params[4]
        assert "k-1" not in params[3]


class TestSqlAuditStoreChecksumRoundTrip:
    """Append must write the checksum; query must read it back."""

    @pytest.mark.asyncio
    async def test_append_then_read_back_preserves_checksum(self) -> None:
        db = MockDb()
        store = SqlAuditStore(db=db, config=MockConfig(hmac_key="secret"))
        entry = _make_entry()

        await store.append(entry)

        insert_queries = [q for q in db.executed_queries if "INSERT INTO" in q[0]]
        assert insert_queries
        _, params = insert_queries[0]
        stored_checksum = params[8]
        assert stored_checksum

        db.rows = [
            {
                "id": 1,
                "action": entry.action,
                "changed_by": entry.actor_id,
                "table_name": entry.resource_type,
                "entity_id": str(entry.resource_id),
                "outcome": entry.outcome,
                "severity": str(entry.severity),
                "changed_at": entry.occurred_at.isoformat(),
                "metadata": params[7],
                "old_values": params[3],
                "new_values": params[4],
                "source": None,
                "tenant_id": None,
                "checksum": stored_checksum,
                "entry_schema_version": 1,
            }
        ]
        results = await store.query(AuditQuery(limit=10))
        assert len(results) == 1
        assert results[0].checksum == stored_checksum
