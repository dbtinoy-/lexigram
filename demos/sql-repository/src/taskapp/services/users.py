"""User service — business logic for user management."""

from __future__ import annotations

from typing import Any

from lexigram.result import Result
from taskapp.domain import User, UserRole


class UserService:
    """Business operations for users.

    Uses Result[T, E] instead of raising exceptions.  Controllers
    pattern-match on the result to decide the HTTP response.
    """

    def __init__(self, user_repo: Any) -> None:
        self._repo = user_repo

    async def create_user(
        self,
        name: str,
        email: str,
        role: UserRole = UserRole.MEMBER,
    ) -> Result[User, str]:
        """Create a new user.

        Returns Ok(user) on success, Err(message) on failure.
        """
        if not name:
            return Result.err("Name is required")
        if not email:
            return Result.err("Email is required")

        user = User(name=name, email=email, role=role)
        created = await self._repo.add(user)
        return Result.ok(created)

    async def get_user(self, user_id: int) -> Result[User, str]:
        """Get a user by ID."""
        user = await self._repo.get(user_id)
        if user is None:
            return Result.err(f"User {user_id} not found")
        return Result.ok(user)

    async def list_users(self) -> list[User]:
        """List all users."""
        return await self._repo.list()

    async def delete_user(self, user_id: int) -> Result[bool, str]:
        """Delete a user by ID."""
        deleted = await self._repo.delete(user_id)
        if not deleted:
            return Result.err(f"User {user_id} not found")
        return Result.ok(True)


__all__ = ["UserService"]
