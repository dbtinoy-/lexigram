# Demos Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the five audit gaps in `demos/`: test-gate the llm-experiment harness, containerize `OrdersApi`, deduplicate the orders handlers, supervise the realtime heartbeat task, and type the realtime request parameters.

**Architecture:** Six independently-verifiable tasks across three self-contained demos. Each task keeps the demo's teaching intent intact (no background outbox dispatcher, no StaticFiles mount — see spec "Explicitly rejected"). Tests boot real module graphs or call harness functions directly; no new framework code is touched.

**Tech Stack:** Python 3.11+, pytest (asyncio_mode auto), uv workspace, Make demo gates.

**Spec:** `docs/superpowers/specs/2026-08-21-demos-improvements.md`

## Global Constraints

- Python 3.11+, uv workspace, absolute imports only
- Google-style docstrings on new public members
- Commit convention: `<emoji> <type>(<scope>): <summary>` — one emoji, type matches emoji
- No worktrees, no branches, no `Co-authored-by` trailers
- Demo ruff exemptions (`T201`, `INP001`, `ANN`) remain in force
- Demos are excluded from the aggregate pytest run (`norecursedirs` in root `pyproject.toml`); always run demo tests via explicit paths or `make test-demos`
- Working tree is shared — check `git status --short` before committing; stage only your files

---

### Task 1: llm-experiment test suite + gate wiring

**Files:**
- Create: `demos/llm-experiment/conftest.py`
- Create: `demos/llm-experiment/tests/test_experiment.py`
- Modify: `Makefile:104` (`DEMO_TEST_DIRS`)

**Interfaces:**
- Consumes: `run_experiment(config: dict[str, Any], *, seed: int, out_dir: Path, ablate: str | None = None) -> ExperimentResult` and `metrics_delta(run_a: ExperimentResult, run_b: ExperimentResult) -> dict[str, Any]` from `demos/llm-experiment/harness.py`; `ExperimentResult` fields `.digest`, `.run_id`.
- Produces: `make test-demos` now includes `demos/llm-experiment/tests`. Nothing downstream consumes the test file itself.

- [ ] **Step 1: Write the conftest that puts the harness on sys.path**

Create `demos/llm-experiment/conftest.py`:

```python
"""Pytest bootstrap for the llm-experiment demo.

Puts the demo directory on ``sys.path`` so tests can import ``harness``
(the same way ``run_experiment.py`` does when executed in place). Demo
packages are intentionally excluded from the monorepo aggregate test run
(see root ``pyproject.toml`` ``norecursedirs``), so these tests run via
``make test-demos`` or:

    uv run pytest demos/llm-experiment/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
```

- [ ] **Step 2: Write the failing test suite**

Create `demos/llm-experiment/tests/test_experiment.py`:

```python
"""Tests for the seeded LLM relay experiment harness.

Verifies the reproducibility contract the demo advertises: same seed plus
same config produces a byte-identical digest, a different seed diverges,
and the thinking-ablation path produces a measurable delta.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harness import ExperimentResult, metrics_delta, run_experiment


def make_config() -> dict[str, Any]:
    """Return a minimal experiment config (mirrors experiment.yaml)."""
    return {
        "experiment": {
            "name": "llm-relay-probe-test",
            "description": "Deterministic conversion probe (test config)",
            "seed": 42,
            "iterations": 2,
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "tracing_enabled": True,
            "metrics_enabled": True,
        }
    }


def test_same_seed_produces_identical_digest(tmp_path: Path) -> None:
    config = make_config()

    first = run_experiment(config, seed=42, out_dir=tmp_path)
    second = run_experiment(config, seed=42, out_dir=tmp_path)

    assert first.digest == second.digest
    assert first.run_id == second.run_id


def test_different_seed_diverges(tmp_path: Path) -> None:
    config = make_config()

    baseline = run_experiment(config, seed=42, out_dir=tmp_path)
    other = run_experiment(config, seed=43, out_dir=tmp_path)

    assert baseline.digest != other.digest


def test_ablation_changes_digest_and_delta_is_empty_for_identical_runs(
    tmp_path: Path,
) -> None:
    config = make_config()

    control = run_experiment(config, seed=42, out_dir=tmp_path)
    ablated = run_experiment(config, seed=42, out_dir=tmp_path, ablate="thinking")

    # Ablating thinking changes the payloads, so digests must diverge...
    assert control.digest != ablated.digest
    # ...and metrics_delta reports no difference for identical runs.
    assert metrics_delta(control, run_experiment(config, seed=42, out_dir=tmp_path)) == {}


def test_artifacts_land_under_runs_directory(tmp_path: Path) -> None:
    result = run_experiment(make_config(), seed=42, out_dir=tmp_path)

    run_dir = tmp_path / "runs" / result.run_id
    assert run_dir.is_dir()
    assert len(result.checkpoint_paths) > 0
```

