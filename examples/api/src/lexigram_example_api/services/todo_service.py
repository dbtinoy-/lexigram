"""Todo service — CRUD operations with ownership enforcement.

:class:`TodoService` manages the full lifecycle of todo items: creation,
listing, completion, and deletion.  All operations enforce that a user
may only read and modify *their own* todos.

All domain operations return ``Result[T, E]`` so callers can pattern-match
outcomes without catching exceptions for control flow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.exceptions.domain import DomainError, NotFoundError
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

from lexigram_example_api.domain.todo import Todo, TodoCompleted, TodoCreated

if TYPE_CHECKING:
    from lexigram.contracts.events.protocols import DomainEventPublisherProtocol

    from lexigram_example_api.repositories.todo_repository import TodoRepositoryProtocol

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Domain errors
# ---------------------------------------------------------------------------


class TodoNotFound(NotFoundError):
    """Raised when a requested todo does not exist.

    Attributes:
        todo_id: The identifier that was not found.
    """

    def __init__(self, todo_id: str) -> None:
        """Initialise with the missing todo identifier.

        Args:
            todo_id: The todo identifier that could not be found.
        """
        super().__init__(f"Todo not found: {todo_id}")
        self.todo_id = todo_id


class TodoAccessDenied(DomainError):
    """Raised when a user attempts to access another user's todo."""

    def __init__(self, todo_id: str) -> None:
        """Initialise with the todo identifier that was access-denied.

        Args:
            todo_id: The todo identifier that access was denied to.
        """
        super().__init__(f"Access denied to todo: {todo_id}")
        self.todo_id = todo_id


class TodoAlreadyCompleted(DomainError):
    """Raised when attempting to complete an already-completed todo.

    Attributes:
        todo_id: The identifier of the already-completed todo.
    """

    def __init__(self, todo_id: str) -> None:
        """Initialise with the completed todo identifier.

        Args:
            todo_id: The todo identifier that is already completed.
        """
        super().__init__(f"Todo already completed: {todo_id}")
        self.todo_id = todo_id


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class TodoService:
    """Domain service for todo item operations.

    Enforces per-user ownership on all read and write operations.
    Publishes domain events to the event bus on state-changing operations.

    Args:
        repo: Repository for todo persistence.
        event_publisher: Domain event publisher.
    """

    def __init__(
        self,
        repo: TodoRepositoryProtocol,
        event_publisher: DomainEventPublisherProtocol,
    ) -> None:
        """Initialise TodoService with injected dependencies.

        Args:
            repo: Repository for todo persistence.
            event_publisher: Domain event publisher.
        """
        self._repo = repo
        self._events = event_publisher

    async def create(
        self,
        owner_id: str,
        title: str,
        description: str | None = None,
    ) -> Result[Todo, DomainError]:
        """Create and persist a new todo item.

        Args:
            owner_id: UUID string of the user creating the todo.
            title: Short headline for the task.
            description: Optional longer description.

        Returns:
            ``Ok(Todo)`` with the persisted entity.
        """
        todo = Todo(title=title, description=description, owner_id=owner_id)
        saved = await self._repo.save(todo)
        await self._events.publish(
            TodoCreated(todo_id=saved.todo_id, title=saved.title, owner_id=owner_id)
        )
        logger.info("todo_created", todo_id=saved.todo_id, owner_id=owner_id)
        return Ok(saved)

    async def list_by_owner(
        self,
        owner_id: str,
    ) -> Result[list[Todo], DomainError]:
        """Return all todos owned by a given user.

        Args:
            owner_id: UUID string of the owning user.

        Returns:
            ``Ok(list[Todo])`` — may be an empty list if none exist.
        """
        todos = await self._repo.find_by_owner(owner_id)
        return Ok(todos)

    async def get(
        self,
        todo_id: str,
        owner_id: str,
    ) -> Result[Todo, DomainError]:
        """Retrieve a single todo by identifier, enforcing ownership.

        Args:
            todo_id: UUID string of the todo to retrieve.
            owner_id: UUID string of the requesting user (ownership check).

        Returns:
            ``Ok(Todo)`` if found and owned by the user, or:
            - ``Err(TodoNotFound)`` if the todo does not exist.
            - ``Err(TodoAccessDenied)`` if owned by a different user.
        """
        todo = await self._repo.find_by_id(todo_id)
        if todo is None:
            return Err(TodoNotFound(todo_id))
        if todo.owner_id != owner_id:
            return Err(TodoAccessDenied(todo_id))
        return Ok(todo)

    async def complete(
        self,
        todo_id: str,
        owner_id: str,
    ) -> Result[Todo, DomainError]:
        """Mark a todo as completed.

        Args:
            todo_id: UUID string of the todo to complete.
            owner_id: UUID string of the requesting user (ownership check).

        Returns:
            ``Ok(Todo)`` with the updated entity, or:
            - ``Err(TodoNotFound)`` if the todo does not exist.
            - ``Err(TodoAccessDenied)`` if owned by a different user.
            - ``Err(TodoAlreadyCompleted)`` if already done.
        """
        get_result = await self.get(todo_id, owner_id)
        if get_result.is_err():
            return get_result

        todo = get_result.unwrap()
        if todo.completed:
            return Err(TodoAlreadyCompleted(todo_id))

        todo.complete()
        saved = await self._repo.save(todo)
        await self._events.publish(
            TodoCompleted(todo_id=saved.todo_id, owner_id=owner_id)
        )
        logger.info("todo_completed", todo_id=saved.todo_id, owner_id=owner_id)
        return Ok(saved)

    async def delete(
        self,
        todo_id: str,
        owner_id: str,
    ) -> Result[bool, DomainError]:
        """Delete a todo item, enforcing ownership.

        Args:
            todo_id: UUID string of the todo to delete.
            owner_id: UUID string of the requesting user (ownership check).

        Returns:
            ``Ok(True)`` if deleted, or:
            - ``Err(TodoNotFound)`` if the todo does not exist.
            - ``Err(TodoAccessDenied)`` if owned by a different user.
        """
        get_result = await self.get(todo_id, owner_id)
        if get_result.is_err():
            return get_result

        await self._repo.delete(todo_id)
        logger.info("todo_deleted", todo_id=todo_id, owner_id=owner_id)
        return Ok(True)
