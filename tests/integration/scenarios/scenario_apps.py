"""Test application factories for the cross-package scenario suite.

Each factory composes the real framework modules (SQL, Web, Events, Cache,
Audit, Auth, Tasks, Tenancy, etc.) with a small number of scenario-local
controllers/handlers so the suite exercises genuine provider boot, routing,
persistence, caching, and audit behaviour. The factories are deliberately
minimal: no domain framework beyond the modules under test is introduced
here.

Infrastructure notes:
- Database scenarios use an in-memory SQLite backend so they run without a
  live PostgreSQL service.
- Cache scenarios use the in-memory cache backend so they run without Redis.
- Task scenarios use the in-memory task queue so they run without Redis.
- Auth/audit/events scenarios use in-memory stores or the in-process bus.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.app.base import Application
from lexigram.audit import AuditModule
from lexigram.audit.config import AuditConfig
from lexigram.audit.store.memory import InMemoryAuditStore
from lexigram.audit.store.sql import entry_to_row
from lexigram.audit.verification.checksum import compute_audit_checksum
from lexigram.auth import AuthModule
from lexigram.auth.authn.jwt import JWTTokenManager
from lexigram.auth.storage.token_store import UserStoreProtocol
from lexigram.cache import CacheModule
from lexigram.contracts.audit import AuditEntry, AuditStoreProtocol
from lexigram.contracts.auth import PasswordHasherProtocol
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.contracts.infra.tasks import TaskQueueProtocol
from lexigram.di.module import DynamicModule
from lexigram.di.provider import Provider
from lexigram.events.buses import EventBusImpl
from lexigram.events.messages.event import Event
from lexigram.events.module import EventsModule
from lexigram.sql.config import DatabaseConfig
from lexigram.sql.module import DatabaseModule
from lexigram.tasks.backends.memory import MemoryTaskQueue
from lexigram.tasks.di.provider import TaskProvider
from lexigram.tasks.module import TasksModule
from lexigram.tasks.results.core import ResultStore
from lexigram.tenancy.module import TenancyModule
from lexigram.tenancy.resolution.chain import CompositeResolver
from lexigram.tenancy.types import TenantResolutionContext
from lexigram.web import delete, get, post, put
from lexigram.web.config import ServerConfig, WebConfig
from lexigram.web.module import WebModule
from lexigram.web.routing.controllers import Controller
from lexigram.web.security.config import CSRFConfig, SecurityConfig

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class _SchemaSetupProvider(Provider):
    """Create the schema a scenario needs once the database is available."""

    name = "scenario-schema-setup"

    def __init__(self, statements: list[str]) -> None:
        super().__init__()
        self._statements = statements

    async def boot(self, container: Any) -> None:
        db = await container.resolve(DatabaseProviderProtocol)
        for statement in self._statements:
            await db.execute_query(statement)


async def _json(request: Request) -> dict[str, Any]:
    """Read the JSON body as a dict, tolerating empty bodies."""
    try:
        return await request.json()
    except Exception:  # noqa: BLE001
        return {}


def _web_kwargs(controllers: list[type[Controller]]) -> dict[str, Any]:
    """Build ``WebModule.configure`` kwargs shared by the scenario apps.

    CSRF is disabled because scenario callers are anonymous test clients —
    the default ``WebConfig`` enables CSRF and would reject every mutating
    request with a 403.
    """
    return {
        "controllers": controllers,
        "web_config": WebConfig(
            server=ServerConfig(host="127.0.0.1", port=8000),
            security=SecurityConfig(
                enable_csrf=False,
                csrf=CSRFConfig(enabled=False),
            ),
        ),
    }


# ---------------------------------------------------------------------------
# Web + SQL CRUD
# ---------------------------------------------------------------------------


class ItemsController(Controller):
    """CRUD controller backed by the real DatabaseService."""

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        self._db = db

    @post("/api/v1/items", status_code=201)
    async def create(self, request: Request) -> JSONResponse:
        payload = await _json(request)
        result = await self._db.execute_insert(
            "crud_items",
            {"name": payload.get("name", "")},
        )
        row = await self._db.execute_query(
            "SELECT id, name FROM crud_items WHERE id = ?", [result.inserted_id]
        )
        body = (
            row.rows[0]
            if row.rows
            else {"id": result.inserted_id, "name": payload.get("name", "")}
        )
        return JSONResponse(body, status_code=201)

    @get("/api/v1/items")
    async def list(self, request: Request) -> JSONResponse:
        page = int(request.query_params.get("page", 1))
        size = int(request.query_params.get("size", 10))
        offset = (page - 1) * size
        result = await self._db.execute_query(
            "SELECT id, name FROM crud_items ORDER BY id LIMIT ? OFFSET ?",
            [size, offset],
        )
        count = await self._db.execute_query(
            "SELECT COUNT(*) AS total FROM crud_items"
        )
        total = count.rows[0]["total"] if count.rows else 0
        return JSONResponse(
            {"items": result.rows, "total": total, "page": page, "size": size}
        )

    @get("/api/v1/items/{item_id}")
    async def get_one(self, item_id: str) -> JSONResponse | dict[str, Any]:
        result = await self._db.execute_query(
            "SELECT id, name FROM crud_items WHERE id = ?", [int(item_id)]
        )
        if not result.rows:
            return JSONResponse({"detail": "not found"}, status_code=404)
        return result.rows[0]

    @put("/api/v1/items/{item_id}")
    async def update(self, item_id: str, request: Request) -> JSONResponse:
        payload = await _json(request)
        await self._db.execute_update(
            "crud_items",
            {"name": payload.get("name", "")},
            "id = ?",
            [int(item_id)],
        )
        result = await self._db.execute_query(
            "SELECT id, name FROM crud_items WHERE id = ?", [int(item_id)]
        )
        if not result.rows:
            return JSONResponse({"detail": "not found"}, status_code=404)
        return result.rows[0]

    @delete("/api/v1/items/{item_id}", status_code=204)
    async def delete_one(self, item_id: str) -> JSONResponse:
        await self._db.execute_delete("crud_items", "id = ?", [int(item_id)])
        return JSONResponse({}, status_code=204)


def create_crud_app() -> Application:
    """Compose a Web + SQL CRUD application backed by in-memory SQLite."""
    app = Application(name="scenario-crud")
    app.add_modules(
        [
            DatabaseModule.configure(
                DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
            ),
            WebModule.configure(**_web_kwargs([ItemsController])),
        ]
    )
    app.add_provider(
        _SchemaSetupProvider(
            [
                (
                    "CREATE TABLE IF NOT EXISTS crud_items (id INTEGER PRIMARY KEY "
                    "AUTOINCREMENT, name TEXT NOT NULL)"
                )
            ]
        )
    )
    return app


# ---------------------------------------------------------------------------
# Events + SQL
# ---------------------------------------------------------------------------


class OrderCreated(Event):
    """Order aggregate was created."""


class OrderPaid(Event):
    """Order aggregate was paid."""


class OrderConfirmed(Event):
    """Order aggregate was confirmed."""


class OrderShipped(Event):
    """Order aggregate was shipped."""


class OrderDelivered(Event):
    """Order aggregate was delivered."""


_EVENT_HANDLERS: dict[type[Event], tuple[str, str]] = {
    OrderCreated: ("INSERT INTO orders (id, status) VALUES (?, ?)", "created"),
    OrderPaid: ("UPDATE orders SET status = ? WHERE id = ?", "paid"),
    OrderConfirmed: ("UPDATE orders SET status = ? WHERE id = ?", "confirmed"),
    OrderShipped: ("UPDATE orders SET status = ? WHERE id = ?", "shipped"),
    OrderDelivered: ("UPDATE orders SET status = ? WHERE id = ?", "delivered"),
}


class _EventSubscriberProvider(Provider):
    """Subscribe the scenario handlers to the real event bus at boot."""

    name = "scenario-event-subscribers"

    async def boot(self, container: Any) -> None:
        db = await container.resolve(DatabaseProviderProtocol)
        bus = await container.resolve(EventBusImpl)

        for event_type, (sql, status) in _EVENT_HANDLERS.items():

            async def handler(
                event: Any,
                _sql: str = sql,
                _status: str = status,
            ) -> None:
                aggregate_id = str(getattr(event, "aggregate_id", ""))
                if _sql.startswith("INSERT"):
                    await db.execute_query(_sql, [aggregate_id, _status])
                else:
                    await db.execute_query(_sql, [_status, aggregate_id])

            bus.subscribe(event_type, handler)


def create_events_app() -> Application:
    """Compose Events + SQL application using the in-process event bus."""
    app = Application(name="scenario-events")
    app.add_modules(
        [
            DatabaseModule.configure(
                DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
            ),
            EventsModule.configure(),
        ]
    )
    app.add_provider(
        _SchemaSetupProvider(
            [
                (
                    "CREATE TABLE IF NOT EXISTS orders ("
                    "id TEXT PRIMARY KEY, status TEXT NOT NULL)"
                )
            ]
        )
    )
    app.add_provider(_EventSubscriberProvider())
    return app


# ---------------------------------------------------------------------------
# Web + Auth session
# ---------------------------------------------------------------------------


class SessionController(Controller):
    """Register/login/me/refresh backed by the real auth stack."""

    def __init__(
        self,
        users: UserStoreProtocol,
        hasher: PasswordHasherProtocol,
        tokens: JWTTokenManager,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    @post("/api/v1/auth/register", status_code=201)
    async def register(self, request: Request) -> JSONResponse:
        payload = await _json(request)
        email = payload.get("email", "")
        password = payload.get("password", "")

        existing = await self._users.get_user_by_email(email)
        if existing is not None:
            return JSONResponse({"detail": "email already registered"}, status_code=409)

        hashed = await self._hasher.hash(password)
        user = await self._users.create_user(
            name=email.split("@")[0],
            email=email,
            hashed_password=hashed,
        )
        auth = self._tokens.create_token(user)
        return JSONResponse(
            {
                "email": user.email,
                "user_id": user.user_id,
                "access_token": auth.token,
                "refresh_token": auth.refresh_token,
            },
            status_code=201,
        )

    @post("/api/v1/auth/login")
    async def login(self, request: Request) -> JSONResponse:
        payload = await _json(request)
        email = payload.get("email", "")
        password = payload.get("password", "")

        user = await self._users.get_user_by_email(email)
        if user is None:
            return JSONResponse({"detail": "invalid credentials"}, status_code=401)
        credentials = await self._users.get_credentials(user.user_id)
        hashed = credentials.hashed_password if credentials else None
        if hashed is None or not await self._hasher.verify(password, hashed):
            return JSONResponse({"detail": "invalid credentials"}, status_code=401)

        auth = self._tokens.create_token(user)
        return JSONResponse(
            {
                "access_token": auth.token,
                "refresh_token": auth.refresh_token,
                "token_type": auth.token_type,
            }
        )

    @get("/api/v1/me")
    async def me(self, request: Request) -> JSONResponse:
        header = request.headers.get("authorization", "")
        if not header.lower().startswith("bearer "):
            return JSONResponse({"detail": "missing token"}, status_code=401)

        token = header.split(" ", 1)[1].strip()
        result = await self._tokens.verify_token(token)
        if result.is_err():
            return JSONResponse({"detail": "invalid token"}, status_code=401)

        verified = result.unwrap()
        user = await self._users.get_user_by_id(verified.user_id)
        if user is None:
            return JSONResponse({"detail": "user not found"}, status_code=401)
        return JSONResponse({"email": user.email, "user_id": user.user_id})

    @post("/api/v1/auth/refresh")
    async def refresh(self, request: Request) -> JSONResponse:
        payload = await _json(request)
        refresh_token = payload.get("refresh_token", "")
        result = await self._tokens.refresh_token(refresh_token)
        if result.is_err():
            return JSONResponse({"detail": "invalid refresh token"}, status_code=401)

        auth = result.unwrap()
        return JSONResponse(
            {
                "access_token": auth.token,
                "refresh_token": auth.refresh_token,
                "token_type": auth.token_type,
            }
        )


def create_web_auth_app() -> Application:
    """Compose Web + Auth application using the in-memory auth stack."""
    app = Application(name="scenario-web-auth")
    app.add_modules(
        [
            AuthModule.stub(),
            WebModule.configure(**_web_kwargs([SessionController])),
        ]
    )
    return app


# ---------------------------------------------------------------------------
# Audit + SQL + Web
# ---------------------------------------------------------------------------


class _HmacMemoryAuditStore(InMemoryAuditStore):
    """In-memory store that stamps entries with their HMAC checksum.

    The package's ``InMemoryAuditStore`` intentionally does not compute
    checksums; the SQL store does. The SQL backend cannot be used in this
    scenario because its logger is wired after container validation, which
    the Web controller cannot depend on. This scenario-local subclass keeps
    the in-memory backend fast while giving the HMAC test the same
    write-then-verify semantics as ``SqlAuditStore``.
    """

    def __init__(self, key: bytes) -> None:
        super().__init__()
        self._key = key

    async def append(self, entry: AuditEntry) -> None:
        row = entry_to_row(entry)
        checksum = compute_audit_checksum(row, self._key)
        await super().append(replace(entry, checksum=checksum))


class _HmacAuditStoreProvider(Provider):
    """Overrides the audit store with the scenario's checksumming wrapper."""

    name = "scenario-hmac-audit-store"

    def __init__(self, store: _HmacMemoryAuditStore) -> None:
        super().__init__()
        self._store = store

    async def register(self, container: Any) -> None:
        container.singleton(AuditStoreProtocol, self._store)

    async def boot(self, container: Any) -> None:
        return None