- [ ] **Step 3: Run the suite to verify it fails for the right reason**

Run: `uv run pytest demos/llm-experiment/tests -q --no-cov`
Expected: collection error or failures ONLY if a harness assumption is wrong (e.g. missing config key raises `KeyError`). If a test fails on a real assertion (digest equality), stop and investigate the harness before proceeding — do not weaken assertions.

- [ ] **Step 4: Run the suite to verify it passes**

Run: `uv run pytest demos/llm-experiment/tests -q --no-cov`
Expected: 4 passed

- [ ] **Step 5: Wire the suite into the Makefile gate**

In `Makefile:104`, change:

```make
DEMO_TEST_DIRS := demos/event-driven-orders/tests demos/realtime-monitor/tests
```

to:

```make
DEMO_TEST_DIRS := demos/event-driven-orders/tests demos/realtime-monitor/tests demos/llm-experiment/tests
```

- [ ] **Step 6: Run the full demo gate**

Run: `make test-demos`
Expected: all three suites pass

- [ ] **Step 7: Commit**

```bash
git add demos/llm-experiment/conftest.py demos/llm-experiment/tests/test_experiment.py Makefile
git commit -m "✅ test(demos): gate llm-experiment determinism suite"
```

---

### Task 2: event-driven-orders — resolve OrdersApi through the container

**Files:**
- Modify: `demos/event-driven-orders/src/orders/di/provider.py`
- Modify: `demos/event-driven-orders/src/orders/module.py:29-38` (exports)
- Modify: `demos/event-driven-orders/src/orders/main.py:62-72` (_run)
- Test: `demos/event-driven-orders/tests/test_orders.py`

**Interfaces:**
- Consumes: existing `OrdersApi(command_bus, event_bus, repository, view, outbox)` constructor (`src/orders/services.py:31`); `CommandBusImpl`, `EventBusProtocol`, `OrderRepository`, `OrdersView`, `Outbox` already registered by `OrdersProvider.register()` / `EventsModule`.
- Produces: `container.resolve(OrdersApi)` works after `Application.boot(...)`; `OrdersModule.configure().exports` contains `OrdersApi`.

- [ ] **Step 1: Write the failing test**

Append to `demos/event-driven-orders/tests/test_orders.py` (add `OrdersApi` to the existing imports from `orders.services`... note: there is no existing OrdersApi import — add `from orders.services import OrdersApi` alongside the other orders imports):

```python
async def test_orders_api_resolves_from_container(app: Application) -> None:
    api = await app.container.resolve(OrdersApi)

    order_id = await api.place("Bob Belcher", [item("SKU-9", 1, "12.00")])
    await api.pay(order_id, Decimal("12.00"))

    rows = api.list_orders()
    assert rows[0]["order_id"] == order_id
    assert rows[0]["status"] == "paid"
```

