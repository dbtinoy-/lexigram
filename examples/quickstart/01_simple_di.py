#!/usr/bin/env python3
"""
Example 1: Simple Dependency Injection
======================================

This example demonstrates the core Lexigram pattern:
1. Define a contract (Protocol)
2. Implement the contract
3. Register it in a provider
4. Inject it via constructor
5. Resolve and use

Run: python examples/01_simple_di.py
"""

import asyncio
from typing import Protocol

from lexigram.app import Application
from lexigram.di import Provider, Module
from lexigram.di.module import module


# 1. Define a contract (interface)
class GreeterProtocol(Protocol):
    """Contract: something that can greet."""
    async def greet(self, name: str) -> str: ...


# 2. Implement it
class Greeter:
    """Concrete implementation of GreeterProtocol."""
    async def greet(self, name: str) -> str:
        return f"Hello, {name}!"


# 3. Register in a provider
class GreeterProvider(Provider):
    """Register Greeter and UserService in the container."""
    name = "greeter"

    async def register(self, container) -> None:
        container.singleton(GreeterProtocol, Greeter)
        container.singleton(UserService)  # Auto-wire UserService


# 3b. Wrap provider in a module
@module(providers=[GreeterProvider], exports=[GreeterProtocol])
class GreeterModule(Module):
    """Module that exports the GreeterProtocol."""
    pass


# 4. Inject it (constructor injection)
class UserService:
    """Service that depends on GreeterProtocol."""
    def __init__(self, greeter: GreeterProtocol):
        self.greeter = greeter

    async def welcome(self, name: str) -> str:
        return await self.greeter.greet(name)


# 5. Resolve and use
async def main() -> None:
    async with Application.boot(modules=[GreeterModule]) as app:
        service = await app.container.resolve(UserService)
        msg = await service.welcome("Alice")
        print(msg)  # "Hello, Alice!"


if __name__ == "__main__":
    asyncio.run(main())
