from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from lexigram import serialization as json
from lexigram.ai.governance.audit.models import (
    AIAuditEvent,
    AuditEventType,
    AuditQuery,
    AuditSummary,
)
from lexigram.contracts.audit import AuditEntry, AuditEventSeverity

if TYPE_CHECKING:
    from lexigram.contracts.audit import AuditLoggerProtocol
    from lexigram.contracts.data import DatabaseProviderProtocol

_PII_METADATA_KEYS = frozenset(
    {"prompt", "message", "content", "query", "text", "input", "output", "response"}
)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ai_audit_events (
    event_id    TEXT    NOT NULL PRIMARY KEY,
    event_type  TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL,
    model       TEXT,
    provider    TEXT,
    user_id     TEXT,
    status      TEXT    NOT NULL DEFAULT 'success',
    tokens      INTEGER,
    cost        REAL,
    latency_ms  REAL,
    metadata    TEXT    NOT NULL DEFAULT '{}'
)
"""

_INSERT_EVENT = (
    "INSERT OR IGNORE INTO ai_audit_events "
    "(event_id, event_type, timestamp, model, provider, user_id, "
    "status, tokens, cost, latency_ms, metadata) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def _sanitize_metadata(metadata: dict[str, Any]) -> str:
    """Redact PII-sensitive keys and serialise to JSON for storage."""
    safe: dict[str, Any] = {}
    for k, v in metadata.items():
        safe[k] = "[REDACTED]" if k.lower() in _PII_METADATA_KEYS else v
    return json.dumps_str(safe)


class DatabaseAuditStore:
    """SQL-backed audit store using :class:`~lexigram.contracts.data.DatabaseProviderProtocol`.

    Writes events to an ``ai_audit_events`` table (created lazily on first
    use).  Metadata fields matching common PII keys (``prompt``, ``content``,
    ``message``, etc.) are redacted to ``"[REDACTED]"`` before storage.

    ``record()`` is safe to call from hot-paths — it issues a single
    ``INSERT OR IGNORE`` that will not raise on duplicate ``event_id``.

    Args:
        db: A connected :class:`~lexigram.contracts.data.DatabaseProviderProtocol`
            resolved from the DI container.
    """

    def __init__(
        self,
        db: DatabaseProviderProtocol,
        audit_logger: AuditLoggerProtocol | None = None,
    ) -> None:
        self._db = db
        self._audit_logger = audit_logger
        self._initialised = False

    async def _ensure_table(self) -> None:
        if not self._initialised:
            await self._db.execute(_CREATE_TABLE)
            self._initialised = True

    async def record(self, event: AIAuditEvent) -> None:
        """Persist *event* to the database, sanitising PII in metadata.

        Args:
            event: The audit event to store.
        """
        await self._ensure_table()
        await self._db.execute(
            _INSERT_EVENT,
            [
                event.event_id,
                event.event_type.value,
                event.timestamp.isoformat(),
                event.model,
                event.provider,
                event.user_id,
                event.status,
                event.tokens,
                event.cost,
                event.latency_ms,
                _sanitize_metadata(event.metadata),
            ],
        )
        if self._audit_logger is not None:
            meta: dict[str, Any] = {"model": event.model, "provider": event.provider}
            if event.tokens is not None:
                meta["tokens"] = event.tokens
            if event.cost is not None:
                meta["cost"] = event.cost
            await self._audit_logger.log(
                AuditEntry(
                    action=f"ai.{event.event_type.value}",
                    actor_id=event.user_id or "system",
                    resource_type="ai_inference",
                    resource_id=event.event_id,
                    outcome=event.status,
                    severity=AuditEventSeverity.MEDIUM,
                    metadata=meta,
                    source="ai_governance",
                )
            )

    async def query(self, query: AuditQuery) -> list[AIAuditEvent]:
        """Retrieve audit events matching *query*, newest first.

        Args:
            query: Filter criteria.

        Returns:
            Matching events ordered by timestamp descending.
        """
        await self._ensure_table()
        sql, params = self._build_where(query)
        full_sql = (
            f"SELECT * FROM ai_audit_events{sql} "
            f"ORDER BY timestamp DESC "
            f"LIMIT ? OFFSET ?"
        )
        result = await self._db.execute_query(
            full_sql, [*params, query.limit, query.offset]
        )
        return [self._row_to_event(row) for row in result.rows]

    async def aggregate(self, query: AuditQuery) -> AuditSummary:
        """Compute summary statistics for events matching *query*.

        Executes four targeted SQL queries (totals + three GROUP BY) so that
        callers do not need to load full event rows into memory.

        Args:
            query: Filter criteria that scope the aggregation.

        Returns:
            Summary statistics for the matching events.
        """
        await self._ensure_table()
        where, base_params = self._build_where(query)

        # -- totals ---------------------------------------------------------
        totals_sql = (
            "SELECT COUNT(*) AS total_events, "
            "COALESCE(SUM(cost), 0.0) AS total_spend, "
            "COALESCE(SUM(tokens), 0) AS total_tokens, "
            "SUM(CASE WHEN status = 'denied' THEN 1 ELSE 0 END) AS denied_count "
            f"FROM ai_audit_events{where}"
        )
        totals_result = await self._db.execute_query(totals_sql, base_params)
        row = totals_result.rows[0] if totals_result.rows else {}
        summary = AuditSummary(
            total_events=int(row.get("total_events", 0)),
            total_spend=float(row.get("total_spend", 0.0)),
            total_tokens=int(row.get("total_tokens", 0)),
            denied_count=int(row.get("denied_count", 0)),
        )

        # -- by model -------------------------------------------------------
        model_result = await self._db.execute_query(
            f"SELECT COALESCE(model, 'unknown') AS grp, COUNT(*) AS cnt "
            f"FROM ai_audit_events{where} GROUP BY model",
            base_params,
        )
        summary.by_model = {r["grp"]: int(r["cnt"]) for r in model_result.rows}

        # -- by user --------------------------------------------------------
        user_result = await self._db.execute_query(
            f"SELECT COALESCE(user_id, 'anonymous') AS grp, COUNT(*) AS cnt "
            f"FROM ai_audit_events{where} GROUP BY user_id",
            base_params,
        )
        summary.by_user = {r["grp"]: int(r["cnt"]) for r in user_result.rows}

        # -- by event type --------------------------------------------------
        type_result = await self._db.execute_query(
            f"SELECT event_type AS grp, COUNT(*) AS cnt "
            f"FROM ai_audit_events{where} GROUP BY event_type",
            base_params,
        )
        summary.by_event_type = {r["grp"]: int(r["cnt"]) for r in type_result.rows}

        return summary

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _build_where(self, query: AuditQuery) -> tuple[str, list[Any]]:
        """Build a parameterised WHERE clause from *query* filter criteria."""
        clauses: list[str] = []
        params: list[Any] = []

        if query.start:
            clauses.append("timestamp >= ?")
            params.append(query.start.isoformat())
        if query.end:
            clauses.append("timestamp <= ?")
            params.append(query.end.isoformat())
        if query.user_id:
            clauses.append("user_id = ?")
            params.append(query.user_id)
        if query.model:
            clauses.append("model = ?")
            params.append(query.model)
        if query.provider:
            clauses.append("provider = ?")
            params.append(query.provider)
        if query.status:
            clauses.append("status = ?")
            params.append(query.status)
        if query.event_types:
            placeholders = ", ".join("?" * len(query.event_types))
            clauses.append(f"event_type IN ({placeholders})")
            params.extend(et.value for et in query.event_types)

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        return where, params

    @staticmethod
    def _row_to_event(row: Any) -> AIAuditEvent:
        """Deserialise a database row into an :class:`AIAuditEvent`."""
        raw_meta = row.get("metadata", "{}")
        try:
            meta = json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta
        except (ValueError, TypeError):
            meta = {}

        return AIAuditEvent(
            event_id=row["event_id"],
            event_type=AuditEventType(row["event_type"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            model=row.get("model"),
            provider=row.get("provider"),
            user_id=row.get("user_id"),
            status=row.get("status", "success"),
            tokens=row.get("tokens"),
            cost=row.get("cost"),
            latency_ms=row.get("latency_ms"),
            metadata=meta,
        )