Place it inside the existing `TestOrderLifecycle` class as an additional method, matching file style.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest demos/event-driven-orders/tests/test_orders.py::TestOrderLifecycle::test_orders_api_resolves_from_container -v --no-cov`
Expected: FAIL — resolution error (`OrdersApi` not registered)

- [ ] **Step 3: Register the lazy factory in the provider**

In `demos/event-driven-orders/src/orders/di/provider.py`:

Add import:

```python
from orders.services import OrdersApi
```

Change the class to hold booted state and register a lazy factory (same pattern as `CacheProvider`'s post-boot factories):

```python
class OrdersProvider(Provider):
    """Provide the order write/read sides and their bus wiring."""

    name = "orders"
    priority = ProviderPriority.NORMAL

    def __init__(self) -> None:
        super().__init__()
        self._api: OrdersApi | None = None

    def _get_api(self) -> OrdersApi:
        """Return the API facade assembled during boot."""
        if self._api is None:
            raise RuntimeError("OrdersProvider has not been booted yet")
        return self._api

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(OrderRepository, OrderRepository())
        container.singleton(OrdersView, OrdersView())
        container.singleton(NotificationHandler, NotificationHandler())
        container.singleton(Outbox, Outbox())
        container.singleton(OrdersApi, self._get_api)
```

At the end of `boot()`, after the bus wiring, assemble the facade:

```python
        self._api = OrdersApi(
            command_bus=command_bus,
            event_bus=event_bus,
            repository=repository,
            view=view,
            outbox=outbox,
        )
```

- [ ] **Step 4: Export OrdersApi from the module**

In `demos/event-driven-orders/src/orders/module.py`: add `from orders.services import OrdersApi` and add `OrdersApi` to the `exports=[...]` list.

- [ ] **Step 5: Simplify main.py to a single resolve**

Replace `demos/event-driven-orders/src/orders/main.py:62-72` body of `_run`:

```python
async def _run(args: argparse.Namespace) -> None:
    async with Application.boot(
        name="orders", modules=[OrdersModule.configure()]
    ) as app:
        api = await app.container.resolve(OrdersApi)
```

Remove the now-unused imports of `EventBusProtocol`, `CommandBusImpl`, `OrdersView`, `Outbox`, `OrderRepository` from main.py (keep `OrderItem`, `OrdersModule`, `OrdersApi` usage).

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest demos/event-driven-orders/tests/test_orders.py -v --no-cov`
Expected: all tests PASS (including pre-existing ones)

- [ ] **Step 7: Commit**

```bash
git add demos/event-driven-orders/src/orders/di/provider.py demos/event-driven-orders/src/orders/module.py demos/event-driven-orders/src/orders/main.py demos/event-driven-orders/tests/test_orders.py
git commit -m "♻️ refactor(demos): resolve OrdersApi through the container"
```

---

### Task 3: event-driven-orders — deduplicate command handler plumbing

**Files:**
- Modify: `demos/event-driven-orders/src/orders/handlers.py`
- Test: none new (pure refactor — existing suite is the safety net)

**Interfaces:**
- Consumes: `Outbox.stage(event)`, `EventBusProtocol.publish(event) -> Result`, `logger` already defined at `handlers.py:31`.
- Produces: `OrderCommandHandlerBase(repository, event_bus, outbox)` with `async def _publish(self, event: DomainEvent, event_name: str) -> None`; the three concrete handlers keep identical public signatures (`handle(command) -> str | None`) so `di/provider.py` needs no changes.

- [ ] **Step 1: Extract the base class and rewrite the three handlers**

Rewrite `demos/event-driven-orders/src/orders/handlers.py` — keep the module docstring and imports, then replace the three classes with:

