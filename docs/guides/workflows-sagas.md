---
title: "Workflows & Sagas"
description: "Orchestrate multi-step processes with compensation, state machines, and pipeline steps."
---

:::tip[Living demo]
A runnable, CI-gated companion lives at `demos/event-driven-orders/`. Try it locally:

```bash
uv run python -m orders demo
```
:::


`lexigram-workflow` provides three orchestration primitives: **pipelines** for sequential step execution, **sagas** for long-running processes with compensation, and **graph workflows** for DAG-based execution with branching and gates.

For the full configuration reference, workflow graph DSL, and advanced saga patterns, see the [`lexigram-workflow` package docs](/packages/lexigram-workflow/).

---

## 1. Pipelines

A `Pipeline` executes steps in registration order. Each step receives a shared `PipelineContext` and produces a `Result`:

```python
from lexigram.result import Result, Ok, Err
from lexigram.workflow import Pipeline, FunctionStep, PipelineContext


class OrderPipeline:
    def __init__(self) -> None:
        self._pipeline = Pipeline()

    def build(self) -> None:
        self._pipeline.add_step(FunctionStep(
            name="validate_order", func=self.validate, timeout=10.0,
        ))
        self._pipeline.add_step(FunctionStep(
            name="charge_payment", func=self.charge,
            dependencies=["validate_order"], timeout=30.0,
        ))
        self._pipeline.add_step(FunctionStep(
            name="send_confirmation", func=self.confirm,
            dependencies=["charge_payment"], timeout=5.0,
        ))

    async def validate(self, ctx: PipelineContext) -> Result[str, str]:
        return Ok("validated") if ctx.metadata.get("order") else Err("No order")

    async def charge(self, ctx: PipelineContext) -> Result[str, str]:
        return Ok("charged")

    async def confirm(self, ctx: PipelineContext) -> Result[str, str]:
        return Ok("confirmed")
```

### Conditional & Parallel Steps

```python
from lexigram.workflow import ConditionalStep, ParallelStep

conditional = ConditionalStep(
    name="check_risk",
    condition=lambda ctx: ctx.metadata.get("amount", 0) > 10000,
    true_step=FunctionStep(name="require_review", func=review),
    false_step=FunctionStep(name="auto_approve", func=approve),
)

parallel = ParallelStep(
    name="notify_all", fail_fast=False, timeout=15.0,
    steps=[
        FunctionStep(name="email", func=send_email),
        FunctionStep(name="sms", func=send_sms),
    ],
)
```

---

## 2. Sagas

A saga coordinates a multi-step process with compensating actions. Extend `AbstractSaga` and add steps:

```python
from lexigram.result import Result, Ok, Err
from lexigram.workflow import AbstractSaga, SagaStep


class BookingSaga(AbstractSaga):
    def __init__(self) -> None:
        super().__init__()
        self.add_step(SagaStep(
            name="reserve_flight",
            action=self.reserve_flight,
            compensation=self.cancel_flight,
            max_retries=3, idempotent=True,
        ))
        self.add_step(SagaStep(
            name="book_hotel",
            action=self.book_hotel,
            compensation=self.cancel_hotel,
        ))

    async def reserve_flight(self) -> Result[str, str]:
        return Ok("FL-123")

    async def cancel_flight(self) -> None:
        await self._flight_api.cancel("FL-123")

    async def book_hotel(self) -> Result[str, str]:
        return Err("no rooms available")

    async def cancel_hotel(self) -> None:
        pass


result = await saga.execute()
if result.is_err():
    print(f"Compensated: {saga.was_compensated()}")
```

:::caution
Compensation actions must be **idempotent**. A saga may call `compensate()` multiple times. Mark steps with `idempotent=True`.
:::

### Saga State Machine

Sagas transition through `SagaState`: `PENDING → RUNNING → COMPLETED` or `PENDING → RUNNING → COMPENSATING → FAILED`. The state is persisted via `SagaStoreProtocol`:

```python
from lexigram.contracts.workflow.protocols import SagaStoreProtocol, SagaState


class SagaPersistence:
    def __init__(self, store: SagaStoreProtocol) -> None:
        self._store = store

    async def save_checkpoint(self, saga_id: str, state: SagaState, data: dict) -> None:
        await self._store.save(saga_id, state, data)

    async def resume(self, saga_id: str) -> SagaState | None:
        result = await self._store.load(saga_id)
        return result[0] if result else None
```

---

## 3. Graph Workflows

