"""SQL-backed idempotency store for durable deduplication without Redis.

Uses ``DatabaseProviderProtocol`` from ``lexigram-contracts`` as the storage
layer — never directly from ``lexigram-sql``.  The provider is injected by the
DI container at runtime.

Schema managed by this store (created lazily on first use)::

    CREATE TABLE idempotency_keys (
        key        TEXT        NOT NULL,
        result     TEXT        NOT NULL,  -- JSON-serialised payload
        created_at TIMESTAMP   NOT NULL,
        expires_at TIMESTAMP,             -- NULL means never expires
        PRIMARY KEY (key)
    );
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import count
import re
from typing import TYPE_CHECKING, Any

from lexigram import serialization as json
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

logger = get_logger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key        TEXT      NOT NULL,
    result     TEXT      NOT NULL,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    PRIMARY KEY (key)
)
"""

_GET_SQL = "SELECT result, expires_at FROM idempotency_keys WHERE key = ?"
_SET_SQL = (
    "INSERT INTO idempotency_keys (key, result, created_at, expires_at) "
    "VALUES (?, ?, ?, ?) "
    "ON CONFLICT (key) DO UPDATE SET result = excluded.result, "
    "expires_at = excluded.expires_at"
)
_DELETE_SQL = "DELETE FROM idempotency_keys WHERE key = ?"
_PURGE_EXPIRED_SQL = (
    "DELETE FROM idempotency_keys WHERE expires_at IS NOT NULL AND expires_at <= ?"
)
_ACQUIRE_SQL = (
    "INSERT INTO idempotency_keys (key, result, created_at, expires_at) "
    "VALUES (?, '__pending__', ?, ?) "
    "ON CONFLICT (key) DO NOTHING"
)


def _translate_placeholders(sql: str, dialect: str) -> str:
    """Translate ``?`` placeholders into dialect-correct form.

    SQLite (and unknown dialects) keep ``?`` untouched. Postgres uses
    sequentially numbered ``$1``, ``$2``, ... so that each positional
    parameter binds to exactly one placeholder — a naive ``?`` -> ``$1``
    substitution would bind every parameter to the first slot.
    """
    if dialect not in ("postgres", "postgresql"):
        return sql
    counter = count(1)
    return re.sub(r"\?", lambda _match: f"${next(counter)}", sql)


