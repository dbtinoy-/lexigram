"""SQL dialect helpers for direct-SQL stores.

The admin-security stores issue raw DDL/DML that uses Postgres-only
syntax (``gen_random_uuid``, ``TIMESTAMPTZ``, ``NOW()``, ``INTERVAL``).
These helpers centralise the dialect branch so stores keep a single
code path that works on both Postgres and SQLite.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from lexigram.contracts.data.sql.sql_dialect import SQLDialect

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol


# Postgres drivers report ``database_type`` as ``postgres``, the enum
# name is ``POSTGRESQL`` — map the driver identifier to the enum member.
_DIALECT_ALIASES: Final[dict[str, SQLDialect]] = {
    "postgres": SQLDialect.POSTGRESQL,
}


def _dialect(db: DatabaseProviderProtocol) -> str:
    raw = (getattr(db, "database_type", "") or "").lower()
    if raw in _DIALECT_ALIASES:
        return _DIALECT_ALIASES[raw]
    for dialect in SQLDialect:
        if raw == dialect.value or raw == dialect.name.lower():
            return dialect
    return raw


def is_postgres(db: DatabaseProviderProtocol) -> bool:
    """Return ``True`` when the provider targets Postgres.

    Args:
        db: The database provider.

    Returns:
        ``True`` for Postgres/PostgreSQL providers; ``False`` otherwise.
    """
    return _dialect(db) == SQLDialect.POSTGRESQL


def now_expr(db: DatabaseProviderProtocol) -> str:
    """Return the dialect's current-timestamp expression.

    Args:
        db: The database provider.

    Returns:
        ``NOW()`` on Postgres, ``CURRENT_TIMESTAMP`` elsewhere.
    """
    return "NOW()" if is_postgres(db) else "CURRENT_TIMESTAMP"


def since_expr(db: DatabaseProviderProtocol, seconds: int) -> str:
    """Return the dialect's "now minus N seconds" expression.

    Args:
        db: The database provider.
        seconds: Look-back window in seconds.

    Returns:
        Postgres ``NOW() - INTERVAL 'N seconds'`` or SQLite
        ``datetime('now', '-N seconds')``.
    """
    if is_postgres(db):
        return f"NOW() - INTERVAL '{int(seconds)} seconds'"
    return f"datetime('now', '-{int(seconds)} seconds')"
