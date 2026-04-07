"""Users controller — example CRUD resource."""
from __future__ import annotations

from lexigram.web.routing.controllers import Controller
from lexigram.web.routing.decorators import delete, get, post, put


class UserController(Controller):
    """Handles /users routes."""

    prefix = "/users"

    @get("/")
    async def list_users(self) -> dict:
        """List all users."""
        return {"users": [], "total": 0}

    @post("/")
    async def create_user(self) -> dict:
        """Create a new user."""
        return {"id": "new-user-id", "message": "User created"}

    @get("/{user_id}")
    async def get_user(self, user_id: str) -> dict:
        """Get a user by ID."""
        return {"id": user_id}

    @put("/{user_id}")
    async def update_user(self, user_id: str) -> dict:
        """Update a user."""
        return {"id": user_id, "message": "Updated"}

    @delete("/{user_id}")
    async def delete_user(self, user_id: str) -> None:
        """Delete a user."""
