"""Integration smoke tests for the lexigram-example-api lifecycle.

These tests verify that all Python modules import cleanly and that the
application's object graph can be assembled without errors.

No live infrastructure (PostgreSQL, Redis) is required — the example app
uses in-memory implementations for development and testing.
"""

from __future__ import annotations

import pytest


class TestPackageImports:
    """Verify that all top-level package modules import without error."""

    def test_main_module_importable(self) -> None:
        """The main entry-point module imports cleanly."""
        import lexigram_example_api.main  # noqa: F401

    def test_config_importable(self) -> None:
        """AppConfig imports and instantiates with defaults."""
        from lexigram_example_api.config import AppConfig

        cfg = AppConfig()
        assert cfg.port == 8000
        assert cfg.host == "0.0.0.0"

    def test_domain_importable(self) -> None:
        """Domain models import cleanly."""
        from lexigram_example_api.domain import (
            Todo,
            TodoCompleted,
            TodoCreated,
            User,
            UserCreated,
        )

        assert Todo is not None
        assert User is not None
        assert TodoCreated is not None
        assert TodoCompleted is not None
        assert UserCreated is not None

    def test_repositories_importable(self) -> None:
        """Repository classes import cleanly."""
        from lexigram_example_api.repositories import (
            InMemoryTodoRepository,
            InMemoryUserRepository,
            TodoRepositoryProtocol,
            UserRepositoryProtocol,
        )

        assert InMemoryUserRepository is not None
        assert InMemoryTodoRepository is not None
        assert UserRepositoryProtocol is not None
        assert TodoRepositoryProtocol is not None

    def test_services_importable(self) -> None:
        """Service classes import cleanly."""
        from lexigram_example_api.services import TodoService, UserService

        assert UserService is not None
        assert TodoService is not None

    def test_controllers_importable(self) -> None:
        """Controller classes import cleanly."""
        from lexigram_example_api.controllers import AuthController, TodoController

        assert AuthController is not None
        assert TodoController is not None

    def test_di_provider_importable(self) -> None:
        """AppProvider imports cleanly."""
        from lexigram_example_api.di import AppProvider

        assert AppProvider is not None

    def test_module_importable(self) -> None:
        """AppModule imports cleanly."""
        from lexigram_example_api.module import AppModule

        assert AppModule is not None


class TestDomainObjectCreation:
    """Verify domain entities and events can be instantiated."""

    def test_user_entity_creation(self) -> None:
        """User entity initialises with generated UUID."""
        from lexigram_example_api.domain.user import User

        user = User(email="test@example.com", hashed_password="hashed")
        assert user.user_id != ""
        assert user.email == "test@example.com"
        assert user.is_active is True

    def test_user_to_public_dict_excludes_password(self) -> None:
        """to_public_dict() never contains the hashed_password."""
        from lexigram_example_api.domain.user import User

        user = User(email="test@example.com", hashed_password="secret_hash")
        public = user.to_public_dict()

        assert "hashed_password" not in public
        assert public["email"] == "test@example.com"

    def test_todo_entity_creation(self) -> None:
        """Todo entity initialises with generated UUID."""
        from lexigram_example_api.domain.todo import Todo

        todo = Todo(title="Test task", owner_id="owner-123")
        assert todo.todo_id != ""
        assert todo.completed is False

    def test_todo_complete_sets_flag(self) -> None:
        """Calling complete() on a Todo sets completed=True."""
        from lexigram_example_api.domain.todo import Todo

        todo = Todo(title="Something", owner_id="owner-1")
        todo.complete()
        assert todo.completed is True

    def test_user_created_event(self) -> None:
        """UserCreated event stores user_id and email as attributes."""
        from lexigram_example_api.domain.user import UserCreated

        event = UserCreated(user_id="u-1", email="a@b.com")
        assert event.user_id == "u-1"
        assert event.email == "a@b.com"

    def test_todo_created_event(self) -> None:
        """TodoCreated event stores todo_id, title, and owner_id."""
        from lexigram_example_api.domain.todo import TodoCreated

        event = TodoCreated(todo_id="t-1", title="Test", owner_id="u-1")
        assert event.todo_id == "t-1"
        assert event.owner_id == "u-1"

    def test_todo_completed_event(self) -> None:
        """TodoCompleted event stores todo_id and owner_id."""
        from lexigram_example_api.domain.todo import TodoCompleted

        event = TodoCompleted(todo_id="t-1", owner_id="u-1")
        assert event.todo_id == "t-1"
        assert event.owner_id == "u-1"


class TestInMemoryRepositories:
    """Verify in-memory repository round-trips."""

    @pytest.mark.asyncio
    async def test_user_repo_save_and_find(self) -> None:
        """Saving a User and finding by email returns the same user."""
        from lexigram_example_api.domain.user import User
        from lexigram_example_api.repositories.user_repository import (
            InMemoryUserRepository,
        )

        repo = InMemoryUserRepository()
        user = User(email="a@b.com", hashed_password="h")
        await repo.save(user)

        found = await repo.find_by_email("a@b.com")
        assert found is not None
        assert found.user_id == user.user_id

    @pytest.mark.asyncio
    async def test_todo_repo_save_find_delete(self) -> None:
        """Saving, finding, and deleting a Todo works end-to-end."""
        from lexigram_example_api.domain.todo import Todo
        from lexigram_example_api.repositories.todo_repository import (
            InMemoryTodoRepository,
        )

        repo = InMemoryTodoRepository()
        todo = Todo(title="Test", owner_id="o-1")
        await repo.save(todo)

        found = await repo.find_by_id(todo.todo_id)
        assert found is not None
        assert found.title == "Test"

        deleted = await repo.delete(todo.todo_id)
        assert deleted is True

        not_found = await repo.find_by_id(todo.todo_id)
        assert not_found is None

    @pytest.mark.asyncio
    async def test_todo_repo_find_by_owner(self) -> None:
        """find_by_owner returns only todos for the given owner_id."""
        from lexigram_example_api.domain.todo import Todo
        from lexigram_example_api.repositories.todo_repository import (
            InMemoryTodoRepository,
        )

        repo = InMemoryTodoRepository()
        await repo.save(Todo(title="Mine", owner_id="owner-A"))
        await repo.save(Todo(title="Theirs", owner_id="owner-B"))

        mine = await repo.find_by_owner("owner-A")
        assert len(mine) == 1
        assert mine[0].title == "Mine"
