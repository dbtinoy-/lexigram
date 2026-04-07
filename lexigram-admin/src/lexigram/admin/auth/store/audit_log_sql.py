from __future__ import annotations

"""SQL-backed implementation of AdminAuditLogStoreProtocol.

This is the *only* module in ``lexigram-admin`` that issues raw SQL against
the ``admin_security_audit_log`` table.  The audit service layer depends on
the ``AdminAuditLogStoreProtocol`` protocol and never on this class directly.
"""

from datetime import datetime
from typing import Any
import uuid

from lexigram.admin.auth.types import AdminSecurityEvent, AdminSecurityEventType
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.serialization import dumps_str, loads_str

logger = get_logger(__name__)

_TABLE = "admin_security_audit_log"

_CREATE_TABLE_SQL = f"""
    CREATE TABLE IF NOT EXISTS {_TABLE} (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        event_type  VARCHAR(50) NOT NULL,
        admin_user_id UUID,
        ip_address  VARCHAR(45) NOT NULL,
        user_agent  TEXT NOT NULL DEFAULT '',
        success     BOOLEAN NOT NULL DEFAULT FALSE,
        metadata    TEXT NOT NULL DEFAULT '{{}}',
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
"""

_CREATE_INDEX_CREATED_AT = (
    f"CREATE INDEX IF NOT EXISTS idx_admin_audit_log_created_at"
    f" ON {_TABLE}(created_at DESC)"
)

_CREATE_INDEX_USER_ID = (
    f"CREATE INDEX IF NOT EXISTS idx_admin_audit_log_admin_user_id"
    f" ON {_TABLE}(admin_user_id, created_at DESC) WHERE admin_user_id IS NOT NULL"
)

_CREATE_INDEX_EVENT_TYPE = (
    f"CREATE INDEX IF NOT EXISTS idx_admin_audit_log_event_type"
    f" ON {_TABLE}(event_type, created_at DESC)"
)


