"""Todo repository — protocol contract and in-memory implementation.

The :class:`TodoRepositoryProtocol` defines the persistence interface for
:class:`~lexigram_example_api.domain.Todo` entities.  Services depend on
the *protocol*, never the concrete implementation, honoring IoC.

:class:`InMemoryTodoRepository` provides a zero-infrastructure implementation
suitable for integration tests and local development.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lexigram.logging import get_logger

from lexigram_example_api.domain.todo import Todo

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


@runtime_checkable
class TodoRepositoryProtocol(Protocol):
    """Persistence contract for :class:`~lexigram_example_api.domain.Todo`.

    All methods are async to accommodate SQL/Redis/HTTP-backed
    implementations without changing call-sites.
    """

    async def find_by_id(self, todo_id: str) -> Todo | None:
        """Look up a todo by its stable identifier.

        Args:
            todo_id: UUID string of the todo to retrieve.

        Returns:
            The matching :class:`~lexigram_example_api.domain.Todo`, or
            ``None`` if not found.
        """
        ...

    async def find_by_owner(self, owner_id: str) -> list[Todo]:
        """Return all todos owned by a given user.

        Args:
            owner_id: UUID string of the owning user.

        Returns:
            List of :class:`~lexigram_example_api.domain.Todo` instances,
            ordered by creation time (newest last).  Empty list if none.
        """
        ...

    async def save(self, todo: Todo) -> Todo:
        """Persist a todo entity (insert or upsert).

        Args:
            todo: The entity to persist.  The ``todo_id`` field is used as
                the primary key.

        Returns:
            The persisted entity.
        """
        ...

    async def delete(self, todo_id: str) -> bool:
        """Remove a todo by identifier.

        Args:
            todo_id: UUID string of the todo to remove.

        Returns:
            ``True`` if the todo existed and was removed; ``False`` otherwise.
        """
        ...


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------


class InMemoryTodoRepository:
    """Thread-safe, in-process todo repository backed by a single dict.

    Intended for unit/integration testing and local development sessions.
    Data is lost when the process exits.
    """

    def __init__(self) -> None:
        """Initialise an empty in-memory store."""
        self._store: dict[str, Todo] = {}

    async def find_by_id(self, todo_id: str) -> Todo | None:
        """Look up a todo by its stable identifier.

        Args:
            todo_id: UUID string to search.

        Returns:
            Matching todo or ``None``.
        """
        return self._store.get(todo_id)

    async def find_by_owner(self, owner_id: str) -> list[Todo]:
        """Return all todos for a given owner sorted by creation time.

        Args:
            owner_id: UUID string of the owning user.

        Returns:
            Sorted list of todos (oldest first).
        """
        return sorted(
            (t for t in self._store.values() if t.owner_id == owner_id),
            key=lambda t: t.created_at,
        )

    async def save(self, todo: Todo) -> Todo:
        """Upsert a todo into the internal store.

        Args:
            todo: Todo entity to persist.

        Returns:
            The same entity (pass-through for interface consistency).
        """
        self._store[todo.todo_id] = todo
        logger.debug("todo_saved", todo_id=todo.todo_id, owner_id=todo.owner_id)
        return todo

    async def delete(self, todo_id: str) -> bool:
        """Remove a todo by identifier.

        Args:
            todo_id: UUID string of the todo to remove.

        Returns:
            ``True`` if deleted; ``False`` if it did not exist.
        """
        existed = todo_id in self._store
        self._store.pop(todo_id, None)
        if existed:
            logger.debug("todo_deleted", todo_id=todo_id)
        return existed
