"""SQL-backed implementation of AdminRoleStoreProtocol.

Owns all DDL and DML for the ``admin_roles`` table.  The service layer
depends only on ``AdminRoleStoreProtocol`` — never on this class directly.
Permissions and inheritance are stored as JSON text for database-portable
array semantics.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.rbac.protocols import AdminRoleStoreProtocol
from lexigram.admin.sql_dialect import is_postgres, now_expr
from lexigram.contracts.auth import RoleDefinition
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.serialization import dumps_str, loads

logger = get_logger(__name__)

_TABLE = "admin_roles"


def _load_list(value: Any) -> list[str]:
    """Parse a stored JSON text column into a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    try:
        parsed = loads(str(value))
    except ValueError:
        return []
    return [str(v) for v in parsed] if isinstance(parsed, list) else []


@inject
class AdminRoleSqlStore(AdminRoleStoreProtocol):
    """SQL store for admin roles.

    Implements ``AdminRoleStoreProtocol``.  Manages the ``admin_roles``
    table including DDL bootstrap.  Role names are the primary key; rows
    mirror the shape ``AuthorizationService.sync_from_db`` expects from
    its legacy ``admin_roles`` fallback table (``name``, ``description``,
    ``permissions``, ``inherits``, plus ``is_system`` for UI protection).
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        """Initialise with a resolved database provider.

        Args:
            db: Framework database provider exposing ``execute`` and
                ``execute_query``.
        """
        self._db = db
        self._initialized = False

    async def ensure_schema(self) -> None:
        """Create the roles table if it does not exist (idempotent)."""
        if self._initialized:
            return
        if is_postgres(self._db):
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    name        VARCHAR(100) PRIMARY KEY,
                    description TEXT         NOT NULL DEFAULT '',
                    permissions TEXT         NOT NULL DEFAULT '[]',
                    inherits    TEXT         NOT NULL DEFAULT '[]',
                    is_system   BOOLEAN      NOT NULL DEFAULT FALSE,
                    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                )
            """
        else:
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    name        VARCHAR(100) PRIMARY KEY,
                    description TEXT         NOT NULL DEFAULT '',
                    permissions TEXT         NOT NULL DEFAULT '[]',
                    inherits    TEXT         NOT NULL DEFAULT '[]',
                    is_system   BOOLEAN      NOT NULL DEFAULT FALSE,
                    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """
        await self._db.execute(create_sql, [])
        self._initialized = True

    async def list_roles(self) -> list[RoleDefinition]:
        """Return all roles ordered by name (see protocol docs)."""
        result = await self._db.execute_query(
            f"SELECT name, description, permissions, inherits, is_system FROM {_TABLE} ORDER BY name",
            [],
        )
        return [self._row_to_role(row) for row in self._rows(result)]

    async def get_role(self, name: str) -> RoleDefinition | None:
        """Look up a role by name (see protocol docs)."""
        result = await self._db.execute_query(
            f"SELECT name, description, permissions, inherits, is_system FROM {_TABLE} WHERE name = ?",
            [name],
        )
        rows = self._rows(result)
        return self._row_to_role(rows[0]) if rows else None

    async def create_role(self, role: RoleDefinition) -> None:
        """Insert a new role (see protocol docs)."""
        await self._db.execute(
            f"INSERT INTO {_TABLE} (name, description, permissions, inherits, is_system) VALUES (?, ?, ?, ?, ?)",
            [
                role.name,
                role.description,
                dumps_str(role.permissions),
                dumps_str(role.inherits),
                role.is_system,
            ],
        )

    async def update_role(self, role: RoleDefinition) -> None:
        """Update an existing role by name (see protocol docs)."""
        await self._db.execute(
            f"UPDATE {_TABLE} SET description = ?, permissions = ?, inherits = ?, is_system = ?, "
            f"updated_at = {now_expr(self._db)} WHERE name = ?",
            [
                role.description,
                dumps_str(role.permissions),
                dumps_str(role.inherits),
                role.is_system,
                role.name,
            ],
        )

    async def delete_role(self, name: str) -> bool:
        """Delete a role by name; ``True`` when a row was removed."""
        result = await self._db.execute(
            f"DELETE FROM {_TABLE} WHERE name = ?",
            [name],
        )
        row_count = getattr(result, "row_count", None)
        if row_count is not None:
            return int(row_count) > 0
        return True

    @staticmethod
    def _rows(result: Any) -> list[dict[str, Any]]:
        """Normalize execute_query results (object/.rows, list, or dict)."""
        if hasattr(result, "rows") and result.rows:
            return list(result.rows)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
        return []

    @staticmethod
    def _row_to_role(row: dict[str, Any]) -> RoleDefinition:
        """Build an RoleDefinition from a provider row."""
        return RoleDefinition(
            name=str(row.get("name", "")),
            description=str(row.get("description", "")),
            permissions=_load_list(row.get("permissions")),
            inherits=_load_list(row.get("inherits")),
            is_system=bool(row.get("is_system", False)),
        )


__all__ = ["AdminRoleSqlStore"]
