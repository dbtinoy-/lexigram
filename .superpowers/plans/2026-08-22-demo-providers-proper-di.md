# Demo Providers Proper-DI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the four ad-hoc patterns found in demo providers (provider-held state + stringly factories, seeding logic in `boot()`, router surgery, inline-instance registration) with the container's sanctioned mechanisms.

**Architecture:** The DI container's factory protocol is richer than the demos assume: `singleton(Key, factory=...)` invokes the factory **at resolve time** as `impl(resolver)` and **awaits async results** (`core/lexigram/src/lexigram/di/resolution/resolver.py:163-167`). So every "boot-built collaborator" can become a typed async factory method on the provider — no `None`-guards, no `getattr(self, kind)` strings, no pre-boot state. Seeding moves into dedicated seed services (AGENTS.md §4.3 forbids business logic on Providers). The ops_console WebSocket mounts through the sanctioned `@websocket` decorator on a Controller method instead of appending to `web.starlette.router.routes`.

**Tech Stack:** Lexigram DI (`ContainerRegistrarProtocol`/`ContainerResolverProtocol`), lexigram-web routing decorators, pytest via `make test-demos`, ruff/mypy.

**Spec:** Audit findings of 2026-08-22 (this session): container semantics verified in source; `AuthConfig.users/roles` confirmed inert in lexigram-auth (framework gap — marked with TODOs, not fixed here).

## Global Constraints

- Shared working tree: pathspec-only commits (`git commit <paths> -m "<emoji> <type>(<scope>): ..."`); never stash/reset --hard/clean; other lanes active (auth-mfa is untracked WIP — **do not touch `demos/auth-mfa/**`**).
- Behavior lock: every task must keep its demo's full test suite passing unchanged (same test count) and `make smoke-demos` exit 0.
- LOC ≤500 per touched file; run `uv run python dev/check_loc_limit.py --root .` at each task end (expect `0 new, 0 stale`).
- Do not modify framework packages (`packages/`, `core/`) — the two framework gaps met here get TODO markers for upstream follow-up.

---

### Task 1: resilient-rates — stateless provider, resolver-receiving factory

**Files:**
- Modify: `demos/resilient-rates/src/rates/di/provider.py`

**Interfaces:**
- Produces: same registrations as before (`FaultController`, `SimulatedRatesProvider`, `RatesService` keys). Provider becomes stateless; `_get_service` deleted.

- [ ] **Step 1: Rewrite the provider**

Replace the class body after the docstring with:

```python
class RatesProvider(Provider):
    """Register the rate desk services as container-managed singletons."""

    name = "rates"

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind singletons; RatesService builds lazily from booted deps."""
        faults = FaultController()
        container.singleton(FaultController, instance=faults)
        container.singleton(
            SimulatedRatesProvider,
            instance=SimulatedRatesProvider(faults=faults),
        )
        # Cache backend and resilience pipeline are wired by the imported
        # modules' own providers; the lazy factory below resolves them at
        # first use — after every provider has booted.
        container.singleton(RatesService, factory=self._build_service)

    async def _build_service(
        self, resolver: ContainerResolverProtocol
    ) -> RatesService:
        """Assemble ``RatesService`` from its booted collaborators."""
        return RatesService(
            cache=await resolver.resolve(CacheBackendProtocol),
            pipeline_factory=await resolver.resolve(
                ResiliencePipelineFactoryProtocol
            ),
            provider=await resolver.resolve(SimulatedRatesProvider),
            faults=await resolver.resolve(FaultController),
        )
```

Delete: `__init__`, `_get_service`, old `boot()`.

- [ ] **Step 2: Verify**

```bash
uv run pytest demos/resilient-rates/tests -q -m "not integration" --no-cov   # expect: all pass, same count (7)
cd demos/resilient-rates && PYTHONPATH=src timeout 120 ../../.venv/bin/python -m rates demo >/dev/null && cd -   # exit 0
```

- [ ] **Step 3: Commit**

