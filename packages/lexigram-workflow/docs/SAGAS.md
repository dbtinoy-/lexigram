---
title: lexigram-workflow Sagas
description: Distributed transaction coordination with compensating actions, state persistence, and versioning.
---

> **Alpha (0.1.x)** — MIT licensed. Public API may change before 1.0.

## Saga support in the workflow package

`lexigram-workflow` provides an orchestration-based saga model via `AbstractSaga`. Unlike the event-driven sagas in `lexigram-events` (which integrate with `EventBusProtocol`), workflow sagas are standalone — they define steps, execute them sequentially, and run compensations on failure.

```
AbstractSaga.execute()
  ├── Step 1: reserve_inventory → Ok/Err
  ├── Step 2: charge_payment   → Ok/Err
  ├── Step 3: confirm_order    → Ok/Err
  └── On failure: compensations in reverse order
```

## Pipeline vs saga differences

| Aspect | Pipeline | Saga |
|--------|----------|------|
| Purpose | Data transformation | Distributed transaction |
| Context | Shared dict across steps | Isolated per step action |
| Error handling | Step returns `Result` | Compensations called on failure |
| State persistence | In-memory | Optional `SagaStoreProtocol` |
| Use case | ETL, validation chains | Order fulfillment, booking |

Pipelines transform data. Sagas coordinate side effects across services.

## Step definition with compensation

Steps are added via `SagaStep` with an action and optional compensation:

```python
from lexigram.workflow.types import SagaStep
from lexigram.workflow.saga.base import AbstractSaga
from lexigram.result import Ok, Err, Result

class BookingSaga(AbstractSaga[str]):
    def __init__(self, booking_id: str, service: BookingService) -> None:
        super().__init__()
        self._booking_id = booking_id

        self.add_step(SagaStep(
            name="reserve_room",
            action=lambda: service.reserve(booking_id),
            compensation=lambda: service.release(booking_id),
        ))
        self.add_step(SagaStep(
            name="charge_card",
            action=lambda: service.charge(booking_id),
            compensation=lambda: service.refund(booking_id),
        ))

    def get_id(self) -> str:
        return self._booking_id

    def is_completed(self) -> bool:
        return self.state == SagaState.COMPLETED
```

Actions return `Result[Any, SagaStepError]`. On `Err`, all completed steps are compensated in reverse order.

## State persistence and recovery

For durable execution, inject a `SagaStoreProtocol` implementation via `WorkflowProvider`:

```python
from lexigram.workflow import WorkflowModule
from lexigram.contracts.workflow import SagaStoreProtocol

module = WorkflowModule.configure(
    saga_store=my_durable_store,  # implements SagaStoreProtocol
)
app.add_module(module)
```

Without a store, saga state lives in memory — restarting the process loses active sagas. With a store, the saga's current step, result, and state are persisted between steps, enabling recovery after process restart.

The `SagaStoreProtocol` defines:
- `save(saga_id, state)` — persist saga state
- `load(saga_id)` — restore saga state
- `list(status)` — find sagas by status for administrative views

## Example: booking/reservation saga

```python
from lexigram.workflow.saga.base import AbstractSaga
from lexigram.workflow.types import SagaStep
from lexigram.result import Ok, Err

class HotelBookingSaga(AbstractSaga[str]):
    VERSION = 1

    def __init__(self, booking_id: str, hotel: HotelService, payment: PaymentService) -> None:
        super().__init__()
        self._booking_id = booking_id

        self.add_step(SagaStep(
            name="hold_room",
            action=lambda: hotel.hold(booking_id),
            compensation=lambda: hotel.release(booking_id),
        ))
        self.add_step(SagaStep(
            name="charge_deposit",
            action=lambda: payment.charge(booking_id, amount=100),
            compensation=lambda: payment.refund(booking_id),
        ))

    def get_id(self) -> str:
        return self._booking_id

    def is_completed(self) -> bool:
        return self.state == SagaState.COMPLETED

saga = HotelBookingSaga("book-42", hotel_service, payment_service)
result = await saga.execute()
if result.is_ok():
    print(f"Booking {saga.get_id()} confirmed")
else:
    print(f"Booking failed — compensations applied")
```

## Versioning sagas

Sagas declare a `VERSION` class attribute. If the saga definition changes (different steps, different order) while a persisted saga is mid-execution, `WorkflowVersionMismatchError` is raised — preventing silent incompatibility:

```python
class BookingSaga(AbstractSaga[str]):
    VERSION = 2  # Bump when step definitions change
```

The version is stored alongside persisted saga state. On recovery, the stored version is compared against the current `VERSION`. A mismatch prevents execution and raises `WorkflowVersionMismatchError`.

## See also

- `AbstractSaga` — base class for orchestration sagas
- `SagaStep` — step definition with action + compensation
- `SagaStoreProtocol` — durable saga state interface
- `SagaState` — saga lifecycle enum (PENDING, COMPLETED, COMPENSATED, FAILED)
- `WorkflowProvider` — DI registration for sagas
