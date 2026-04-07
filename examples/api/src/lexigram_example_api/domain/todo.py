"""Todo domain entity and related events.

``Todo`` is a lightweight aggregate that records a user's task.  The entity
is owned by a single user (``owner_id``) and transitions between *open* and
*completed* states via :meth:`~Todo.complete`.

Domain events raised by todo operations:
- :class:`TodoCreated` — emitted when a new todo is persisted.
- :class:`TodoCompleted` — emitted when a todo is marked complete.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from lexigram.contracts.domain import DomainEvent


# ---------------------------------------------------------------------------
# Domain events
# ---------------------------------------------------------------------------


class TodoCreated(DomainEvent):
    """Raised when a new todo item is created.

    Attributes:
        todo_id: Stable identifier of the new todo.
        title: Short description of the task.
        owner_id: Identifier of the user who owns the todo.
    """

    def __init__(
        self,
        *,
        todo_id: str,
        title: str,
        owner_id: str,
        **kwargs: object,
    ) -> None:
        """Initialise the event.

        Args:
            todo_id: The created todo's identifier.
            title: Title of the new todo.
            owner_id: Owning user's identifier.
            **kwargs: Forwarded to :class:`~lexigram.contracts.domain.DomainEvent`.
        """
        super().__init__(todo_id=todo_id, title=title, owner_id=owner_id, **kwargs)


class TodoCompleted(DomainEvent):
    """Raised when an existing todo item is marked as completed.

    Attributes:
        todo_id: Identifier of the completed todo.
        owner_id: Identifier of the owning user.
    """

    def __init__(self, *, todo_id: str, owner_id: str, **kwargs: object) -> None:
        """Initialise the event.

        Args:
            todo_id: The completed todo's identifier.
            owner_id: Owning user's identifier.
            **kwargs: Forwarded to :class:`~lexigram.contracts.domain.DomainEvent`.
        """
        super().__init__(todo_id=todo_id, owner_id=owner_id, **kwargs)


# ---------------------------------------------------------------------------
# Domain entity
# ---------------------------------------------------------------------------


@dataclass
class Todo:
    """Todo entity — tracks a single actionable task for a user.

    Attributes:
        todo_id: Stable UUID string identifier.
        title: Short headline for the task.
        description: Optional longer description.
        owner_id: Identifier of the user who owns this todo.
        completed: Whether the task has been finished.
        created_at: UTC timestamp of creation.
        updated_at: UTC timestamp of the last modification.
    """

    todo_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str | None = None
    owner_id: str = ""
    completed: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def complete(self) -> None:
        """Mark the todo as completed and update the timestamp.

        This is a domain operation — business logic lives on the entity,
        not scattered across services.
        """
        self.completed = True
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable representation of the todo.

        Returns:
            Dict with all public todo fields; timestamps as ISO-8601 strings.
        """
        return {
            "todo_id": self.todo_id,
            "title": self.title,
            "description": self.description,
            "owner_id": self.owner_id,
            "completed": self.completed,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