```bash
git add demos/resilient-rates/src/rates/di/provider.py
git commit demos/resilient-rates/src/rates/di/provider.py -m "♻️ refactor(demos): rates provider uses resolver-receiving service factory"
```

---

### Task 2: event-driven-orders — class-style registrations + typed API factory

**Files:**
- Modify: `demos/event-driven-orders/src/orders/di/provider.py`

**Interfaces:**
- Produces: identical bus wiring and `OrdersApi` key; no `self._api` state.

- [ ] **Step 1: Rewrite**

```python
class OrdersProvider(Provider):
    """Provide the order write/read sides and their bus wiring."""

    name = "orders"
    priority = ProviderPriority.NORMAL

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(OrderRepository, OrderRepository)
        container.singleton(OrdersView, OrdersView)
        container.singleton(NotificationHandler, NotificationHandler)
        container.singleton(Outbox, Outbox)
        # The facade needs buses wired in boot(); build lazily.
        container.singleton(OrdersApi, factory=self._build_api)

    async def _build_api(
        self, resolver: ContainerResolverProtocol
    ) -> OrdersApi:
        """Register handlers/subscriptions, then assemble the facade."""
        repository = await resolver.resolve(OrderRepository)
        outbox = await resolver.resolve(Outbox)
        command_bus = await resolver.resolve(CommandBusImpl)
        command_bus.register(
            PlaceOrder,
            PlaceOrderHandler(repository=repository, outbox=outbox),
        )
        command_bus.register(
            PayOrder,
            PayOrderHandler(repository=repository, outbox=outbox),
        )
        command_bus.register(
            ShipOrder,
            ShipOrderHandler(repository=repository, outbox=outbox),
        )
        event_bus = await resolver.resolve(EventBusProtocol)
        view = await resolver.resolve(OrdersView)
        notifier = await resolver.resolve(NotificationHandler)
        event_bus.subscribe(OrderPlaced, view.on_order_placed)
        event_bus.subscribe(OrderPaid, view.on_order_paid)
        event_bus.subscribe(OrderShipped, view.on_order_shipped)
        event_bus.subscribe(OrderPlaced, notifier.on_order_placed)
        event_bus.subscribe(OrderShipped, notifier.on_order_shipped)
        return OrdersApi(
            command_bus=command_bus,
            event_bus=event_bus,
            repository=repository,
            view=view,
            outbox=outbox,
        )

    async def shutdown(self) -> None:
        """Nothing to tear down; the demo is fully in-memory."""
```

Delete `__init__`, `_get_api`, old `boot()`. Note: registering classes (not inline instances) lets the container auto-wire/auto-detect and keeps style uniform.

Caveat: if `CommandBusImpl` is NOT a registered key in this app (check `module.py` imports), keep its resolution exactly as today — it already resolves in current `boot()`, so it is registered.

- [ ] **Step 2: Verify**

```bash
uv run pytest demos/event-driven-orders/tests -q -m "not integration" --no-cov   # all pass, same count
cd demos/event-driven-orders && PYTHONPATH=src timeout 120 ../../.venv/bin/python -m orders demo >/dev/null && cd -
```

- [ ] **Step 3: Commit**

```bash
git add demos/event-driven-orders/src/orders/di/provider.py
git commit demos/event-driven-orders/src/orders/di/provider.py -m "♻️ refactor(demos): orders provider uses class bindings and typed api factory"
```

---

### Task 3: auth-web — seed service extraction + resolver-receiving factories

**Files:**
- Create: `demos/auth-web/src/auth_web/services/seed.py`
- Modify: `demos/auth-web/src/auth_web/di/provider.py`
- Test: existing `demos/auth-web/tests/` must pass unchanged.

**Interfaces:**
- Produces: `DemoSeedService(user_service, authz)` with `async run() -> None`; constants `DEMO_EMAIL`, `DEMO_PASSWORD`, `ROLE_DEFINITIONS`, `build_auth_config()` keep their current import locations (`auth_web.di.provider` re-exports).

- [ ] **Step 1: Create the seed service**