For DAG-based workflows, use `WorkflowBuilder` and `WorkflowEngine`. Build a directed graph of nodes with gates and edges:

```python
from lexigram.workflow import WorkflowBuilder, WorkflowEngine


class DocumentApprovalFlow:
    def __init__(self) -> None:
        self._builder = WorkflowBuilder()

    def build(self) -> WorkflowEngine:
        b = self._builder
        b.add_node("start", entry_point=True)
        b.add_node("validate")
        b.add_node("review")
        b.add_node("approve")
        b.add_node("reject")
        b.add_node("publish")
        b.add_gate("is_valid", condition=lambda s: s.get("valid", False))

        b.add_edge("start", "validate")
        b.add_edge("validate", "is_valid")
        b.add_edge("is_valid", "review")
        b.add_edge("is_valid", "reject")
        b.add_edge("review", "approve")
        b.add_edge("approve", "publish")
        b.set_entry("start")
        b.set_terminal("publish")
        b.set_terminal("reject")
        return b.build()

    async def run(self, document: dict) -> Result[str, str]:
        return await self.build().execute(document)
```

The engine supports checkpointing — enable it via `GraphConfig` on the builder (settings are configured programmatically, not from YAML):

```python
from lexigram.workflow import WorkflowBuilder, GraphConfig

builder = WorkflowBuilder()
builder.configure(GraphConfig(
    checkpoint_enabled=True,
    max_iterations=50,
    node_timeout=120.0,
))
# ... add nodes, gates, edges ...

engine = builder.build()
result = await engine.execute({"doc_id": "DOC-001"})

# Resume from a checkpoint state with the human's decision:
result = await engine.resume(checkpoint_state, "approved")
```

---

## 4. State Machines

`StateMachineProtocol` provides finite-state-machine orchestration within workflows:

```python
from lexigram.contracts.workflow.protocols import StateMachineProtocol


class OrderStateMachine:
    def __init__(self, machine: StateMachineProtocol) -> None:
        self._machine = machine

    async def process_event(self, event: str) -> str:
        if not self._machine.can_transition(event):
            raise ValueError(f"Cannot transition from {self._machine.current_state}")
        return await self._machine.transition(event)

    @property
    def state(self) -> str:
        return self._machine.current_state
```

---

## 5. Bulk Operations

Process items in batches with retries and progress tracking:

```python
from lexigram.workflow import BulkOperationConfig, BulkOperation

config = BulkOperationConfig(
    batch_size=10, max_concurrency=5,
    timeout=300.0, retry_attempts=3,
)
operation = BulkOperation(config=config)
async for batch in operation.execute(items):
    print(batch)  # BulkBatchResult per batch
```

---

## 6. Configuration & Module

```python
from lexigram import Application
from lexigram.workflow import WorkflowModule, BulkOperationConfig

app = Application(name="my-app")
app.add_module(WorkflowModule.configure(
    config=BulkOperationConfig(batch_size=50, max_concurrency=10),
))
```

```yaml title="application.yaml"
workflow:
  batch_size: 10
  max_concurrency: 5
  timeout: 300.0
  retry_attempts: 3
  pipeline_timeout: 600.0
```

:::note
The `workflow:` section maps to `BulkOperationConfig`. The graph engine's settings (`checkpoint_enabled`, `max_iterations`, `node_timeout`, …) are not read from YAML — configure them per workflow via `WorkflowBuilder.configure(GraphConfig(...))`, as shown in section 3.
:::

---

## 7. Testing

`WorkflowModule.stub()` uses in-memory stores with no external dependencies:

```python
from lexigram import Application
from lexigram.workflow import WorkflowModule, Pipeline, FunctionStep


async def test_pipeline_executes_steps() -> None:
    async with Application.boot(modules=[WorkflowModule.stub()]) as app:
        pipeline = Pipeline()
        pipeline.add_step(FunctionStep(name="step1", func=lambda ctx: "done"))
        result = await pipeline.execute({})
        assert result.is_ok()
```

---

## Next Steps

- [Dependency Injection](/fundamentals/dependency-injection/) — binding protocols to implementations
- [Providers](/fundamentals/providers/) — how `WorkflowProvider` hooks into application boot
- [Testing](/guides/testing/) — substituting stubs for infrastructure
- [`lexigram-workflow` package](/packages/lexigram-workflow/) — saga patterns, decorators (`@workflow`, `@saga_step`), graph engine DSL, event hooks
