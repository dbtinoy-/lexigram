"""Todo controller — CRUD endpoints for todo items.

All endpoints require a valid ``Authorization: Bearer <token>`` header.
Ownership is enforced at the service layer — a user may only read and
modify their own todos.

Handles:
- ``GET    /todos``                   — list all todos for the current user.
- ``POST   /todos``                   — create a new todo.
- ``GET    /todos/{todo_id}``         — retrieve a single todo.
- ``PATCH  /todos/{todo_id}/complete``— mark a todo as completed.
- ``DELETE /todos/{todo_id}``         — delete a todo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel
from starlette.requests import Request

from lexigram.logging import get_logger
from lexigram.web.routing.controllers import Controller
from lexigram.web.routing.decorators import delete, get, patch, post

from lexigram_example_api.services.todo_service import (
    TodoAccessDenied,
    TodoAlreadyCompleted,
    TodoNotFound,
)

if TYPE_CHECKING:
    from lexigram.auth.authn.jwt import JWTTokenManager

    from lexigram_example_api.services.todo_service import TodoService

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateTodoRequest(BaseModel):
    """Body schema for todo creation.

    Attributes:
        title: Short headline for the task (required, non-empty).
        description: Optional longer description.
    """

    title: str
    description: str | None = None


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------


class TodoController(Controller):
    """REST controller for todo item CRUD operations.

    All endpoints are protected — a valid JWT must be present in the
    ``Authorization: Bearer <token>`` header.

    Endpoints:
        GET    /todos                    — List current user's todos.
        POST   /todos                    — Create a new todo.
        GET    /todos/{todo_id}          — Get a single todo by ID.
        PATCH  /todos/{todo_id}/complete — Mark a todo complete.
        DELETE /todos/{todo_id}          — Delete a todo.

    Args:
        todo_service: Domain service for todo operations.
        jwt_manager: JWT manager for token verification on all routes.
    """

    def __init__(
        self,
        todo_service: TodoService,
        jwt_manager: JWTTokenManager,
    ) -> None:
        """Initialise the controller with injected dependencies.

        Args:
            todo_service: Domain service for todo operations.
            jwt_manager: JWT manager for verifying bearer tokens.
        """
        super().__init__()
        self._todo_service = todo_service
        self._jwt = jwt_manager

    @get("/todos")
    async def list_todos(self, request: Request) -> tuple[dict[str, Any], int]:
        """Return all todos owned by the authenticated user.

        Args:
            request: The incoming HTTP request (used to extract JWT).

        Returns:
            ``200`` with ``{"todos": [...]}`` on success.
            ``401`` with ``{"error": "Unauthorized"}`` if not authenticated.
        """
        user_id = await self._extract_user_id(request)
        if user_id is None:
            return {"error": "Unauthorized"}, 401

        result = await self._todo_service.list_by_owner(user_id)
        todos = result.unwrap()  # list_by_owner always returns Ok
        return {"todos": [t.to_dict() for t in todos]}, 200

    @post("/todos")
    async def create_todo(
        self, request: Request, body: CreateTodoRequest
    ) -> tuple[dict[str, Any], int]:
        """Create a new todo item for the authenticated user.

        Args:
            request: The incoming HTTP request (used to extract JWT).
            body: Todo creation payload (title + optional description).

        Returns:
            ``201`` with ``{"todo": {...}}`` on success.
            ``401`` with ``{"error": "Unauthorized"}`` if not authenticated.
            ``422`` with ``{"error": "..."}`` on validation failure.
        """
        user_id = await self._extract_user_id(request)
        if user_id is None:
            return {"error": "Unauthorized"}, 401

        if not body.title.strip():
            return {"error": "Title must not be empty"}, 422

        result = await self._todo_service.create(
            owner_id=user_id,
            title=body.title.strip(),
            description=body.description,
        )

        if result.is_err():
            return {"error": str(result.unwrap_err())}, 400

        logger.info("todo_controller_created", user_id=user_id)
        return {"todo": result.unwrap().to_dict()}, 201

    @get("/todos/{todo_id}")
    async def get_todo(
        self, request: Request, todo_id: str
    ) -> tuple[dict[str, Any], int]:
        """Retrieve a single todo by its identifier.

        Args:
            request: The incoming HTTP request (used to extract JWT).
            todo_id: UUID string of the todo to retrieve.

        Returns:
            ``200`` with ``{"todo": {...}}`` on success.
            ``401`` with ``{"error": "Unauthorized"}`` if not authenticated.
            ``403`` with ``{"error": "..."}`` if the todo belongs to another user.
            ``404`` with ``{"error": "..."}`` if the todo does not exist.
        """
        user_id = await self._extract_user_id(request)
        if user_id is None:
            return {"error": "Unauthorized"}, 401

        result = await self._todo_service.get(todo_id, user_id)
        return self._todo_result_response(result)

    @patch("/todos/{todo_id}/complete")
    async def complete_todo(
        self, request: Request, todo_id: str
    ) -> tuple[dict[str, Any], int]:
        """Mark a todo as completed.

        Args:
            request: The incoming HTTP request (used to extract JWT).
            todo_id: UUID string of the todo to complete.

        Returns:
            ``200`` with ``{"todo": {...}}`` on success.
            ``401`` with ``{"error": "Unauthorized"}`` if not authenticated.
            ``403`` with ``{"error": "..."}`` if access is denied.
            ``404`` with ``{"error": "..."}`` if the todo does not exist.
            ``409`` with ``{"error": "..."}`` if already completed.
        """
        user_id = await self._extract_user_id(request)
        if user_id is None:
            return {"error": "Unauthorized"}, 401

        result = await self._todo_service.complete(todo_id, user_id)

        if result.is_err():
            err = result.unwrap_err()
            if isinstance(err, TodoAlreadyCompleted):
                return {"error": str(err)}, 409
            if isinstance(err, TodoAccessDenied):
                return {"error": str(err)}, 403
            if isinstance(err, TodoNotFound):
                return {"error": str(err)}, 404
            return {"error": str(err)}, 400

        return {"todo": result.unwrap().to_dict()}, 200

    @delete("/todos/{todo_id}")
    async def delete_todo(
        self, request: Request, todo_id: str
    ) -> tuple[dict[str, Any], int]:
        """Delete a todo item.

        Args:
            request: The incoming HTTP request (used to extract JWT).
            todo_id: UUID string of the todo to delete.

        Returns:
            ``204`` body ``{}`` on success.
            ``401`` with ``{"error": "Unauthorized"}`` if not authenticated.
            ``403`` with ``{"error": "..."}`` if access is denied.
            ``404`` with ``{"error": "..."}`` if the todo does not exist.
        """
        user_id = await self._extract_user_id(request)
        if user_id is None:
            return {"error": "Unauthorized"}, 401

        result = await self._todo_service.delete(todo_id, user_id)

        if result.is_err():
            err = result.unwrap_err()
            if isinstance(err, TodoAccessDenied):
                return {"error": str(err)}, 403
            if isinstance(err, TodoNotFound):
                return {"error": str(err)}, 404
            return {"error": str(err)}, 400

        logger.info("todo_controller_deleted", todo_id=todo_id, user_id=user_id)
        return {}, 204

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _todo_result_response(
        self, result: Any
    ) -> tuple[dict[str, Any], int]:
        """Convert a todo service Result into an HTTP response tuple.

        Args:
            result: ``Result[Todo, DomainError]`` from the service.

        Returns:
            An HTTP response tuple ``(body_dict, status_code)``.
        """
        if result.is_err():
            err = result.unwrap_err()
            if isinstance(err, TodoNotFound):
                return {"error": str(err)}, 404
            if isinstance(err, TodoAccessDenied):
                return {"error": str(err)}, 403
            return {"error": str(err)}, 400
        return {"todo": result.unwrap().to_dict()}, 200

    async def _extract_user_id(self, request: Request) -> str | None:
        """Extract and verify the JWT from the Authorization header.

        Args:
            request: The incoming HTTP request.

        Returns:
            The ``user_id`` (``sub`` claim) if the token is valid, or ``None``.
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:]
        try:
            token_result = await self._jwt.verify_token(
                token,
                allow_missing_audience=True,
            )
        except Exception as exc:  # noqa: BLE001 — infrastructure failures from JWT library
            logger.warning("jwt_verification_error", error=str(exc))
            return None

        if token_result.is_err():
            return None

        return token_result.unwrap().user_id