```python
class OrderCommandHandlerBase:
    """Shared wiring for write-side command handlers.

    Args:
        repository: The write-side repository.
        event_bus: The bus published events are announced on.
        outbox: The outbox each event is staged in before publishing.
    """

    def __init__(
        self,
        repository: OrderRepository,
        event_bus: EventBusProtocol,
        outbox: Outbox,
    ) -> None:
        self.repository = repository
        self.event_bus = event_bus
        self.outbox = outbox

    async def _publish(self, event: DomainEvent, event_name: str) -> None:
        """Stage an event, publish it, and warn on rejection.

        Args:
            event: The domain event to deliver.
            event_name: Event type name used in rejection logs.
        """
        self.outbox.stage(event)
        result = await self.event_bus.publish(event)
        if result.is_err():
            logger.warning(
                "order_event_rejected",
                event=event_name,
                error=str(result.unwrap_err()),
            )


class PlaceOrderHandler(OrderCommandHandlerBase):
    """Handle :class:`PlaceOrder` by persisting the order and publishing the event."""

    async def handle(self, command: PlaceOrder) -> str:
        total = sum((item.line_total for item in command.items), Decimal("0"))
        order = Order(
            order_id=self.repository.next_id(),
            customer=command.customer,
            total=total,
            status=OrderStatus.PLACED,
        )
        self.repository.save(order)

        event = order_event(
            OrderPlaced,
            order_id=order.order_id,
            customer=order.customer,
            total=total,
        )
        await self._publish(event, "OrderPlaced")
        logger.info("order_placed", order_id=order.order_id, total=str(total))
        return order.order_id


class PayOrderHandler(OrderCommandHandlerBase):
    """Handle :class:`PayOrder` by marking the order paid."""

    async def handle(self, command: PayOrder) -> None:
        order = self.repository.get(command.order_id)
        if order is None:
            raise OrderNotFoundError(f"Order {command.order_id} not found")
        if order.status is OrderStatus.PAID:
            raise OrderAlreadyPaidError(f"Order {command.order_id} is already paid")
        if order.status is OrderStatus.SHIPPED:
            raise OrderAlreadyShippedError(
                f"Order {command.order_id} is already shipped"
            )

        paid = Order(
            order_id=order.order_id,
            customer=order.customer,
            total=order.total,
            status=OrderStatus.PAID,
        )
        self.repository.save(paid)

        event = order_event(
            OrderPaid,
            order_id=order.order_id,
            amount=command.amount,
        )
        await self._publish(event, "OrderPaid")
        logger.info("order_paid", order_id=order.order_id, amount=str(command.amount))


class ShipOrderHandler(OrderCommandHandlerBase):
    """Handle :class:`ShipOrder` by marking the order shipped."""

    async def handle(self, command: ShipOrder) -> None:
        order = self.repository.get(command.order_id)
        if order is None:
            raise OrderNotFoundError(f"Order {command.order_id} not found")
        if order.status is not OrderStatus.PAID:
            raise OrderNotPlacedError(
                f"Order {command.order_id} must be paid before shipping"
            )

        shipped = Order(
            order_id=order.order_id,
            customer=order.customer,
            total=order.total,
            status=OrderStatus.SHIPPED,
        )
        self.repository.save(shipped)

        event = order_event(OrderShipped, order_id=order.order_id)
        await self._publish(event, "OrderShipped")
        logger.info("order_shipped", order_id=order.order_id)


__all__ = [
    "OrderCommandHandlerBase",
    "PayOrderHandler",
    "PlaceOrderHandler",
    "ShipOrderHandler",
]
```

Add `DomainEvent` to the imports from `orders.domain` (it is re-exported there via `lexigram.contracts.domain`; if not present in `orders.domain.__all__`, import it directly: `from lexigram.contracts.domain import DomainEvent`).

- [ ] **Step 2: Run the full orders suite**

Run: `uv run pytest demos/event-driven-orders/tests -v --no-cov`
Expected: all tests PASS unchanged (behavior preserved)

- [ ] **Step 3: Verify the CLI still works end-to-end**

Run:
```bash
uv run python -m orders place "Smoke Test" --item "SKU-1,1,9.99" && uv run python -m orders list && uv run python -m orders outbox
```
(workdir: `demos/event-driven-orders/src`)
Expected: order placed, listed as `placed`, outbox shows pending records then flushes

- [ ] **Step 4: Commit**

```bash
git add demos/event-driven-orders/src/orders/handlers.py
git commit -m "♻️ refactor(demos): deduplicate orders command handler plumbing"
```

---

### Task 4: realtime-monitor — supervise the heartbeat task

**Files:**
- Modify: `demos/realtime-monitor/src/ops_console/di/provider.py`
- Create: `demos/realtime-monitor/tests/test_provider_heartbeat.py`

