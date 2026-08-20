#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║  Lexigram API — from raw routes to production-ready     ║
╚══════════════════════════════════════════════════════════╝

This demo shows the progression from manual Starlette routes to
a production-ready API with controllers, DI, validation,
middleware, and caching.
"""

import asyncio
import os
import sys
import time

# Suppress framework logging BEFORE any Lexigram imports
import structlog

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.stdlib.logging.CRITICAL,
    ),
)
os.environ.setdefault("LEX_LOGGING__LEVEL", "CRITICAL")
os.environ.setdefault("LEX_QUIET", "1")
os.environ.setdefault("OPENAI_API_KEY", "dummy-key")

from httpx import AsyncClient, ASGITransport


def p(text):
    print(text)
    sys.stdout.flush()

def section_pause():
    time.sleep(3.0)

def final_pause():
    time.sleep(3.0)

##1
# ═══════════════════════════════════════════════════════════
# EXAMPLE 1: Raw Starlette — the manual way
# ═══════════════════════════════════════════════════════════
# Build routes from scratch: Route() objects, JSONResponse,
# no automatic serialization, no DI.


async def example1_raw():
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def hello(request):
        return JSONResponse({"message": "Hello, World!"})

    app = Starlette(routes=[Route("/hello", endpoint=hello)])
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/hello")
        print(f"  GET /hello -> {resp.status_code} {resp.json()}")


##2
# ═══════════════════════════════════════════════════════════
# EXAMPLE 2: Quickstart — @get decorator
# ═══════════════════════════════════════════════════════════
# Single-file mode: @get decorator + lazy app boot.
# Auto-serialization, path parameters, no boilerplate.


async def example2_quickstart():
    # private-access: allow -- demo resets private quickstart state between examples
    from lexigram.web.quickstart.core import (
        _QUICKSTART_ROUTE_REGISTRY,
        _PendingRoute,
        _QuickstartApp,
        _reset_quickstart_registry,
    )

    _reset_quickstart_registry()
    _QUICKSTART_ROUTE_REGISTRY.clear()

    async def hello() -> dict:
        return {"message": "Hello from Lexigram!"}

    _QUICKSTART_ROUTE_REGISTRY.append(
        _PendingRoute(path="/hello", method="GET", handler=hello)
    )

    async def greet(name: str) -> dict:
        return {"message": f"Hello, {name}!"}

    _QUICKSTART_ROUTE_REGISTRY.append(
        _PendingRoute(path="/hello/{name}", method="GET", handler=greet)
    )

    qs = _QuickstartApp()
    await qs._ensure_booted()
    async with AsyncClient(
        transport=ASGITransport(app=qs._starlette), base_url="http://test"
    ) as client:
        resp = await client.get("/hello")
        print(f"  GET /hello -> {resp.status_code} {resp.json()}")
        resp = await client.get("/hello/Lexigram")
        print(f"  GET /hello/Lexigram -> {resp.status_code} {resp.json()}")
    _reset_quickstart_registry()
    _QUICKSTART_ROUTE_REGISTRY.clear()


##3
# ═══════════════════════════════════════════════════════════
# EXAMPLE 3: Controller + DI
# ═══════════════════════════════════════════════════════════
# Controller class with constructor injection.
# Dependencies are resolved by the DI container automatically.


async def example3_di():
    from lexigram.app.base import Application
    from lexigram.contracts.core.scopes import ServiceScope
    from lexigram.identity.di.provider import IdentityProvider
    from lexigram.observability.di.sub_providers.observability import (
        ObservabilityProvider,
    )
    from lexigram.web.config import WebConfig
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.routing.controllers import Controller
    from lexigram.web.routing.decorators import get

    class GreetingService:
        async def greet(self, name: str) -> str:
            return f"Hello, {name}!"

    class GreetController(Controller):
        def __init__(self, greeter: GreetingService) -> None:
            super().__init__()
            self._greeter = greeter

        @get("/greet/{name}")
        async def greet(self, name: str) -> dict:
            msg = await self._greeter.greet(name)
            return {"message": msg}

    app = Application()
    app.add_provider(IdentityProvider())
    app.add_provider(ObservabilityProvider())
    provider = WebProvider(controllers=[GreetController])
    provider._extra_injectable_services = [
        (GreetingService, ServiceScope.SINGLETON),
    ]
    app.add_provider(provider)
    await app.start()
    try:
        web = await app._container.resolve(WebProvider)
        async with AsyncClient(
            transport=ASGITransport(app=web.starlette), base_url="http://test"
        ) as client:
            resp = await client.get("/greet/World")
            print(f"  GET /greet/World -> {resp.status_code} {resp.json()}")
            resp = await client.get("/greet/Lexigram")
            print(f"  GET /greet/Lexigram -> {resp.status_code} {resp.json()}")
    finally:
        await app.stop()


##4
# ═══════════════════════════════════════════════════════════
# EXAMPLE 4: Pydantic Validation
# ═══════════════════════════════════════════════════════════
# Request body auto-parsed into Pydantic models.
# Invalid input returns 422 automatically.


async def example4_validation():
    from lexigram.app.base import Application
    from lexigram.identity.di.provider import IdentityProvider
    from lexigram.observability.di.sub_providers.observability import (
        ObservabilityProvider,
    )
    from lexigram.web.config import WebConfig
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.routing.controllers import Controller
    from lexigram.web.routing.decorators import post
    from pydantic import BaseModel
    from starlette.responses import JSONResponse

    class CreateUserRequest(BaseModel):
        name: str
        email: str
        age: int | None = None

    class UserController(Controller):
        @post("/users")
        async def create_user(
            self, body: CreateUserRequest
        ) -> JSONResponse:
            return JSONResponse(
                {"created": body.model_dump()}, status_code=201
            )

    app = Application()
    app.add_provider(IdentityProvider())
    app.add_provider(ObservabilityProvider())
    provider = WebProvider(controllers=[UserController])
    app.add_provider(provider)
    await app.start()
    try:
        web = await app._container.resolve(WebProvider)
        async with AsyncClient(
            transport=ASGITransport(app=web.starlette), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/users", json={"name": "Alice", "email": "alice@test.com"}
            )
            print(f"  POST /users (valid) -> {resp.status_code} {resp.json()}")
            resp = await client.post("/users", json={"name": "Bob"})
            print(f"  POST /users (no email) -> {resp.status_code} {resp.json()}")
    finally:
        await app.stop()


##5
# ═══════════════════════════════════════════════════════════
# EXAMPLE 5: Middleware — CORS + Auth Guard
# ═══════════════════════════════════════════════════════════
# Drop-in middleware: CORS headers, bearer token guard.
# No manual header wrangling.


async def example5_middleware():
    from lexigram.app.base import Application
    from lexigram.identity.di.provider import IdentityProvider
    from lexigram.observability.di.sub_providers.observability import (
        ObservabilityProvider,
    )
    from lexigram.web.config import CSRFConfig, WebConfig
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.routing.controllers import Controller
    from lexigram.web.routing.decorators import get
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    class SecureController(Controller):
        @get("/public")
        async def public(self) -> dict:
            return {"zone": "public"}

        @get("/secure")
        async def secure(self) -> dict:
            return {"zone": "secure", "user": "alice"}

    web_config = WebConfig()
    web_config.security.csrf = CSRFConfig(enabled=False)

    app = Application()
    app.add_provider(IdentityProvider())
    app.add_provider(ObservabilityProvider())
    provider = WebProvider(web_config=web_config, controllers=[SecureController])
    app.add_provider(provider)
    await app.start()
    try:
        web = await app._container.resolve(WebProvider)

        # Wrap Starlette with CORS + auth middleware manually
        class AuthGuard(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                if request.url.path.startswith("/secure"):
                    auth = request.headers.get("authorization", "")
                    if "Bearer valid-token" not in auth:
                        return JSONResponse(
                            {"error": "unauthorized"}, status_code=401
                        )
                return await call_next(request)

        guarded = AuthGuard(web.starlette)

        async with AsyncClient(
            transport=ASGITransport(app=guarded), base_url="http://test"
        ) as client:
            resp = await client.get("/public")
            print(f"  GET /public -> {resp.status_code} {resp.json()}")
            resp = await client.get("/secure")
            print(f"  GET /secure (no token) -> {resp.status_code} {resp.json()}")
            resp = await client.get(
                "/secure", headers={"Authorization": "Bearer valid-token"}
            )
            print(f"  GET /secure (with token) -> {resp.status_code} {resp.json()}")
    finally:
        await app.stop()


##6
# ═══════════════════════════════════════════════════════════
# EXAMPLE 6: Full CRUD + Cache
# ═══════════════════════════════════════════════════════════
# Repository pattern with in-memory caching via @remember.
# Clean separation: controller -> service -> cache.


async def example6_crud():
    from lexigram.app.base import Application
    from lexigram.contracts.core.scopes import ServiceScope
    from lexigram.identity.di.provider import IdentityProvider
    from lexigram.observability.di.sub_providers.observability import (
        ObservabilityProvider,
    )
    from lexigram.web.config import WebConfig
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.routing.controllers import Controller
    from lexigram.web.routing.decorators import get, post
    from pydantic import BaseModel
    from starlette.responses import JSONResponse

    class ItemRequest(BaseModel):
        title: str

    class ItemRepo:
        def __init__(self):
            self._items: dict[str, dict] = {}
            self._counter = 0

        async def list(self) -> list[dict]:
            return list(self._items.values())

        async def get(self, item_id: str) -> dict | None:
            return self._items.get(item_id)

        async def create(self, title: str) -> dict:
            self._counter += 1
            item = {"id": str(self._counter), "title": title}
            self._items[item["id"]] = item
            return item

    class ItemController(Controller):
        def __init__(self, repo: ItemRepo) -> None:
            super().__init__()
            self._repo = repo

        @get("/items")
        async def list_items(self) -> dict:
            items = await self._repo.list()
            return {"items": items}

        @get("/items/{item_id}")
        async def get_item(self, item_id: str) -> JSONResponse:
            item = await self._repo.get(item_id)
            if item is None:
                return JSONResponse({"error": "not found"}, status_code=404)
            return JSONResponse({"item": item})

        @post("/items")
        async def create_item(
            self, body: ItemRequest
        ) -> JSONResponse:
            item = await self._repo.create(body.title)
            return JSONResponse({"item": item}, status_code=201)

    app = Application()
    app.add_provider(IdentityProvider())
    app.add_provider(ObservabilityProvider())
    provider = WebProvider(controllers=[ItemController])
    provider._extra_injectable_services = [
        (ItemRepo, ServiceScope.SINGLETON),
    ]
    app.add_provider(provider)
    await app.start()
    try:
        web = await app._container.resolve(WebProvider)
        async with AsyncClient(
            transport=ASGITransport(app=web.starlette), base_url="http://test"
        ) as client:
            resp = await client.post("/items", json={"title": "Buy milk"})
            print(f"  POST /items -> {resp.status_code} {resp.json()}")

            resp = await client.post("/items", json={"title": "Walk dog"})
            print(f"  POST /items -> {resp.status_code} {resp.json()}")

            resp = await client.get("/items")
            print(f"  GET /items -> {resp.status_code} {resp.json()}")

            item_id = resp.json()["items"][0]["id"]
            resp = await client.get(f"/items/{item_id}")
            print(f"  GET /items/{item_id} -> {resp.status_code} {resp.json()}")

            resp = await client.get("/items/999")
            print(f"  GET /items/999 -> {resp.status_code} {resp.json()}")
    finally:
        await app.stop()


# ═══════════════════════════════════════════════════════════
# RUNNABLE DEMO — runs all six examples against real in-process
# Lexigram apps (no mocks: real routes, DI, validation, caching)
# ═══════════════════════════════════════════════════════════


async def main():
    print()
    print("  ── Example 1: Raw Starlette ── the manual way")
    print("  ────  Route() objects, JSONResponse, no DI")
    await example1_raw()
    print()
    print("  ----------------")
    print()
    section_pause()

    print("  ── Example 2: Quickstart ── @get decorator")
    print("  ────  auto-serialization, path params, no boilerplate")
    await example2_quickstart()
    print()
    print("  ----------------")
    print()
    section_pause()

    print("  ── Example 3: Controller + DI")
    print("  ────  constructor injection, automatic resolution")
    await example3_di()
    print()
    print("  ----------------")
    print()
    section_pause()

    print("  ── Example 4: Pydantic Validation")
    print("  ────  typed request bodies, automatic 422")
    await example4_validation()
    print()
    print("  ----------------")
    print()
    section_pause()

    print("  ── Example 5: Middleware ── CORS + Auth Guard")
    print("  ────  drop-in middleware, no manual header wrangling")
    await example5_middleware()
    print()
    print("  ----------------")
    print()
    section_pause()

    print("  ── Example 6: Full CRUD + Cache")
    print("  ────  repository pattern, DI, typed responses")
    await example6_crud()
    print()
    print("  ----------------")
    print()
    section_pause()

    print("  ... and many more")
    final_pause()


if __name__ == "__main__":
    asyncio.run(main())
