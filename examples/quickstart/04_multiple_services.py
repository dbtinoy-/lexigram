"""
Example: Multiple Services (Service Composition)

Demonstrates how multiple services can depend on each other.
- Define multiple protocols
- Inject service into service
- Build composable business logic
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from lexigram.app import Application
from lexigram.di import Provider, Module
from lexigram.di.module import module as di_module


class LoggerProtocol(Protocol):
    def log(self, message: str) -> None: ...


class SimpleLogger:
    def log(self, message: str) -> None:
        print(f"[LOG] {message}")


class GreeterProtocol(Protocol):
    async def greet(self, name: str) -> str: ...


class Greeter:
    def __init__(self, logger: LoggerProtocol):
        self.logger = logger

    async def greet(self, name: str) -> str:
        self.logger.log(f"Greeting {name}")
        return f"Hello, {name}!"


class UserServiceProtocol(Protocol):
    async def welcome(self, name: str) -> None: ...


class UserService:
    def __init__(self, logger: LoggerProtocol, greeter: GreeterProtocol):
        self.logger = logger
        self.greeter = greeter

    async def welcome(self, name: str) -> None:
        self.logger.log(f"Starting welcome flow for {name}")
        msg = await self.greeter.greet(name)
        print(msg)
        self.logger.log(f"Welcome flow complete")


class ApplicationProvider(Provider):
    name = "application"

    async def register(self, container):
        container.singleton(LoggerProtocol, SimpleLogger)
        container.singleton(GreeterProtocol, Greeter)
        container.singleton(UserServiceProtocol, UserService)


@di_module(providers=[ApplicationProvider], exports=[UserServiceProtocol])
class ApplicationModule(Module):
    pass


async def main():
    async with Application.boot(modules=[ApplicationModule]) as app:
        service = await app.container.resolve(UserServiceProtocol)
        await service.welcome("Alice")
        await service.welcome("Bob")


if __name__ == "__main__":
    asyncio.run(main())