**Interfaces:**
- Consumes: `EventStreamService.publish(event) -> int` (may raise on internal bugs); `RealtimeProvider.__init__(heartbeat_interval: float = 15.0)` which creates `self.events`.
- Produces: `RealtimeProvider._start_heartbeat() -> None` (creates task + attaches done-callback; safe to call in tests without booting the web layer), `_stopping: bool` attribute, structlog event name `"heartbeat_task_died"`.

- [ ] **Step 1: Write the failing test**

Create `demos/realtime-monitor/tests/test_provider_heartbeat.py`:

```python
"""Unit tests for heartbeat task supervision in RealtimeProvider."""

from __future__ import annotations

import asyncio

import pytest

from ops_console.di.provider import RealtimeProvider
from ops_console.domain import SystemEvent


@pytest.mark.asyncio
async def test_heartbeat_survives_publish_crash_and_keeps_beating() -> None:
    provider = RealtimeProvider(heartbeat_interval=0.01)
    calls = {"count": 0}
    original_publish = provider.events.publish

    async def flaky_publish(event: SystemEvent) -> int:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("simulated publish crash")
        return await original_publish(event)

    provider.events.publish = flaky_publish  # type: ignore[method-assign]

    provider._start_heartbeat()
    await asyncio.sleep(0.15)

    try:
        # First tick crashed; supervision must have restarted the loop and
        # subsequent ticks must keep publishing.
        assert calls["count"] >= 3
    finally:
        await provider.shutdown()


@pytest.mark.asyncio
async def test_shutdown_cancels_heartbeat_cleanly() -> None:
    provider = RealtimeProvider(heartbeat_interval=0.01)
    provider._start_heartbeat()
    await asyncio.sleep(0.05)

    await provider.shutdown()

    assert provider._heartbeat_task is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest demos/realtime-monitor/tests/test_provider_heartbeat.py -v --no-cov`
Expected: FAIL — `AttributeError: 'RealtimeProvider' object has no attribute '_start_heartbeat'`

- [ ] **Step 3: Implement supervision in the provider**

In `demos/realtime-monitor/src/ops_console/di/provider.py`:

Add imports:

```python
from lexigram.logging import get_logger
```

and at module level after the imports:

```python
logger = get_logger(__name__)
```

Extend `__init__`:

```python
    def __init__(self, heartbeat_interval: float = 15.0) -> None:
        super().__init__()
        self.heartbeat_interval = heartbeat_interval
        self.events = EventStreamService()
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._stopping = False
```

Replace the task creation line in `boot()` (`self._heartbeat_task = asyncio.create_task(self._heartbeat())`) with:

```python
        self._start_heartbeat()
```

Add the supervision methods (before `_heartbeat`):

```python
    def _start_heartbeat(self) -> None:
        """Start the heartbeat producer under done-callback supervision."""
        self._heartbeat_task = asyncio.create_task(self._heartbeat())
        self._heartbeat_task.add_done_callback(self._on_heartbeat_done)

    def _on_heartbeat_done(self, task: asyncio.Task[None]) -> None:
        """Log unexpected heartbeat death and restart unless shutting down."""
        if task.cancelled() or self._stopping:
            return
        exc = task.exception()
        if exc is not None:
            logger.error("heartbeat_task_died", error=str(exc))
            self._start_heartbeat()
```

Update `shutdown()` to set the stopping flag first:

```python
    async def shutdown(self) -> None:
        self._stopping = True
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest demos/realtime-monitor/tests/test_provider_heartbeat.py -v --no-cov`
Expected: 2 passed

- [ ] **Step 5: Run the whole realtime suite**

Run: `uv run pytest demos/realtime-monitor/tests -q --no-cov`
Expected: all pass (endpoint/stream suites unaffected)

- [ ] **Step 6: Commit**

```bash
git add demos/realtime-monitor/src/ops_console/di/provider.py demos/realtime-monitor/tests/test_provider_heartbeat.py
git commit -m "🐛 fix(demos): supervise realtime heartbeat task"
```

---

