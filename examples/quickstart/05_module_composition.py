"""
Example: Module Composition

Demonstrates how to build an app from multiple independent modules.
- Define separate modules for different concerns
- Each module has its own provider and exports
- Application composes multiple modules
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from lexigram.app import Application
from lexigram.di import Provider, Module
from lexigram.di.module import module as di_module


# ============================================================================
# Module 1: Logging
# ============================================================================

class LoggerProtocol(Protocol):
    def info(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...


class Logger:
    def info(self, message: str) -> None:
        print(f"[INFO] {message}")

    def error(self, message: str) -> None:
        print(f"[ERROR] {message}")


class LoggingProvider(Provider):
    name = "logging"

    async def register(self, container):
        container.singleton(LoggerProtocol, Logger)


@di_module(providers=[LoggingProvider], exports=[LoggerProtocol])
class LoggingModule(Module):
    pass


# ============================================================================
# Module 2: Database (simulated)
# ============================================================================

class DatabaseProtocol(Protocol):
    async def query(self, sql: str) -> list[dict]: ...


class FakeDatabase:
    async def query(self, sql: str) -> list[dict]:
        return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


class DatabaseProvider(Provider):
    name = "database"

    async def register(self, container):
        container.singleton(DatabaseProtocol, FakeDatabase)


@di_module(providers=[DatabaseProvider], exports=[DatabaseProtocol])
class DatabaseModule(Module):
    pass


# ============================================================================
# Module 3: UserService (depends on both)
# ============================================================================

class UserServiceProtocol(Protocol):
    async def list_users(self) -> list[dict]: ...


class UserService:
    def __init__(self, logger: LoggerProtocol, db: DatabaseProtocol):
        self.logger = logger
        self.db = db

    async def list_users(self) -> list[dict]:
        self.logger.info("Fetching users from database")
        users = await self.db.query("SELECT * FROM users")
        self.logger.info(f"Found {len(users)} users")
        return users


class UserServiceProvider(Provider):
    name = "user_service"

    async def register(self, container):
        container.singleton(UserServiceProtocol, UserService)


@di_module(
    providers=[UserServiceProvider],
    exports=[UserServiceProtocol],
    imports=[LoggingModule, DatabaseModule]  # Declare dependencies on other modules
)
class UserServiceModule(Module):
    pass


async def main():
    # Compose all modules
    async with Application.boot(
        modules=[LoggingModule, DatabaseModule, UserServiceModule]
    ) as app:
        service = await app.container.resolve(UserServiceProtocol)
        users = await service.list_users()

        for user in users:
            print(f"  → {user['name']}")


if __name__ == "__main__":
    asyncio.run(main())