class DatabaseIdempotencyStore:
    """SQL-backed idempotency store using ``DatabaseProviderProtocol``.

    Provides at-most-once execution guarantees backed by a relational database,
    suitable for deployments that do not have Redis but already run a SQL
    database.

    The idempotency table is created automatically on first use (lazy
    initialisation).  For production workloads consider creating the table via
    your migration pipeline using the DDL shown in the module docstring.

    Args:
        db: Database provider resolved from the container.
        table: Name of the idempotency table.  Override if the default name
            clashes with an existing table in your schema.
    """

    def __init__(
        self,
        db: DatabaseProviderProtocol,
        table: str = "idempotency_keys",
    ) -> None:
        """Create a database-backed idempotency store.

        Args:
            db: Database provider resolved from the container.
            table: Name of the idempotency table.
        """
        self._db = db
        self._table = table
        self._initialised = False

    async def get(self, key: str) -> Any | None:
        """Retrieve a stored result by idempotency key.

        Expired records are treated as non-existent.

        Args:
            key: The idempotency key.

        Returns:
            The stored result, or ``None`` if not found or expired.
        """
        await self._ensure_table()
        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            rows = await conn.fetch(
                _translate_placeholders(_GET_SQL, self._dialect), key
            )

        if not rows:
            logger.debug("idempotency.db.get", key=key, found=False)
            return None

        row = rows[0]
        expires_at = row.get("expires_at")
        if expires_at and _parse_dt(expires_at) <= datetime.now(UTC):
            logger.debug("idempotency.db.get", key=key, found=False, reason="expired")
            return None

        try:
            result = json.loads(row["result"])
        except (json.JSONDecodeError, KeyError, TypeError):
            result = row.get("result")

        logger.debug("idempotency.db.get", key=key, found=True)
        return result

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store a result with an optional TTL.

        Args:
            key: The idempotency key.
            value: The result to store (must be JSON-serialisable).
            ttl: Time-to-live in seconds, or ``None`` for no expiry.
        """
        await self._ensure_table()
        now = datetime.now(UTC)
        expires_at: datetime | None = (
            now + timedelta(seconds=ttl) if ttl is not None else None
        )
        try:
            serialised = json.dumps(value)
        except (TypeError, ValueError):
            serialised = str(value).encode()

        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            await conn.execute(
                _translate_placeholders(_SET_SQL, self._dialect),
                key,
                serialised,
                now,
                expires_at,
            )

        logger.debug("idempotency.db.set", key=key, ttl=ttl)

    async def delete(self, key: str) -> None:
        """Remove an idempotency record by key.

        Args:
            key: The idempotency key to remove.
        """
        await self._ensure_table()
        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            await conn.execute(_translate_placeholders(_DELETE_SQL, self._dialect), key)
        logger.debug("idempotency.db.delete", key=key)

    async def acquire(self, key: str, ttl: int) -> bool:
        """Atomically claim an idempotency key using INSERT ON CONFLICT DO NOTHING.

        Issues an ``INSERT … ON CONFLICT (key) DO NOTHING`` which is atomic on
        all major RDBMS (PostgreSQL, SQLite, MySQL).  Returns ``True`` only if
        a new row was inserted, meaning this caller won the race to claim the
        key.  Returns ``False`` if another caller already holds the key.

        Args:
            key: The idempotency key to acquire.
            ttl: Time-to-live in seconds for the claimed key.

        Returns:
            ``True`` if the key was freshly claimed; ``False`` if already held.
        """
        await self._ensure_table()
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=ttl)
        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            status = await conn.execute(
                _translate_placeholders(_ACQUIRE_SQL, self._dialect),
                key,
                now,
                expires_at,
            )
        acquired = status is not None and "0 0" not in str(status)
        logger.debug("idempotency.db.acquire", key=key, acquired=acquired)
        return acquired

    async def purge_expired(self) -> None:
        """Remove all records whose TTL has elapsed.

        Call this periodically (e.g. from a scheduled task) to keep the table
        from growing unboundedly.
        """
        await self._ensure_table()
        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            await conn.execute(
                _translate_placeholders(_PURGE_EXPIRED_SQL, self._dialect),
                datetime.now(UTC),
            )
        logger.debug("idempotency.db.purge_expired")

    async def cleanup_expired(self) -> int:
        """Remove all expired records and return the count purged.

        Returns:
            Number of expired rows removed (best-effort; may be ``0`` if the
            driver does not surface affected-row counts).
        """
        await self._ensure_table()
        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            status = await conn.execute(
                _translate_placeholders(_PURGE_EXPIRED_SQL, self._dialect),
                datetime.now(UTC),
            )
        removed = 0
        if status:
            parts = str(status).split()
            if len(parts) >= 2:
                try:
                    removed = int(parts[-1])
                except ValueError:
                    removed = 0
        logger.debug("idempotency.db.cleanup_expired", removed=removed)
        return removed

    @property
    def _dialect(self) -> str:
        """SQL dialect of the injected provider, used for placeholder translation.

        Reads the provider's ``database_type`` attribute (``postgres``,
        ``sqlite``, ``mysql``); providers that do not expose it fall back to
        SQLite-style ``?`` placeholders.
        """
        return str(getattr(self._db, "database_type", "sqlite"))

    async def _ensure_table(self) -> None:
        """Create the idempotency table if it does not already exist."""
        if self._initialised:
            return
        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            await conn.execute(_CREATE_TABLE_SQL)
        self._initialised = True


def _parse_dt(value: Any) -> datetime:
    """Coerce a raw DB value to an aware ``datetime``."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    dt = datetime.fromisoformat(str(value))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


__all__ = ["DatabaseIdempotencyStore"]
