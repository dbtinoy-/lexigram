"""Unit tests for TodoService.

Tests exercise the service through its Protocol contracts — no real
infrastructure is used.  All dependencies are mocked at the boundary.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram_example_api.domain.todo import Todo
from lexigram_example_api.repositories.todo_repository import InMemoryTodoRepository
from lexigram_example_api.services.todo_service import (
    TodoAccessDenied,
    TodoAlreadyCompleted,
    TodoNotFound,
    TodoService,
)


def _make_service(
    todo_repo: InMemoryTodoRepository,
    mock_event_publisher: MagicMock,
) -> TodoService:
    """Factory that wires a TodoService from test doubles.

    Args:
        todo_repo: In-memory todo repository.
        mock_event_publisher: Mock event publisher.

    Returns:
        Configured :class:`~lexigram_example_api.services.todo_service.TodoService`.
    """
    return TodoService(repo=todo_repo, event_publisher=mock_event_publisher)


OWNER_ID = "user-abc"
OTHER_OWNER_ID = "user-xyz"


class TestTodoServiceCreate:
    """Tests for TodoService.create."""

    @pytest.mark.asyncio
    async def test_create_returns_ok_with_todo(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Creating a todo returns Ok(Todo) with the persisted entity."""
        service = _make_service(todo_repo, mock_event_publisher)

        result = await service.create(
            owner_id=OWNER_ID,
            title="Buy groceries",
            description="Milk, eggs, bread",
        )

        assert result.is_ok()
        todo = result.unwrap()
        assert todo.title == "Buy groceries"
        assert todo.description == "Milk, eggs, bread"
        assert todo.owner_id == OWNER_ID
        assert not todo.completed
        assert todo.todo_id != ""

    @pytest.mark.asyncio
    async def test_create_publishes_todo_created_event(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """A TodoCreated domain event is published after creation."""
        service = _make_service(todo_repo, mock_event_publisher)

        await service.create(owner_id=OWNER_ID, title="Write tests")

        mock_event_publisher.publish.assert_called_once()
        event = mock_event_publisher.publish.call_args[0][0]
        assert type(event).__name__ == "TodoCreated"
        assert event.owner_id == OWNER_ID
        assert event.title == "Write tests"

    @pytest.mark.asyncio
    async def test_create_without_description(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Creating a todo without a description is allowed."""
        service = _make_service(todo_repo, mock_event_publisher)

        result = await service.create(owner_id=OWNER_ID, title="Quick task")

        assert result.is_ok()
        assert result.unwrap().description is None


class TestTodoServiceListByOwner:
    """Tests for TodoService.list_by_owner."""

    @pytest.mark.asyncio
    async def test_list_empty_returns_ok_empty_list(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Listing todos for a user with none returns Ok([])."""
        service = _make_service(todo_repo, mock_event_publisher)

        result = await service.list_by_owner(OWNER_ID)

        assert result.is_ok()
        assert result.unwrap() == []

    @pytest.mark.asyncio
    async def test_list_returns_only_owner_todos(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Todos belonging to other users are not returned."""
        service = _make_service(todo_repo, mock_event_publisher)

        await service.create(owner_id=OWNER_ID, title="My todo")
        await service.create(owner_id=OTHER_OWNER_ID, title="Other todo")

        result = await service.list_by_owner(OWNER_ID)

        assert result.is_ok()
        todos = result.unwrap()
        assert len(todos) == 1
        assert todos[0].title == "My todo"


class TestTodoServiceGet:
    """Tests for TodoService.get."""

    @pytest.mark.asyncio
    async def test_get_existing_own_todo_returns_ok(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Getting an owned todo returns Ok(Todo)."""
        service = _make_service(todo_repo, mock_event_publisher)
        created = (await service.create(owner_id=OWNER_ID, title="Task")).unwrap()

        result = await service.get(created.todo_id, OWNER_ID)

        assert result.is_ok()
        assert result.unwrap().todo_id == created.todo_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_err_not_found(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Getting a non-existent todo returns Err(TodoNotFound)."""
        service = _make_service(todo_repo, mock_event_publisher)

        result = await service.get("nonexistent-id", OWNER_ID)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), TodoNotFound)

    @pytest.mark.asyncio
    async def test_get_other_owner_todo_returns_err_access_denied(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Getting another user's todo returns Err(TodoAccessDenied)."""
        service = _make_service(todo_repo, mock_event_publisher)
        created = (
            await service.create(owner_id=OTHER_OWNER_ID, title="Their task")
        ).unwrap()

        result = await service.get(created.todo_id, OWNER_ID)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), TodoAccessDenied)


class TestTodoServiceComplete:
    """Tests for TodoService.complete."""

    @pytest.mark.asyncio
    async def test_complete_open_todo_returns_ok(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Completing an open todo returns Ok(Todo) with completed=True."""
        service = _make_service(todo_repo, mock_event_publisher)
        todo = (await service.create(owner_id=OWNER_ID, title="Do laundry")).unwrap()

        result = await service.complete(todo.todo_id, OWNER_ID)

        assert result.is_ok()
        completed = result.unwrap()
        assert completed.completed is True

    @pytest.mark.asyncio
    async def test_complete_publishes_todo_completed_event(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """A TodoCompleted domain event is published on completion."""
        service = _make_service(todo_repo, mock_event_publisher)
        todo = (await service.create(owner_id=OWNER_ID, title="Finish report")).unwrap()
        mock_event_publisher.publish.reset_mock()

        await service.complete(todo.todo_id, OWNER_ID)

        mock_event_publisher.publish.assert_called_once()
        event = mock_event_publisher.publish.call_args[0][0]
        assert type(event).__name__ == "TodoCompleted"
        assert event.todo_id == todo.todo_id

    @pytest.mark.asyncio
    async def test_complete_already_completed_returns_err(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Completing an already-completed todo returns Err(TodoAlreadyCompleted)."""
        service = _make_service(todo_repo, mock_event_publisher)
        todo = (await service.create(owner_id=OWNER_ID, title="Done task")).unwrap()
        await service.complete(todo.todo_id, OWNER_ID)

        result = await service.complete(todo.todo_id, OWNER_ID)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), TodoAlreadyCompleted)

    @pytest.mark.asyncio
    async def test_complete_other_owner_todo_returns_err_access_denied(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Completing another user's todo returns Err(TodoAccessDenied)."""
        service = _make_service(todo_repo, mock_event_publisher)
        todo = (
            await service.create(owner_id=OTHER_OWNER_ID, title="Their work")
        ).unwrap()

        result = await service.complete(todo.todo_id, OWNER_ID)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), TodoAccessDenied)