class ResourcesController(Controller):
    """Resource CRUD that writes a verifiable audit entry per mutation."""

    def __init__(
        self,
        db: DatabaseProviderProtocol,
        audit: AuditStoreProtocol,
    ) -> None:
        self._db = db
        self._audit = audit

    async def _insert(self, action: str, resource_id: str, name: str) -> None:
        await self._audit.append(
            AuditEntry(
                action=action,
                actor_id="scenario-user",
                resource_type="Resource",
                resource_id=resource_id,
                new_values={"name": name},
                source="scenario",
            )
        )

    @post("/api/v1/resources", status_code=201)
    async def create(self, request: Request) -> JSONResponse:
        payload = await _json(request)
        name = payload.get("name", "")
        result = await self._db.execute_insert("audit_resources", {"name": name})
        resource_id = str(result.inserted_id)
        await self._insert("resource.create", resource_id, name)
        return JSONResponse({"id": int(resource_id), "name": name}, status_code=201)

    @put("/api/v1/resources/{resource_id}")
    async def update(self, resource_id: str, request: Request) -> JSONResponse:
        payload = await _json(request)
        name = payload.get("name", "")
        row = await self._db.execute_query(
            "SELECT id, name FROM audit_resources WHERE id = ?", [int(resource_id)]
        )
        if not row.rows:
            return JSONResponse({"detail": "not found"}, status_code=404)
        await self._db.execute_update(
            "audit_resources", {"name": name}, "id = ?", [int(resource_id)]
        )
        await self._insert("resource.update", resource_id, name)
        return {"id": int(resource_id), "name": name}

    @delete("/api/v1/resources/{resource_id}", status_code=204)
    async def delete_one(self, resource_id: str) -> JSONResponse:
        row = await self._db.execute_query(
            "SELECT name FROM audit_resources WHERE id = ?", [int(resource_id)]
        )
        name = row.rows[0]["name"] if row.rows else ""
        await self._db.execute_delete(
            "audit_resources", "id = ?", [int(resource_id)]
        )
        await self._insert("resource.delete", resource_id, name)
        return JSONResponse({}, status_code=204)