Move `ROLE_DEFINITIONS`, `DEMO_EMAIL`, `DEMO_PASSWORD` and the user/role seeding block (currently inside `boot()`) into `services/seed.py`:

```python
"""One-shot demo data seeding for the auth web demo."""

from __future__ import annotations

from lexigram.auth.authn.user_service import UserService
from lexigram.auth.authz.service import AuthorizationService
from lexigram.logging import get_logger

logger = get_logger(__name__)

DEMO_EMAIL = "admin@auth.demo"
DEMO_PASSWORD = "Demo-Password-1"

# Single source of truth for RBAC seeding. AuthConfig.roles is inert today
# (the authorization sub-provider never reads it), so these are pushed into
# AuthorizationService.set_roles() here.
# TODO(framework): consume AuthConfig.users/roles so demos stop hand-seeding.
ROLE_DEFINITIONS: dict[str, dict[str, object]] = {
    "viewer": {"name": "viewer", "permissions": ["profile:read"]},
    "editor": {
        "name": "editor",
        "permissions": ["articles:*"],
        "inherits": ["viewer"],
    },
    "admin": {"name": "admin", "permissions": ["*"], "inherits": ["editor"]},
}


class DemoSeedService:
    """Seed the demo account and RBAC roles exactly once."""

    def __init__(
        self, user_service: UserService, authz: AuthorizationService
    ) -> None:
        self._user_service = user_service
        self._authz = authz

    async def run(self) -> None:
        """Create the demo admin if absent and install role definitions."""
        seeded = await self._user_service.create_user(
            name="Demo Admin",
            email=DEMO_EMAIL,
            password=DEMO_PASSWORD,
            roles=["admin"],
        )
        if seeded.is_err():
            logger.info("seed_user_present", email=DEMO_EMAIL)
        self._authz.set_roles(ROLE_DEFINITIONS)


__all__ = ["DEMO_EMAIL", "DEMO_PASSWORD", "DemoSeedService", "ROLE_DEFINITIONS"]
```

- [ ] **Step 2: Rewrite the provider around async factories**

New shape (keep module docstring, imports trimmed to what is used):

```python
class AuthWebProvider(Provider):
    """Assemble the demo's session layer and register UI services."""

    name = "auth-web"

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind pure instances now; collaborators build lazily post-boot."""
        repository = InMemorySessionRepository()
        container.singleton(InMemorySessionRepository, instance=repository)
        container.singleton(SessionRepositoryProtocol, instance=repository)
        container.singleton(UserService, factory=self._build_user_service)
        container.singleton(SessionCookieBackend, factory=self._build_backend)
        container.singleton(
            PasswordChangeService, factory=self._build_password_changes
        )
        container.singleton(AuthApiController, factory=self._build_api)
        container.singleton(PagesController, instance=PagesController())
        container.singleton(DemoSeedService, factory=self._build_seed_service)

    async def _build_user_service(
        self, resolver: ContainerResolverProtocol
    ) -> UserService:
        authentication = await resolver.resolve(AuthenticationService)
        # UserService ships unregistered: build it on the SAME policy/user
        # store AuthenticationService holds so password changes are visible
        # to login.
        # TODO(framework): export UserService (or its dep keys) from
        # lexigram-auth so this attribute-fishing disappears.
        return UserService(
            password_policy=authentication.password_policy,
            user_store=authentication.user_store,
        )

    async def _build_backend(
        self, resolver: ContainerResolverProtocol
    ) -> SessionCookieBackend:
        return SessionCookieBackend(
            session_repository=await resolver.resolve(SessionRepositoryProtocol),
            user_fetcher=(await resolver.resolve(UserService)).get_user,
            secure=False,  # local demo runs plain http
        )

    async def _build_password_changes(
        self, resolver: ContainerResolverProtocol
    ) -> PasswordChangeService:
        authentication = await resolver.resolve(AuthenticationService)
        return PasswordChangeService(
            password_hasher=await resolver.resolve(PasswordHasherProtocol),
            policy=authentication.password_policy,
            user_store=authentication.user_store,
        )

    async def _build_api(
        self, resolver: ContainerResolverProtocol
    ) -> AuthApiController:
        return AuthApiController(
            authentication=await resolver.resolve(AuthenticationService),
            cookies=await resolver.resolve(SessionCookieBackend),
            sessions=await resolver.resolve(InMemorySessionRepository),
            authz=await resolver.resolve(AuthorizationService),
            password_changes=await resolver.resolve(PasswordChangeService),
        )

    async def _build_seed_service(
        self, resolver: ContainerResolverProtocol
    ) -> DemoSeedService:
        return DemoSeedService(
            user_service=await resolver.resolve(UserService),
            authz=await resolver.resolve(AuthorizationService),
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Seed demo data; everything else wires lazily."""
        seeder = await container.resolve(DemoSeedService)
        await seeder.run()
```

