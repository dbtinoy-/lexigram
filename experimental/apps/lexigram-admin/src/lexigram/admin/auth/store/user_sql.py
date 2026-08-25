"""SQL statement and parameter builders for the admin_users store.

Pure query-builder helpers — no database access. The dialect-sensitive
statements (SQLite TEXT vs Postgres JSONB) are selected by the caller via
the ``serialize_lists`` flag or ``db_type`` string.
"""

from __future__ import annotations

from typing import Any

from lexigram.serialization import dumps_str

_POSTGRES_DB_TYPES = ("postgres", "postgresql")


def is_postgres_db_type(db_type: str) -> bool:
    """Return True when the normalized database type is Postgres."""
    return db_type.lower() in _POSTGRES_DB_TYPES


def table_exists_sql(db_type: str) -> str:
    """Return the table-existence probe for the given database type.

    Args:
        db_type: ``database_type`` reported by the provider.

    Returns:
        SQL returning a truthy row iff the ``admin_users`` table exists.
    """
    if is_postgres_db_type(db_type):
        return (
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'admin_users')"
        )
    return "SELECT name FROM sqlite_master WHERE type='table' AND name='admin_users'"


def create_table_sql(db_type: str) -> str:
    """Return the ``CREATE TABLE admin_users`` DDL for the given database type.

    Note:
        UUID in SQLite is TEXT, JSONB columns degrade to TEXT.
    """
    if is_postgres_db_type(db_type):
        return """
            CREATE TABLE admin_users (
                id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password TEXT,
                roles JSONB,
                permissions JSONB,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """
    return """
        CREATE TABLE admin_users (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password TEXT,
            roles TEXT,
            permissions TEXT,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """


def upsert_user_sql() -> str:
    """Return the Postgres atomic upsert statement with RETURNING.

    Explicit ::jsonb casts are required because asyncpg cannot infer the
    column type for unparameterised JSONB columns
    (DataError: expected str, got list).
    """
    return (
        "INSERT INTO admin_users (id, name, email, hashed_password, roles, permissions, is_active) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (email) DO UPDATE SET "
        "name = EXCLUDED.name, hashed_password = EXCLUDED.hashed_password, "
        "roles = EXCLUDED.roles, permissions = EXCLUDED.permissions, is_active = EXCLUDED.is_active, updated_at = NOW() "
        "RETURNING id, name, email"
    )


def upsert_user_params(
    admin_id: str,
    name: str,
    email: str,
    hashed_password: str,
    roles: list[str] | None,
    permissions: list[str] | None,
) -> list[Any]:
    """Return bind parameters for :func:`upsert_user_sql`."""
    return [
        admin_id,
        name,
        email,
        hashed_password,
        roles or [],
        permissions or [],
        True,
    ]


def insert_user_sql() -> str:
    """Return the plain INSERT used as the Postgres fallback path."""
    return (
        "INSERT INTO admin_users (id, name, email, hashed_password, roles, permissions, is_active) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)"
    )


def serialize_roles(roles: list[str] | None, *, serialize_lists: bool) -> Any:
    """Encode a roles/permissions list per dialect (JSON text vs native list)."""
    if not serialize_lists:
        return roles or []
    return dumps_str(roles or [])


def insert_user_payload(
    admin_id: str,
    name: str,
    email: str,
    hashed_password: str,
    roles: list[str] | None,
    permissions: list[str] | None,
    *,
    serialize_lists: bool,
) -> dict[str, Any]:
    """Build the column payload for ``execute_insert("admin_users", ...)``.

    SQLite cannot bind Python lists — roles/permissions are stored as JSON
    text when ``serialize_lists`` is set.
    """
    return {
        "id": admin_id,
        "name": name,
        "email": email,
        "hashed_password": hashed_password,
        "roles": serialize_roles(roles, serialize_lists=serialize_lists),
        "permissions": serialize_roles(permissions, serialize_lists=serialize_lists),
        "is_active": True,
    }


def update_user_payload(user: Any, *, serialize_lists: bool) -> dict[str, Any]:
    """Build the column payload for updating an existing ``admin_users`` row."""
    return {
        "name": user.name,
        "email": user.email,
        "hashed_password": getattr(user, "hashed_password", None),
        "roles": serialize_roles(
            getattr(user, "roles", []), serialize_lists=serialize_lists
        ),
        "permissions": serialize_roles(
            getattr(user, "permissions", []), serialize_lists=serialize_lists
        ),
        "is_active": getattr(user, "is_active", True),
    }


def claim_first_admin_sql(*, serialize_lists: bool) -> str:
    """Return the conditional first-admin INSERT statement.

    Runs a single ``INSERT ... SELECT ... WHERE NOT EXISTS`` so concurrent
    first-run submissions cannot both insert. When ``serialize_lists`` is
    set (SQLite), roles/permissions are pre-encoded JSON text; otherwise
    explicit ``::jsonb`` casts bind native lists on Postgres.
    """
    if serialize_lists:
        return (
            "INSERT INTO admin_users "
            "(id, name, email, hashed_password, roles, permissions, is_active) "
            "SELECT ?, ?, ?, ?, ?, ?, ? "
            "WHERE NOT EXISTS (SELECT 1 FROM admin_users)"
        )
    return (
        "INSERT INTO admin_users "
        "(id, name, email, hashed_password, roles, permissions, is_active) "
        "SELECT ?, ?, ?, ?, roles::jsonb, permissions::jsonb, ? "
        "WHERE NOT EXISTS (SELECT 1 FROM admin_users)"
    )


def claim_first_admin_params(
    admin_id: str,
    name: str,
    email: str,
    hashed_password: str,
    roles: list[str],
    *,
    serialize_lists: bool,
) -> list[Any]:
    """Return bind parameters for :func:`claim_first_admin_sql`."""
    if serialize_lists:
        return [
            admin_id,
            name,
            email,
            hashed_password,
            dumps_str(roles),
            "[]",
            True,
        ]
    return [admin_id, name, email, hashed_password, roles, [], True]


__all__ = [
    "claim_first_admin_params",
    "claim_first_admin_sql",
    "create_table_sql",
    "insert_user_payload",
    "insert_user_sql",
    "is_postgres_db_type",
    "serialize_roles",
    "table_exists_sql",
    "update_user_payload",
    "upsert_user_params",
    "upsert_user_sql",
]
