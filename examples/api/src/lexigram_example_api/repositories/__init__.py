"""Repository protocols and implementations package.

Exports:
    UserRepositoryProtocol: Contract for user persistence.
    TodoRepositoryProtocol: Contract for todo persistence.
    InMemoryUserRepository: In-memory implementation for development/testing.
    InMemoryTodoRepository: In-memory implementation for development/testing.
"""

from __future__ import annotations

from lexigram_example_api.repositories.todo_repository import (
    InMemoryTodoRepository,
    TodoRepositoryProtocol,
)
from lexigram_example_api.repositories.user_repository import (
    InMemoryUserRepository,
    UserRepositoryProtocol,
)

__all__ = [
    "InMemoryTodoRepository",
    "InMemoryUserRepository",
    "TodoRepositoryProtocol",
    "UserRepositoryProtocol",
]
