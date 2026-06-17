"""SQL-backed audit store using DatabaseProviderProtocol."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lexigram import serialization as json
from lexigram.audit.config import AuditConfig
from lexigram.audit.verification.checksum import compute_audit_checksum
from lexigram.contracts.audit import AuditEntry, AuditEventSeverity, AuditQuery
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.logging import get_logger

__all__ = ["SqlAuditStore"]

logger = get_logger(__name__)


def _as_utc_naive(dt: datetime) -> datetime:
    """Return the timestamp as a naive **UTC** datetime for TIMESTAMP columns.

    The audit table declares ``changed_at TIMESTAMP`` (no time zone), so
    aware datetimes must be converted to UTC and stripped of tzinfo before
    binding — asyncpg rejects aware values against TIMESTAMP columns.
    """
    return dt.replace(tzinfo=None) if dt.tzinfo is None else dt.astimezone(UTC).replace(tzinfo=None)


class SqlAuditStore:
    """SQL-backed audit store implementing AuditStoreProtocol.

    Persists audit entries to a relational database via
    DatabaseProviderProtocol. Supports optional HMAC-SHA256 checksums
    when an HMAC key is configured.

    Args:
        db: Database provider for executing queries.
        config: Audit configuration containing table name and HMAC key.
    """

    def __init__(self, db: DatabaseProviderProtocol, config: AuditConfig) -> None:
        self._db = db
        self._hmac_key = config.hmac_key
        self._table = config.table_name

    async def initialize(self) -> None:
        """Create the audit log table and indexes if they do not exist."""
        pk_type = "INTEGER PRIMARY KEY AUTOINCREMENT"

        db_url = str(getattr(self._db, "url", "")).lower()
        if (
            "postgres" in db_url
            or "postgresql" in db_url
            or "Postgres" in self._db.__class__.__name__
        ):
            pk_type = "SERIAL PRIMARY KEY"

        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {self._table} (
            id {pk_type},
            table_name VARCHAR(255) NOT NULL,
            entity_id VARCHAR(255) NOT NULL,
            action VARCHAR(50) NOT NULL,
            old_values TEXT,
            new_values TEXT,
            changed_by VARCHAR(255),
            changed_at TIMESTAMP NOT NULL,
            metadata TEXT,
            checksum VARCHAR(64),
            severity VARCHAR(20),
            source VARCHAR(100),
            outcome VARCHAR(50),
            tenant_id VARCHAR(255),
            correlation_id VARCHAR(255),
            causation_id VARCHAR(255),
            command_payload_hash VARCHAR(64),
            payload_size_bytes INTEGER,
            entry_schema_version INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_audit_table_entity ON {self._table}(table_name, entity_id);
        CREATE INDEX IF NOT EXISTS idx_audit_changed_at ON {self._table}(changed_at);
        CREATE INDEX IF NOT EXISTS idx_audit_checksum ON {self._table}(checksum);
        CREATE INDEX IF NOT EXISTS idx_audit_tenant_occurred ON {self._table}(tenant_id, changed_at);
        CREATE INDEX IF NOT EXISTS idx_audit_correlation ON {self._table}(correlation_id)
        """

        statements = [s.strip() for s in create_sql.split(";") if s.strip()]
        for stmt in statements:
            await self._db.execute_query(stmt)

    async def append(self, entry: AuditEntry) -> None:
        """Persist a single audit entry to the database.

        Computes an HMAC-SHA256 checksum when an HMAC key is configured.

        Args:
            entry: The audit event to store.
        """
        row: dict[str, Any] = {
            "table_name": entry.resource_type,
            "entity_id": str(entry.resource_id),
            "action": entry.action,
            "old_values": json.dumps_str(entry.old_values or {}),
            "new_values": json.dumps_str(entry.new_values or {}),
            "changed_by": entry.actor_id,
            "changed_at": _as_utc_naive(entry.occurred_at),
            "metadata": json.dumps_str(entry.metadata),
            "severity": str(entry.severity) if entry.severity else None,
            "source": entry.source or None,
            "outcome": entry.outcome or None,
            "tenant_id": entry.tenant_id,
            "correlation_id": correlation_id
            if isinstance(correlation_id := getattr(entry, "correlation_id", None), str)
            else None,
            "causation_id": causation_id
            if isinstance(causation_id := getattr(entry, "causation_id", None), str)
            else None,
            "command_payload_hash": cmd_hash.hex()
            if isinstance(
                cmd_hash := getattr(entry, "command_payload_hash", None), bytes
            )
            else None,
            "payload_size_bytes": payload_size
            if isinstance(
                payload_size := getattr(entry, "payload_size_bytes", None), int
            )
            else None,
            "entry_schema_version": getattr(entry, "schema_version", 1),
        }

        checksum: str | None = None
        if self._hmac_key:
            checksum = compute_audit_checksum(row, self._hmac_key)
        row["checksum"] = checksum

        sql = (
            f"INSERT INTO {self._table} "
            "(table_name, entity_id, action, old_values, new_values, "
            "changed_by, changed_at, metadata, checksum, severity, source, outcome, "
            "tenant_id, correlation_id, causation_id, command_payload_hash, payload_size_bytes, entry_schema_version) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        params = [
            row["table_name"],
            row["entity_id"],
            row["action"],
            row["old_values"],
            row["new_values"],
            row["changed_by"],
            row["changed_at"],
            row["metadata"],
            row["checksum"],
            row["severity"],
            row["source"],
            row["outcome"],
            row["tenant_id"],
            row["correlation_id"],
            row["causation_id"],
            row["command_payload_hash"],
            row["payload_size_bytes"],
            row["entry_schema_version"],
        ]
        await self._db.execute_query(sql, params)

    async def query(self, query: AuditQuery) -> list[AuditEntry]:
        """Retrieve entries matching filters, newest-first.

        Args:
            query: Filter criteria.

        Returns:
            List of matching audit entries.
        """
        conditions, params = self._build_where(query)
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = (
            f"SELECT * FROM {self._table} "
            f"WHERE {where_clause} "
            f"ORDER BY changed_at DESC "
            f"LIMIT ? OFFSET ?"
        )
        params.extend([query.limit, query.offset])

        result = await self._db.execute_query(sql, params)
        if result.success:
            return [self._row_to_entry(row) for row in result.rows]
        return []

    async def count(self, query: AuditQuery) -> int:
        """Return count of entries matching filters.

        Args:
            query: Filter criteria.

        Returns:
            Number of matching entries.
        """
        conditions, params = self._build_where(query)
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT COUNT(*) as count FROM {self._table} WHERE {where_clause}"

        result = await self._db.execute_query(sql, params)
        if result.success and result.rows:
            return int(result.rows[0].get("count", 0))
        return 0

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_where(self, query: AuditQuery) -> tuple[list[str], list[Any]]:
        """Build WHERE conditions and parameter list from an AuditQuery.

        Args:
            query: Filter criteria object.

        Returns:
            Tuple of (conditions list, params list).
        """
        conditions: list[str] = []
        params: list[Any] = []

        if query.actor_id is not None:
            conditions.append("changed_by = ?")
            params.append(query.actor_id)
        if query.action is not None:
            conditions.append("action = ?")
            params.append(query.action)
        if query.resource_type is not None:
            conditions.append("table_name = ?")
            params.append(query.resource_type)
        if query.resource_id is not None:
            conditions.append("entity_id = ?")
            params.append(str(query.resource_id))
        if query.source is not None:
            conditions.append("source = ?")
            params.append(query.source)
        if query.severity is not None:
            conditions.append("severity = ?")
            params.append(str(query.severity))
        if query.outcome is not None:
            conditions.append("outcome = ?")
            params.append(query.outcome)
        if query.correlation_id is not None:
            conditions.append("correlation_id = ?")
            params.append(query.correlation_id)
        if query.tenant_id is not None:
            conditions.append("tenant_id = ?")
            params.append(query.tenant_id)
        if query.since is not None:
            conditions.append("changed_at >= ?")
            params.append(_as_utc_naive(query.since))
        if query.until is not None:
            conditions.append("changed_at <= ?")
            params.append(_as_utc_naive(query.until))

        return conditions, params

    def _row_to_entry(self, row: dict[str, Any]) -> AuditEntry:
        """Hydrate an AuditEntry from a database row dict.

        Args:
            row: Raw database row dictionary.

        Returns:
            Populated AuditEntry instance.
        """
        changed_at = row.get("changed_at")
        if isinstance(changed_at, datetime):
            ts = changed_at
        elif changed_at:
            ts = datetime.fromisoformat(str(changed_at))
        else:
            ts = datetime.now(UTC)

        old_raw = row.get("old_values")
        new_raw = row.get("new_values")
        meta_raw = row.get("metadata")

        severity_raw = row.get("severity")
        severity: AuditEventSeverity
        try:
            severity = (
                AuditEventSeverity(severity_raw)
                if severity_raw
                else AuditEventSeverity.MEDIUM
            )
        except ValueError:
            severity = AuditEventSeverity.MEDIUM

        cmd_hash_raw = row.get("command_payload_hash")
        command_payload_hash: bytes | None = None
        if cmd_hash_raw:
            try:
                command_payload_hash = bytes.fromhex(str(cmd_hash_raw))
            except (ValueError, TypeError):
                command_payload_hash = None

        return AuditEntry(
            action=row.get("action", ""),
            actor_id=row.get("changed_by") or "",
            resource_type=row.get("table_name") or "",
            resource_id=str(row.get("entity_id") or ""),
            outcome=row.get("outcome") or "success",
            severity=severity,
            occurred_at=ts,
            metadata=json.loads_str(meta_raw) if meta_raw else {},
            old_values=json.loads_str(old_raw) if old_raw else None,
            new_values=json.loads_str(new_raw) if new_raw else None,
            source=row.get("source") or "",
            tenant_id=row.get("tenant_id"),
            correlation_id=row.get("correlation_id"),
            causation_id=row.get("causation_id"),
            command_payload_hash=command_payload_hash,
            payload_size_bytes=row.get("payload_size_bytes"),
        )