class TestTodoServiceDelete:
    """Tests for TodoService.delete."""

    @pytest.mark.asyncio
    async def test_delete_own_todo_returns_ok_true(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Deleting an owned todo returns Ok(True)."""
        service = _make_service(todo_repo, mock_event_publisher)
        todo = (await service.create(owner_id=OWNER_ID, title="Stale task")).unwrap()

        result = await service.delete(todo.todo_id, OWNER_ID)

        assert result.is_ok()
        assert result.unwrap() is True

    @pytest.mark.asyncio
    async def test_delete_removes_todo_from_list(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """After deletion the todo no longer appears in list_by_owner."""
        service = _make_service(todo_repo, mock_event_publisher)
        todo = (await service.create(owner_id=OWNER_ID, title="Remove me")).unwrap()

        await service.delete(todo.todo_id, OWNER_ID)
        list_result = await service.list_by_owner(OWNER_ID)

        assert list_result.unwrap() == []

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_err_not_found(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Deleting a non-existent todo returns Err(TodoNotFound)."""
        service = _make_service(todo_repo, mock_event_publisher)

        result = await service.delete("ghost-id", OWNER_ID)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), TodoNotFound)

    @pytest.mark.asyncio
    async def test_delete_other_owner_todo_returns_err_access_denied(
        self,
        todo_repo: InMemoryTodoRepository,
        mock_event_publisher: MagicMock,
    ) -> None:
        """Attempting to delete another user's todo returns Err(TodoAccessDenied)."""
        service = _make_service(todo_repo, mock_event_publisher)
        todo = (
            await service.create(owner_id=OTHER_OWNER_ID, title="Not yours")
        ).unwrap()

        result = await service.delete(todo.todo_id, OWNER_ID)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), TodoAccessDenied)