Keep module-level `build_auth_config()` unchanged; update the provider file's re-export `__all__` to include `DemoSeedService` passthrough only if tests import it from there (check first: `grep -rn "from auth_web" demos/auth-web/tests/`).

- [ ] **Step 3: Verify**

```bash
uv run pytest demos/auth-web/tests -q -m "not integration" --no-cov   # all pass, same count
wc -l demos/auth-web/src/auth_web/di/provider.py                      # <500
```

- [ ] **Step 4: Commit**

```bash
git add demos/auth-web/src/auth_web/services/seed.py demos/auth-web/src/auth_web/di/provider.py
git commit demos/auth-web/src/auth_web/services/seed.py demos/auth-web/src/auth_web/di/provider.py -m "♻️ refactor(demos): auth-web extracts DemoSeedService and resolver factories"
```

---

### Task 4: auth-rbac — same treatment as Task 3

**Files:**
- Create: `demos/auth-rbac/src/rbac_console/services/seed.py` (create `services/__init__.py` if absent)
- Modify: `demos/auth-rbac/src/rbac_console/di/provider.py`

**Interfaces:**
- Produces: `RbacSeedService(personas, articles, users, authz)` with `async run() -> None`; seeding content (personas/articles/roles) moved verbatim from current `boot()`.

- [ ] **Step 1: Extract `RbacSeedService`**

Mirror Task 3 Step 1: move persona creation, article seeding, role definitions, and their constants into `RbacSeedService.run()` verbatim; add the same `TODO(framework)` marker about `AuthConfig.roles`.

- [ ] **Step 2: Convert the provider**

Apply the Task 3 pattern: delete `__init__` held state and `_get(kind)`; register pure instances (`ArticleStore`, `PersonaDirectory`, `InMemorySessionRepository`, `SessionRepositoryProtocol`) plus factories `_build_users`, `_build_authz_cookies` (if `SessionCookieBackend` construction needs multi-resolve), `_build_api`, `_build_seed_service`. `boot()` reduces to resolving `RbacSeedService` and running it.

Preserve the existing NOTE about not re-registering `AuthorizationService` (module export visibility) — factories resolve it via `resolver.resolve(AuthorizationService)` exactly like today's boot does.

- [ ] **Step 3: Verify**

```bash
uv run pytest demos/auth-rbac/tests -q -m "not integration" --no-cov   # all pass, same count (10)
wc -l demos/auth-rbac/src/rbac_console/di/provider.py                  # <500
```

- [ ] **Step 4: Commit**

```bash
git add demos/auth-rbac/src/rbac_console
git commit demos/auth-rbac/src/rbac_console -m "♻️ refactor(demos): rbac-console extracts RbacSeedService and resolver factories"
```

---

### Task 5: realtime-monitor — @websocket Controller instead of router surgery

**Files:**
- Modify: `demos/realtime-monitor/src/ops_console/controllers/operator.py`
- Modify: `demos/realtime-monitor/src/ops_console/module.py`
- Modify: `demos/realtime-monitor/src/ops_console/di/provider.py`

