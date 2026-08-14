"""SQL-backed implementation of SessionRepositoryProtocol for admin sessions.

This is the *only* module in ``lexigram-admin`` that issues raw SQL against
the ``admin_sessions`` table.  The session-management service layer depends
on the ``SessionRepositoryProtocol`` protocol from ``lexigram-contracts`` and never
on this class directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.data import DatabaseProviderProtocol, Table
from lexigram.serialization import dumps_str, loads_str

if TYPE_CHECKING:
    from datetime import datetime

from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class AdminSessionSqlRepository:
    """SQL-backed repository for admin session persistence.

    Owns all DDL (table/index creation) and DML (CRUD) for the
    ``admin_sessions`` table.  The constructor accepts any object that
    satisfies ``DatabaseProviderProtocol`` from ``lexigram-contracts``; the
    type annotation is kept as ``Any`` here to avoid a circular import — the
    contract is enforced at DI-wiring time.

    Implements the ``SessionRepositoryProtocol`` protocol (structural subtyping).
    """

    _TABLE = Table("admin_sessions")

    def __init__(self, db_provider: DatabaseProviderProtocol) -> None:
        """Initialise with a resolved database provider.

        Args:
            db_provider: Framework database provider that exposes
                ``execute_insert``, ``execute_query``, and ``execute``.
        """
        self._db = db_provider
        self._initialized = False

    # ------------------------------------------------------------------
    # Schema bootstrap (DDL)
    # ------------------------------------------------------------------

    async def ensure_schema(self) -> None:
        """Create the ``admin_sessions`` table and indexes if absent.

        Safe to call multiple times — the check is idempotent after the first
        successful run.  Raises on any unexpected DDL failure so callers
        surface the problem rather than silently skipping session persistence.
        """
        if self._initialized:
            return

        try:
            db_type = (getattr(self._db, "database_type", "") or "").lower()
            exists = await self._table_exists(db_type)

            if not exists:
                logger.info("Creating %s table…", self._TABLE)
                await self._db.execute(self._create_table_sql(db_type), [])
                logger.info("✅ %s table created", self._TABLE)
                await self._create_indexes()

            self._initialized = True

        except Exception as _schema_err:  # noqa: BLE001 — schema setup may fail with DB-specific errors; log and propagate
            logger.exception("Failed to initialise %s schema", self._TABLE)
            raise

    async def _table_exists(self, db_type: str) -> bool:
        if db_type in ("postgres", "postgresql"):
            sql = (
                "SELECT EXISTS ("  # noqa: S608 — table name is constant class attr Table("admin_sessions"), never user input
                "  SELECT FROM information_schema.tables"
                "  WHERE table_schema = 'public'"
                f"  AND table_name = '{self._TABLE.name}'"
                ")"
            )
            result = await self._db.execute_query(sql, [])
            if hasattr(result, "rows") and result.rows:
                return bool(result.rows[0].get("exists", False))
            if isinstance(result, list) and result:
                return bool(result[0].get("exists", False))
            return False

        # SQLite fallback
        sql = (
            "SELECT name FROM sqlite_master "  # noqa: S608 — table name is constant class attr Table("admin_sessions"), never user input
            f"WHERE type='table' AND name='{self._TABLE.name}'"
        )
        result = await self._db.execute_query(sql, [])
        if hasattr(result, "rows"):
            return len(result.rows) > 0
        if isinstance(result, list):
            return len(result) > 0
        return bool(result)

    @staticmethod
    def _create_table_sql(db_type: str) -> str:
        if db_type in ("postgres", "postgresql"):
            return """
                CREATE TABLE admin_sessions (
                    session_id  VARCHAR(255) PRIMARY KEY,
                    admin_id    VARCHAR(255) NOT NULL,
                    device_id   VARCHAR(255),
                    ip_address  VARCHAR(45),
                    user_agent  TEXT,
                    fingerprint JSONB,
                    fingerprint_sig VARCHAR(64),
                    is_active   BOOLEAN NOT NULL DEFAULT true,
                    expires_at  TIMESTAMPTZ,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_active_at TIMESTAMPTZ DEFAULT NOW(),
                    FOREIGN KEY (admin_id)
                        REFERENCES admin_users(id) ON DELETE CASCADE
                )
            """
        return """
            CREATE TABLE admin_sessions (
                session_id  VARCHAR(255) PRIMARY KEY,
                admin_id    VARCHAR(255) NOT NULL,
                device_id   VARCHAR(255),
                ip_address  VARCHAR(45),
                user_agent  TEXT,
                fingerprint TEXT,
                fingerprint_sig TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1,
                expires_at  TIMESTAMP,
                created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

    async def _create_indexes(self) -> None:
        indexes = [
            f"CREATE INDEX ix_{self._TABLE.name}_admin_id ON {self._TABLE}(admin_id)",
            f"CREATE INDEX ix_{self._TABLE.name}_device_id ON {self._TABLE}(device_id)",
            f"CREATE INDEX ix_{self._TABLE.name}_is_active ON {self._TABLE}(is_active)",
            f"CREATE INDEX ix_{self._TABLE.name}_expires_at ON {self._TABLE}(expires_at)",
        ]
        for sql in indexes:
            try:
                await self._db.execute(sql, [])
            except (RuntimeError, ValueError, OSError) as exc:
                logger.debug("Index creation skipped: %s", exc)
        logger.info("✅ %s indexes created", self._TABLE)

    # ------------------------------------------------------------------
    # SessionRepositoryProtocol protocol implementation
    # ------------------------------------------------------------------

    async def insert(self, payload: dict[str, Any]) -> None:
        """Persist a new session record.

        Args:
            payload: Field/value mapping (session_id, admin_id, device_id,
                ip_address, user_agent, fingerprint, expires_at, …).
        """
        await self.ensure_schema()
        payload = dict(payload)
        fingerprint = payload.get("fingerprint")
        if isinstance(fingerprint, dict):
            db_type = (getattr(self._db, "database_type", "") or "").lower()
            if db_type in ("sqlite", "sqlite3", "memory"):
                payload["fingerprint"] = dumps_str(fingerprint)
        await self._db.execute_insert(self._TABLE.name, payload)

    async def find_active(self, session_id: str) -> dict[str, Any] | None:
        """Return the row for an active session, or ``None`` if absent/inactive.

        Args:
            session_id: Opaque session identifier.

        Returns:
            Raw row dict, or ``None``.
        """
        await self.ensure_schema()
        sql = f"SELECT * FROM {self._TABLE} WHERE session_id = ? AND is_active = TRUE"  # noqa: S608 — table name is constant class attr Table("admin_sessions"), never user input
        result = await self._db.execute_query(sql, [session_id])

        rows = self._extract_rows(result)
        if not rows:
            return None
        return self._decode_fingerprint(dict(rows[0]))

    async def find_active_by_user(
        self,
        user_id: str,
        cutoff: datetime,
    ) -> list[dict[str, Any]]:
        """Return all non-expired, active sessions for a user.

        Args:
            user_id: Owner identifier.
            cutoff: Sessions expiring at-or-before this timestamp are excluded.

        Returns:
            List of raw row dicts ordered by ``last_active_at`` descending.
        """
        await self.ensure_schema()
        sql = (
            f"SELECT * FROM {self._TABLE} "  # noqa: S608 — table name is constant class attr Table("admin_sessions"), never user input
            "WHERE admin_id = ? AND is_active = TRUE AND expires_at > ? "
            "ORDER BY last_active_at DESC"
        )
        result = await self._db.execute_query(sql, [user_id, cutoff])
        return [self._decode_fingerprint(dict(r)) for r in self._extract_rows(result)]

    async def revoke(self, session_id: str) -> None:
        """Deactivate a single session.

        Args:
            session_id: Session to revoke.
        """
        await self.ensure_schema()
        sql = f"UPDATE {self._TABLE} SET is_active = FALSE WHERE session_id = ?"  # noqa: S608 — table name is constant class attr Table("admin_sessions"), never user input
        await self._db.execute(sql, (session_id,))

    async def revoke_all(self, user_id: str) -> None:
        """Deactivate every active session owned by a user.

        Args:
            user_id: Owner whose sessions are to be revoked.
        """
        await self.ensure_schema()
        sql = f"UPDATE {self._TABLE} SET is_active = FALSE WHERE admin_id = ?"  # noqa: S608 — table name is constant class attr Table("admin_sessions"), never user input
        await self._db.execute(sql, (user_id,))

    async def update_activity(self, session_id: str, now: datetime) -> None:
        """Refresh the ``last_active_at`` timestamp for an active session.

        Args:
            session_id: Session to touch.
            now: Current UTC timestamp to persist.
        """
        await self.ensure_schema()
        sql = (
            f"UPDATE {self._TABLE} "  # noqa: S608 — table name is constant class attr Table("admin_sessions"), never user input
            "SET last_active_at = ? "
            "WHERE session_id = ? AND is_active = TRUE"
        )
        await self._db.execute(sql, (now, session_id))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_rows(result: Any) -> list[Any]:
        """Normalise heterogeneous query result shapes into a plain list."""
        if hasattr(result, "rows"):
            return list(result.rows)
        if isinstance(result, list):
            return result
        return []

    @staticmethod
    def _decode_fingerprint(row: dict[str, Any]) -> dict[str, Any]:
        """Deserialize a string-stored fingerprint back into a dict for SQLite."""
        fingerprint = row.get("fingerprint")
        if isinstance(fingerprint, str):
            try:
                row["fingerprint"] = loads_str(fingerprint)
            except ValueError:
                pass
        return row
