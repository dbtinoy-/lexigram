"""
Example: Result[T, E] Error Handling

Demonstrates the Result pattern for handling expected, recoverable errors.
- Define domain errors as exceptions
- Return Result[T, E] from operations
- Handle both success and error paths
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from lexigram.app import Application
from lexigram.di import Provider, Module
from lexigram.di.module import module as di_module
from lexigram.result import Result, Ok, Err


class UserNotFound(Exception):
    """Domain error: User not found."""
    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(f"User {user_id} not found")


class User:
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name


class UserRepositoryProtocol(Protocol):
    async def find(self, user_id: str) -> Result[User, UserNotFound]: ...


class InMemoryUserRepository:
    def __init__(self):
        self.users = {
            "u1": User("u1", "Alice"),
            "u2": User("u2", "Bob"),
        }

    async def find(self, user_id: str) -> Result[User, UserNotFound]:
        user = self.users.get(user_id)
        if user:
            return Ok(user)
        return Err(UserNotFound(user_id))


class UserService:
    def __init__(self, repo: UserRepositoryProtocol):
        self.repo = repo

    async def greet_user(self, user_id: str) -> str:
        result = await self.repo.find(user_id)
        if result.is_ok():
            user = result.unwrap()
            return f"Hello, {user.name}!"
        else:
            error = result.unwrap_err()
            return f"Error: {error}"


class UserProvider(Provider):
    name = "user"

    async def register(self, container):
        container.singleton(UserRepositoryProtocol, InMemoryUserRepository)
        container.singleton(UserService)


@di_module(providers=[UserProvider], exports=[UserService])
class UserModule(Module):
    pass


async def main():
    async with Application.boot(modules=[UserModule]) as app:
        service = await app.container.resolve(UserService)

        # Success case
        msg = await service.greet_user("u1")
        print(f"✓ {msg}")

        # Error case
        msg = await service.greet_user("u99")
        print(f"✗ {msg}")


if __name__ == "__main__":
    asyncio.run(main())