**Interfaces:**
- Consumes: `OperatorHandler(AbstractWebSocketHandler)` with `async handle(ws)` lifecycle entry (verified: provider endpoint calls `handler.handle(ws)`).
- Produces: route `/api/ws/operator` mounted by WebModule via `controllers=[..., OperatorHandler]`; `RealtimeProvider` keeps only heartbeat duties.

- [ ] **Step 1: Make OperatorHandler a Controller with a decorated entrypoint**

```python
"""WebSocket operator channel for the realtime monitor demo."""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, WebSocket
from lexigram.web.routing.decorators import websocket
from lexigram.web.websocket.handler import AbstractWebSocketHandler
from ops_console.domain import Severity, SystemEvent
from ops_console.services.event_stream import EventStreamService


class OperatorHandler(Controller, AbstractWebSocketHandler):
    """Publish operator messages into the event stream."""

    prefix = ""

    def __init__(self, events: EventStreamService) -> None:
        AbstractWebSocketHandler.__init__(self)
        self.events = events

    @websocket("/api/ws/operator")
    async def operator_channel(self, websocket: WebSocket) -> None:
        """Own the connection lifecycle via the shared WS handler."""
        await self.handle(websocket)

    async def on_connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_json(
            {"ok": True, "message": "operator channel connected"}
        )

    async def on_message(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        event = SystemEvent(
            kind="operator",
            message=str(message.get("message") or "operator event"),
            severity=Severity.from_name(str(message.get("severity") or "info")),
            source="operator-channel",
            payload={"echo": True},
        )
        await self.events.publish(event)
        await websocket.send_json({"ok": True, "severity": event.severity.value})


__all__ = ["OperatorHandler"]
```

- [ ] **Step 2: Register through the web layer; drop router surgery**

`module.py`: `controllers=[ConsoleController]` → `controllers=[ConsoleController, OperatorHandler]`.

`di/provider.py`: delete `_make_endpoint`; reduce `boot()` to `self._start_heartbeat()` (plus docstring update). Keep heartbeat supervision/shutdown exactly as-is.

- [ ] **Step 3: Verify**

```bash
uv run pytest demos/realtime-monitor/tests -q -m "integration" --no-cov -k "websocket or operator" 2>/dev/null || true
uv run pytest demos/realtime-monitor/tests -q -m "not integration" --no-cov   # all pass, SAME count incl. ws tests
make smoke-demos                                                              # exit 0
```

If the ws test connects to `/api/ws/operator`, it exercises the new mounting directly — any failure means the Controller+AbstractWebSocketHandler MRO breaks `collect_routes()`/handler dispatch; debug before proceeding (do not revert to router.append).

- [ ] **Step 4: Commit**

```bash
git add demos/realtime-monitor/src/ops_console
git commit demos/realtime-monitor/src/ops_console -m "♻️ refactor(demos): mount operator ws via @websocket controller, drop router surgery"
```

---

### Task 6: Final verification sweep

- [ ] **Step 1: Full gates**

```bash
make check-demos                       # tests + compile + smoke
uv run python dev/check_loc_limit.py --root .   # 0 new, 0 stale
uv run ruff check demos/               # clean
```

- [ ] **Step 2: Commit anything remaining**

```bash
git status --short demos/
# only if drift exists:
git add demos/ && git diff --cached --stat && git commit demos/ -m "🔧 chore(demos): final quality pass leftovers"
```

---

## Self-Review

- Coverage: A (T1/T2/T3/T4 factories), B+D (T3/T4 seed services + TODO markers), C (T5 decorator mounting), E (T2 class-style). ✔
- Placeholders: none — every rewrite shows complete code or exact verbatim-move instructions. ✔
- Type consistency: `_build_*` names, `DemoSeedService`/`RbacSeedService.run()`, `OperatorHandler.handle` chain consistent across tasks. ✔
- Risk watchlist: T5 MRO interaction (Controller × AbstractWebSocketHandler) and T3 freeze-validation interplay are the two spots where execution may need adjustment; both have explicit verify steps that fail loudly.