def create_audit_app() -> Application:
    """Compose Audit + SQL + Web application backed by in-memory SQLite."""
    app = Application(name="scenario-audit")
    app.add_modules(
        [
            DatabaseModule.configure(
                DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
            ),
            # The in-memory backend is used because the SQL store's logger is
            # wired during boot (after container validation), which prevents a
            # Web application from depending on ``AuditLoggerProtocol``.
            AuditModule.configure(
                config=AuditConfig(
                    store_backend="memory",
                    hmac_key=b"scenario-hmac-key",
                )
            ),
            WebModule.configure(**_web_kwargs([ResourcesController])),
        ]
    )
    app.add_provider(
        _SchemaSetupProvider(
            [
                (
                    "CREATE TABLE IF NOT EXISTS audit_resources ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)"
                )
            ]
        )
    )
    app.add_provider(_HmacAuditStoreProvider(_HmacMemoryAuditStore(b"scenario-hmac-key")))
    return app


# ---------------------------------------------------------------------------
# Web + Cache + SQL
# ---------------------------------------------------------------------------


class _CachedItemsController(Controller):
    """Cache-aside CRUD backed by the real cache and SQL providers."""

    def __init__(
        self,
        db: DatabaseProviderProtocol,
        cache: CacheBackendProtocol,
    ) -> None:
        self._db = db
        self._cache = cache

    def _key(self, item_id: int) -> str:
        return f"item:{item_id}"

    async def _read(self, item_id: int) -> JSONResponse | dict[str, Any]:
        cached = await self._cache.get(self._key(item_id))
        if cached.is_ok() and cached.unwrap_or(None) is not None:
            return JSONResponse(
                cached.unwrap(),
                headers={"X-Cache": "HIT"},
            )

        result = await self._db.execute_query(
            "SELECT id, name FROM cache_items WHERE id = ?", [item_id]
        )
        if not result.rows:
            return JSONResponse({"detail": "not found"}, status_code=404)
        row = result.rows[0]
        await self._cache.set(self._key(item_id), row)
        return JSONResponse(row, headers={"X-Cache": "MISS"})

    @post("/api/v1/items", status_code=201)
    async def create(self, request: Request) -> JSONResponse:
        payload = await _json(request)
        result = await self._db.execute_insert(
            "cache_items",
            {"name": payload.get("name", "")},
        )
        await self._cache.delete(self._key(result.inserted_id))
        row = {"id": result.inserted_id, "name": payload.get("name", "")}
        return JSONResponse(row, status_code=201)

    @get("/api/v1/items/{item_id}")
    async def get_one(self, item_id: str) -> JSONResponse | dict[str, Any]:
        return await self._read(int(item_id))

    @put("/api/v1/items/{item_id}")
    async def update(self, item_id: str, request: Request) -> JSONResponse:
        payload = await _json(request)
        await self._db.execute_update(
            "cache_items",
            {"name": payload.get("name", "")},
            "id = ?",
            [int(item_id)],
        )
        await self._cache.delete(self._key(int(item_id)))
        # Return the fresh row directly so the next GET observes the
        # invalidation as a cache MISS instead of being served from the
        # entry re-populated here.
        result = await self._db.execute_query(
            "SELECT id, name FROM cache_items WHERE id = ?", [int(item_id)]
        )
        if not result.rows:
            return JSONResponse({"detail": "not found"}, status_code=404)
        return result.rows[0]