### Task 5: realtime-monitor — annotate request parameters

**Files:**
- Modify: `demos/realtime-monitor/src/ops_console/controllers/console.py`

**Interfaces:**
- Consumes: `starlette.requests.Request` (the exact type the framework's own `AbstractSSEHandler` uses).
- Produces: no runtime changes — annotations only; defaults stay exactly as-is so route binding is untouched.

- [ ] **Step 1: Add the import and annotate every request parameter**

In `console.py`, add to the third-party import group:

```python
from starlette.requests import Request
```

Then change these signatures (bodies untouched):

```python
    async def stream(self, request: Request) -> AsyncGenerator[dict[str, Any], None]:
```

```python
    @get("/api/events/stream")
    async def stream(self, request: Request | None = None) -> Any:
```

```python
    @get("/api/stats")
    async def stats(self, request: Request | None = None) -> dict[str, Any]:
```

```python
    @get("/static/dashboard.js")
    async def dashboard_js(self, request: Request | None = None) -> FileResponse:
```

```python
    @get("/static/style.css")
    async def dashboard_css(self, request: Request | None = None) -> FileResponse:
```

```python
    @get("/")
    async def dashboard(self, request: Request | None = None) -> HTMLContent:
```

```python
    @post("/api/events")
    async def publish_event(self, request: Request | None = None) -> dict[str, Any]:
```

- [ ] **Step 2: Run lint and the realtime suite**

Run: `uv run ruff check demos/realtime-monitor/ && uv run pytest demos/realtime-monitor/tests -q --no-cov`
Expected: lint clean, all tests pass

- [ ] **Step 3: Commit**

```bash
git add demos/realtime-monitor/src/ops_console/controllers/console.py
git commit -m "🎨 style(demos): annotate realtime request parameters"
```

---

### Task 6: minor polish + full gate verification

**Files:**
- Modify: `demos/event-driven-orders/src/orders/domain.py:108-113` (`order_event` signature)

**Interfaces:**
- Consumes: nothing new.
- Produces: `order_event(event_cls, order_id: str, aggregate_id: UUID | None = None, **payload)` — all existing callers pass no `aggregate_id`, so this is source-compatible.

- [ ] **Step 1: Tighten the aggregate_id parameter**

In `domain.py`, change the `order_event` signature and docstring line:

```python
def order_event(
    event_cls: type[DomainEvent],
    order_id: str,
    aggregate_id: UUID | None = None,
    **payload: Any,
) -> DomainEvent:
    """Build a domain event with aggregate context attached.

    Args:
        event_cls: The event class to instantiate.
        order_id: Order identifier (also attached as aggregate_id).
        aggregate_id: Optional override for the aggregate id.
        **payload: Event-specific fields.

    Returns:
        An :class:`DomainEvent` instance ready for the event bus.
    """
```

(`UUID` is already imported at `domain.py:14`.)

- [ ] **Step 2: Lint everything**

Run: `uv run ruff check demos/ && uv run ruff format --check demos/`
Expected: clean

- [ ] **Step 3: Run the complete demo gate**

Run: `make check-demos`
Expected: all three test suites pass AND compile checks pass

- [ ] **Step 4: Commit**

```bash
git add demos/event-driven-orders/src/orders/domain.py
git commit -m "🔧 chore(demos): tighten order_event aggregate id typing"
```

---

## Self-Review Notes

- Spec coverage: P1→Task 1, P2→Task 2, P3→Task 3, P4→Task 4, P5→Task 5, R6→Task 6, R7→per-task commits + Task 6 Step 3. Rejected items (outbox dispatcher, StaticFiles) appear in no task — correct.
- Type consistency: `_start_heartbeat`/`_on_heartbeat_done`/`_stopping` names match between Task 4 steps and its test; `OrdersApi` export added in Task 2 before main.py relies on resolution; `OrderCommandHandlerBase` exported in Task 3's `__all__`.
- Ordering: Tasks 1–6 are independent except Task 6 depends on nothing; any task can be rejected without blocking neighbors. Recommended order preserves smallest-risk-first.
