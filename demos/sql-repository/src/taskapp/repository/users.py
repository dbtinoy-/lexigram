"""User repository — maps User entities to the ``users`` table."""

from __future__ import annotations

from typing import Any

from lexigram.sql.repositories.base import SQLRepository
from taskapp.domain import User, UserRole


class UserRepository(SQLRepository[User, int]):
    """CRUD operations for User entities.

    The repository handles all SQL details.  Business logic lives in
    services, not here.
    """

    def __init__(self, provider: Any) -> None:
        super().__init__(
            provider=provider,
            table_name="users",
            key_field="id",
        )

    def _entity_to_dict(self, entity: User) -> dict[str, Any]:
        """Convert a User domain model to a database row dict."""
        return {
            "name": entity.name,
            "email": entity.email,
            "role": entity.role.value,
        }

    def _row_to_entity(self, row: dict[str, Any]) -> User:
        """Convert a database row dict to a User domain model."""
        return User(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            role=UserRole(row["role"]),
        )


__all__ = ["UserRepository"]