def create_cache_app() -> Application:
    """Compose Web + Cache + SQL cache-aside app with in-memory cache."""
    app = Application(name="scenario-cache")
    app.add_modules(
        [
            DatabaseModule.configure(
                DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
            ),
            CacheModule.stub(),
            WebModule.configure(**_web_kwargs([_CachedItemsController])),
        ]
    )
    app.add_provider(
        _SchemaSetupProvider(
            [
                (
                    "CREATE TABLE IF NOT EXISTS cache_items ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)"
                )
            ]
        )
    )
    return app


# ---------------------------------------------------------------------------
# Tasks + Queue (in-memory)
# ---------------------------------------------------------------------------


class _TasksHandlerProvider(Provider):
    """Register deterministic task handlers on the real handler registry."""

    name = "scenario-task-handlers"

    def __init__(self, flaky_attempts: dict[str, int]) -> None:
        super().__init__()
        self._flaky_attempts = flaky_attempts

    async def boot(self, container: Any) -> None:
        from lexigram.tasks.execution.registry import HandlerRegistry

        registry = await container.resolve(HandlerRegistry)

        async def send_welcome_email(**kwargs: Any) -> dict[str, str]:
            return {"sent": kwargs.get("user_id", "")}

        async def flaky_task(**kwargs: Any) -> str:
            attempts = self._flaky_attempts
            attempts["count"] = attempts.get("count", 0) + 1
            if attempts["count"] <= int(kwargs.get("fail_times", 1)):
                raise RuntimeError("flaky failure")
            return "ok"

        async def always_fail_task(**kwargs: Any) -> None:
            raise RuntimeError("always fails")

        registry.register("send_welcome_email", send_welcome_email)
        registry.register("flaky_task", flaky_task)
        registry.register("always_fail_task", always_fail_task)

        from lexigram.tasks.di.provider import TaskProvider

        provider = await container.resolve(TaskProvider)
        provider.refresh_worker_handlers()


