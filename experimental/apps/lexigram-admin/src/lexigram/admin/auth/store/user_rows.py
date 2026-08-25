"""Row parsing and lightweight record types for the admin_users store."""

from __future__ import annotations

from typing import Any

from lexigram.serialization import loads as json_loads


def parse_list_column(value: Any) -> list[str]:
    """Normalize a roles/permissions column value into a string list.

    Handles real lists (Postgres JSONB arrays), Postgres array literals
    (``"{admin,editor}"``), and JSON text (SQLite TEXT columns).

    Args:
        value: Raw column value.

    Returns:
        List of string entries; empty when the value is ``None`` or empty.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    text = str(value).strip()
    if text.startswith("{") and text.endswith("}"):
        inner = text[1:-1].strip()
        return [part.strip() for part in inner.split(",")] if inner else []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json_loads(text)
        except ValueError:
            return []
        return [str(v) for v in parsed] if isinstance(parsed, list) else []
    return []


def row_to_user(row: dict[str, Any]) -> Any:
    """Build a mutable user record object from an ``admin_users`` row."""

    class _UserObj:
        def __init__(self, row: dict[str, Any]) -> None:
            self.user_id = str(row.get("id") or row.get("user_id"))
            self.name = row.get("name")
            self.email = row.get("email")
            self.roles = parse_list_column(row.get("roles"))
            self.permissions = parse_list_column(row.get("permissions"))
            self.hashed_password = row.get("hashed_password")
            self.is_active = row.get("is_active")

        def record_login(self) -> Any:
            """Record login - no-op for admin users"""

    return _UserObj(row)


class CreatedUser:
    """Lightweight created-user record returned by create/claim operations."""

    def __init__(self, uid: str, name: str, email: str) -> None:
        self.user_id = uid
        self.name = name
        self.username = name
        self.email = email


def first_row(result: Any) -> Any:
    """Extract the first row from a query result in any supported shape.

    Supports ``QueryResult`` objects (``rows``), DB-API cursors
    (``fetchone``), plain dicts, and lists of dicts.

    Args:
        result: Raw result from ``execute_query``.

    Returns:
        The first row mapping, or ``None`` when no rows are present.
    """
    if hasattr(result, "rows") and result.rows:
        return result.rows[0]
    if hasattr(result, "fetchone"):
        return result.fetchone()
    if isinstance(result, dict):
        return result
    if isinstance(result, list) and result:
        return result[0]
    return None


__all__ = ["CreatedUser", "first_row", "parse_list_column", "row_to_user"]
