---
title: lexigram-events Sagas
description: Long-running business process coordination — choreography vs orchestration, compensation, idempotency.
---

> **Alpha (0.1.x)** — MIT licensed. Public API may change before 1.0.

## Saga pattern

A saga is a sequence of local transactions that together form a distributed business process. If any step fails, previously completed steps are undone via **compensating actions**.

lexigram-events provides two saga implementations:

| Approach | Module | Use case |
|----------|--------|----------|
| `SagaManager` | `lexigram.events.sagas.manager` | Sequential steps, simple compensation chain |
| `SagaOrchestrator` | `lexigram.events.sagas.orchestrator` | Parallel steps, conditional transitions, state-machine flow |

### Choreography vs orchestration

**Choreography** — each service emits events that trigger the next step. No central coordinator. Built on `EventBusProtocol` directly.

**Orchestration** — a central `SagaManager` or `SagaOrchestrator` tells each participant what to do and when. Easier to monitor, debug, and evolve.

lexigram-events uses **orchestration** — you define the step sequence and compensation logic in one place.

## Saga steps

Steps are decorated with `@saga_step`:

```python
from lexigram.events.sagas.base import saga_step

class OrderFulfillmentSaga(SagaBase):
    name = "order_fulfillment"

    @saga_step("reserve_inventory", max_retries=3, retry_delay=1.0)
    async def reserve(self, ctx: SagaContext) -> SagaStepResult:
        return await inventory_service.reserve(ctx["order_id"])

    @saga_step("reserve_inventory", compensation=True)
    async def release(self, ctx: SagaContext) -> SagaStepResult:
        return await inventory_service.release(ctx["order_id"])
```

Each step declares:
- `name` — unique identifier
- `max_retries` / `retry_delay` — transient failure handling
- `compensation=True` — marks a method as the compensating action for the matching step

## Example: order fulfillment saga

```python
from lexigram.events.sagas.base import SagaBase, saga_step
from lexigram.events.sagas.context import SagaContext, SagaStepResult
class OrderFulfillmentSaga(SagaBase):
    name = "order_fulfillment"

    @saga_step("reserve_inventory", max_retries=3)
    async def reserve(self, ctx: SagaContext) -> SagaStepResult:
        return await inventory.reserve(ctx["order_id"])

    @saga_step("reserve_inventory", compensation=True)
    async def release(self, ctx: SagaContext) -> SagaStepResult:
        return await inventory.release(ctx["order_id"])

    @saga_step("charge_payment", max_retries=2)
    async def charge(self, ctx: SagaContext) -> SagaStepResult:
        return await payment.charge(ctx["order_id"], ctx["amount"])

    @saga_step("charge_payment", compensation=True)
    async def refund(self, ctx: SagaContext) -> SagaStepResult:
        return await payment.refund(ctx["order_id"])

    @saga_step("confirm_order")
    async def confirm(self, ctx: SagaContext) -> SagaStepResult:
        return await order.confirm(ctx["order_id"])

# Usage
manager = SagaManager()
manager.register(OrderFulfillmentSaga)
saga_id = await manager.start("order_fulfillment", {"order_id": "ord-1", "amount": 500})
```

If `charge_payment` fails, the saga automatically calls `release` (compensation for step 1) in reverse order.

## Compensation/rollback

When a step returns an `Err` result, the saga:

1. Marks the failed step as `FAILED`
2. Calls compensation handlers for all previously completed steps in **reverse order**
3. Marks the saga as `COMPENSATED`

Compensations are called with the same `SagaContext`. They should be idempotent — they may be retried on transient failures.

## Idempotency and retry

Each step has `max_retries` and `retry_delay`. Transient failures (network timeouts, database deadlocks) trigger a retry. Non-retryable errors (validation failures) skip retries and begin compensation immediately.

The `SagaStore` persists saga state (`SagaRecord`, `SagaStepRecord`) so that a saga interrupted by a process restart can resume — provided a durable store is configured:

```python
from lexigram.events.sagas.store import InMemorySagaStore

store = InMemorySagaStore()
```

## Correlation IDs for saga tracking

Each saga instance gets a unique `saga_id` (UUID). The `SagaContext` carries this ID. Propagate it to downstream services for tracing:

```python
ctx["correlation_id"] = str(saga_id)
```

The `SagaRecord` stores the saga name, status, and timestamps for monitoring.

## See also

- `SagaBase` — base class with `@saga_step` decorator support
- `SagaManager` — sequential saga coordinator
- `SagaOrchestrator` — parallel / conditional saga coordinator
- `SagaStore` — durable saga state persistence
- `SagaConfig` — timeouts, retries, compensation settings