def _tasks_module() -> DynamicModule:
    """Return a TasksModule composition using the real in-memory queue."""
    queue = MemoryTaskQueue()
    provider = TaskProvider(
        queue=queue,
        worker_count=1,
        enable_scheduler=False,
    )
    return DynamicModule(
        module=TasksModule,
        providers=[provider],
        exports=[TaskQueueProtocol, ResultStore],
    )


def create_tasks_app() -> Application:
    """Compose a Tasks application using the in-memory task queue."""
    app = Application(name="scenario-tasks")
    app.add_modules([_tasks_module()])
    app.add_provider(_TasksHandlerProvider({}))
    return app


# ---------------------------------------------------------------------------
# Tenancy + SQL + Web
# ---------------------------------------------------------------------------


class _TenancyController(Controller):
    """Multi-tenant resources backed by real tenancy resolution."""

    def __init__(
        self,
        db: DatabaseProviderProtocol,
        resolver: CompositeResolver,
    ) -> None:
        self._db = db
        self._resolver = resolver

    async def _tenant_id(self, request: Request) -> str:
        headers = dict(request.headers)
        tenant_id = await self._resolver.resolve(
            TenantResolutionContext(headers=headers, path=request.url.path)
        )
        return tenant_id or "anonymous"

    @post("/api/v1/resources", status_code=201)
    async def create(self, request: Request) -> JSONResponse:
        tenant_id = await self._tenant_id(request)
        payload = await _json(request)
        result = await self._db.execute_insert(
            "tenant_resources",
            {"tenant_id": tenant_id, "name": payload.get("name", "")},
        )
        return JSONResponse(
            {"id": result.inserted_id, "name": payload.get("name", "")},
            status_code=201,
        )

    @get("/api/v1/resources")
    async def list(self, request: Request) -> JSONResponse:
        tenant_id = await self._tenant_id(request)
        result = await self._db.execute_query(
            "SELECT id, name FROM tenant_resources WHERE tenant_id = ? "
            "ORDER BY id",
            [tenant_id],
        )
        return JSONResponse({"items": result.rows})

    @get("/api/v1/resources/{resource_id}")
    async def get_one(self, resource_id: str, request: Request) -> JSONResponse:
        tenant_id = await self._tenant_id(request)
        result = await self._db.execute_query(
            "SELECT id, name FROM tenant_resources "
            "WHERE id = ? AND tenant_id = ?",
            [int(resource_id), tenant_id],
        )
        if not result.rows:
            return JSONResponse({"detail": "not found"}, status_code=404)
        return result.rows[0]


def create_tenancy_app() -> Application:
    """Compose Tenancy + SQL + Web app with header-based tenant resolution."""
    app = Application(name="scenario-tenancy")
    app.add_modules(
        [
            DatabaseModule.configure(
                DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
            ),
            TenancyModule.stub(),
            WebModule.configure(**_web_kwargs([_TenancyController])),
        ]
    )
    app.add_provider(
        _SchemaSetupProvider(
            [
                (
                    "CREATE TABLE IF NOT EXISTS tenant_resources ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "tenant_id TEXT NOT NULL, name TEXT NOT NULL)"
                )
            ]
        )
    )
    return app