@inject
class AdminAuditLogSqlStore:
    """SQL implementation of AdminAuditLogStoreProtocol.

    Stores security audit events in the ``admin_security_audit_log`` table.
    All operations are fire-tolerant — exceptions are logged but never
    re-raised from ``insert()`` since audit failure must not block
    authentication.

    Implements ``AdminAuditLogStoreProtocol`` via structural subtyping.
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        """Initialize with a resolved database provider.

        Args:
            db: Framework database provider that exposes ``execute``,
                ``execute_query``, and ``execute_insert``.
        """
        self._db = db
        self._initialized = False

    # ------------------------------------------------------------------
    # Schema bootstrap (DDL)
    # ------------------------------------------------------------------

    async def ensure_schema(self) -> None:
        """Create the audit log table and indexes if they do not exist.

        Safe to call multiple times — idempotent after the first successful
        run.  Raises on any unexpected DDL failure so callers surface the
        problem rather than silently skipping audit persistence.
        """
        if self._initialized:
            return

        try:
            await self._db.execute(_CREATE_TABLE_SQL, [])
            logger.info("✅ %s table ensured", _TABLE)

            for index_sql in (
                _CREATE_INDEX_CREATED_AT,
                _CREATE_INDEX_USER_ID,
                _CREATE_INDEX_EVENT_TYPE,
            ):
                try:
                    await self._db.execute(index_sql, [])
                except (RuntimeError, ValueError, OSError) as exc:
                    logger.debug("Index creation skipped: %s", exc)

            logger.info("✅ %s indexes ensured", _TABLE)
            self._initialized = True

        except Exception:  # noqa: BLE001 — schema DDL may raise DB-specific errors; log and propagate
            logger.exception("Failed to initialise %s schema", _TABLE)
            raise

    # ------------------------------------------------------------------
    # AdminAuditLogStoreProtocol implementation
    # ------------------------------------------------------------------

    async def insert(self, event: AdminSecurityEvent) -> None:
        """Persist a security audit event.

        This method **never raises** — exceptions are caught and logged at
        warning level.  Audit failure must never block the authentication flow.

        Args:
            event: Security event to store.
        """
        await self.ensure_schema()

        try:
            payload = {
                "id": uuid.UUID(event.id) if _is_uuid_string(event.id) else event.id,
                "event_type": event.event_type.value,
                "admin_user_id": (
                    uuid.UUID(event.admin_user_id)
                    if event.admin_user_id and _is_uuid_string(event.admin_user_id)
                    else event.admin_user_id
                ),
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "success": event.success,
                "metadata": dumps_str(event.metadata),
                "created_at": event.created_at,
            }
            await self._db.execute_insert(_TABLE, payload)
            logger.debug(
                "audit_log.inserted",
                event_id=event.id,
                event_type=event.event_type.value,
                admin_user_id=event.admin_user_id,
            )

        except Exception as exc:  # noqa: BLE001 — audit insert must never surface errors to callers
            logger.warning(
                "audit_log.insert_failed",
                event_id=event.id,
                event_type=event.event_type.value,
                error=str(exc),
            )

    async def query_recent(
        self,
        admin_user_id: str | None = None,
        event_type: AdminSecurityEventType | None = None,
        since_seconds: int = 3600,
        limit: int = 100,
    ) -> list[AdminSecurityEvent]:
        """Query recent security events with optional filters.

        Args:
            admin_user_id: Filter to a specific user (``None`` = all users).
            event_type: Filter to a specific event type (``None`` = all types).
            since_seconds: Look-back window in seconds.
            limit: Maximum number of records to return.

        Returns:
            List of ``AdminSecurityEvent`` instances ordered newest first.
        """
        await self.ensure_schema()

        # ``since_seconds`` is always an int — safe to interpolate directly.
        conditions = [f"created_at > NOW() - INTERVAL '{int(since_seconds)} seconds'"]
        params: list[Any] = []

        if admin_user_id is not None:
            params.append(
                uuid.UUID(admin_user_id)
                if _is_uuid_string(admin_user_id)
                else admin_user_id
            )
            conditions.append("admin_user_id = ?")

        if event_type is not None:
            params.append(event_type.value)
            conditions.append("event_type = ?")

        where_clause = " AND ".join(conditions)
        sql = (
            f"SELECT id, event_type, admin_user_id, ip_address, user_agent,"
            f" success, metadata, created_at"
            f" FROM {_TABLE}"
            f" WHERE {where_clause}"
            f" ORDER BY created_at DESC"
            f" LIMIT {int(limit)}"
        )

        try:
            result = await self._db.execute_query(sql, params)
            rows = _extract_rows(result)
            return [_row_to_event(row) for row in rows]

        except Exception as exc:  # noqa: BLE001 — query failures must not crash callers; return empty list
            logger.warning(
                "audit_log.query_failed",
                since_seconds=since_seconds,
                admin_user_id=admin_user_id,
                event_type=event_type.value if event_type else None,
                error=str(exc),
            )
            return []


# ------------------------------------------------------------------
# Module-private helpers
# ------------------------------------------------------------------


def _is_uuid_string(value: str) -> bool:
    """Return ``True`` when *value* is a well-formed UUID string.

    Args:
        value: String to test.

    Returns:
        ``True`` if *value* parses as a UUID, ``False`` otherwise.
    """
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def _extract_rows(result: Any) -> list[Any]:
    """Normalise heterogeneous query result shapes into a plain list.

    Args:
        result: Raw return value from ``DatabaseProviderProtocol.execute_query``.

    Returns:
        Flat list of row-like objects (dicts or asyncpg ``Record`` instances).
    """
    if hasattr(result, "rows"):
        return list(result.rows)
    if isinstance(result, list):
        return result
    return []


def _row_to_event(row: Any) -> AdminSecurityEvent:
    """Construct an ``AdminSecurityEvent`` from a raw database row.

    Args:
        row: Row-like mapping returned by the database driver.

    Returns:
        Fully populated ``AdminSecurityEvent`` instance.
    """
    raw_user_id = row["admin_user_id"]
    raw_metadata = row["metadata"]
    raw_created_at = row["created_at"]

    # Coerce admin_user_id: UUID objects → str, None stays None.
    admin_user_id: str | None = str(raw_user_id) if raw_user_id is not None else None

    # Deserialise metadata stored as a JSON string.
    metadata: dict[str, str | int | bool | None] = loads_str(raw_metadata or "{}")

    # asyncpg returns timezone-aware datetimes; ensure we always have one.
    created_at: datetime = (
        raw_created_at
        if isinstance(raw_created_at, datetime)
        else datetime.fromisoformat(str(raw_created_at))
    )

    return AdminSecurityEvent(
        id=str(row["id"]),
        event_type=AdminSecurityEventType(row["event_type"]),
        admin_user_id=admin_user_id,
        ip_address=row["ip_address"],
        user_agent=row["user_agent"],
        success=bool(row["success"]),
        metadata=metadata,
        created_at=created_at,
    )


__all__ = ["AdminAuditLogSqlStore"]
