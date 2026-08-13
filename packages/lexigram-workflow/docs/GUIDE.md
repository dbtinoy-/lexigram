---
title: lexigram-workflow Guide
description: Pipelines, graph workflows, sagas, bulk operations, and state machines
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-queue` | Optional | Async workflow execution |
| `lexigram-resilience` | Optional | Retry policies |

> **Alpha (0.1.x)** — MIT licensed. Public API may change before 1.0.

## Problem

Business processes rarely fit in a single function call. You need multi-step pipelines, conditional branching, parallel execution, distributed transaction coordination (sagas), and batch processing — with observability, retry, and state persistence.

`lexigram-workflow` provides four orchestration patterns: **Pipelines** (sequential step chains), **Graph workflows** (DAG-based with branching), **Sagas** (compensating transaction coordination), and **Bulk operations** (batched parallel processing).

## Mental model

```
Workflow orchestration patterns in lexigram-workflow:

┌──────────────────────────────────────────────────────────────┐
│                     lexigram-workflow                         │
│                                                              │
│  ┌──────────┐   ┌──────────────┐   ┌──────────┐   ┌───────┐ │
│  │ Pipeline  │   │    Graph     │   │   Saga   │   │ Bulk  │ │
│  │(sequential│   │   (DAG)      │   │(LRA/TCC) │   │(batch)│ │
│  │  steps)   │   │  branching   │   │  compen-  │   │       │ │
│  └──────────┘   └──────────────┘   │  sating   │   └───────┘ │
│                                    └──────────┘              │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  StateMachine  (finite-state + persistence + versioning)  ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

Each pattern builds on a common foundation: async execution, `Result`-based error handling, and DI integration via `WorkflowProvider`.

## Core concepts

### Pipeline

A **Pipeline** is an ordered sequence of steps that share a context. Each step can read previous step results and write its own.

```python
from lexigram.workflow import Pipeline, step, conditional, parallel

pipeline = Pipeline()

@step(name="validate")
async def validate(ctx: dict) -> dict:
    data = ctx.get("input", {})
    if "email" not in data:
        return {"valid": False, "errors": ["email required"]}
    return {"valid": True, "data": data}

@step(name="process")
async def process(ctx: dict) -> dict:
    data = ctx["validate"]["data"]
    return {"result": f"Processed {data['email']}"}

pipeline.add_step(validate)
pipeline.add_step(process)

result = await pipeline.execute({"input": {"email": "a@b.com"}})
print(result)  # Output of final step
```

| Step type | Import | Behavior |
|---|---|---|
| `FunctionStep` (via `@step`) | `from lexigram.workflow import step` | Simple async function |
| `ConditionalStep` (via `@conditional`) | `from lexigram.workflow import conditional` | Branch based on predicate |
| `ParallelStep` (via `@parallel`) | `from lexigram.workflow import parallel` | Run substeps concurrently |

### Graph workflow

For complex workflows with branching, cycles (gated), and human-in-the-loop:

```python
from lexigram.workflow import (
    WorkflowBuilder,
    WorkflowEngine,
    AbstractWorkflowNode,
    GateNode,
    HumanNode,
)
from lexigram.workflow.config import GraphConfig
from lexigram.workflow.graph.node import NodeType


class FetchDataNode(AbstractWorkflowNode):
    name = "fetch_data"
    node_type = NodeType.TASK

    async def execute(self, state: dict) -> dict:
        return {"data": {"items": [1, 2, 3]}}


class ApproveNode(HumanNode):
    name = "approve"
    async def execute(self, state: dict) -> dict:
        return {"approved": True}


builder = WorkflowBuilder()
builder.add_node(FetchDataNode())
builder.add_node(ApproveNode())
builder.add_edge("fetch_data", "approve")

config = GraphConfig(checkpoint_enabled=True)
engine = WorkflowEngine(builder.build(), config=config)
result = await engine.execute("fetch_data")

if result.is_ok():
    wf = result.unwrap()
    print(wf.final_state)  # Merged state from all nodes
```

| Node type | Class | Purpose |
|---|---|---|
| Task | `AbstractWorkflowNode` (subclass) | General work |
| Gate | `GateNode` | Conditional routing |
| Human | `HumanNode` | Pauses for human input |
| LLM | `LLMNode` | AI inference step |
| Agent | `AgentNode` | Agent invocation |
| Tool | `ToolNode` | Tool execution |
| Subworkflow | `SubworkflowNode` | Nested workflow |

### Saga

A **Saga** coordinates a distributed transaction with compensating actions on failure:

```python
from lexigram.result import Ok, Err, Result
from lexigram.workflow import AbstractSaga
from lexigram.contracts.workflow import SagaStep, SagaStepError


class OrderSaga(AbstractSaga):
    VERSION = 1

    def __init__(self) -> None:
        super().__init__()
        self.add_step(SagaStep(
            name="reserve_inventory",
            action=self._reserve,
            compensation=self._release,
        ))
        self.add_step(SagaStep(
            name="charge_payment",
            action=self._charge,
            compensation=self._refund,
        ))

    async def _reserve(self) -> Result[None, SagaStepError]:
        return Ok(None)

    async def _release(self) -> None:
        pass

    async def _charge(self) -> Result[None, SagaStepError]:
        return Ok(None)

    async def _refund(self) -> None:
        pass


saga = OrderSaga()
result = await saga.execute()
if result.is_ok():
    print("Saga completed successfully")
else:
    print("Saga failed — compensations were applied")
```

Saga steps return `Result[Any, SagaStepError]`. On failure, previous steps' compensation handlers are called in reverse order.

### Bulk operations

Process large datasets in batches with concurrency control:

```python
from lexigram.workflow import BulkOperation
from lexigram.workflow.config import BulkOperationConfig


async def process_item(item: str) -> str:
    return f"processed_{item}"


config = BulkOperationConfig(batch_size=10, max_concurrency=5)
op = BulkOperation[str, str](processor=process_item, config=config)
result = await op.execute(items=[f"item-{i}" for i in range(100)])

if result.is_ok():
    batch_result = result.unwrap()
    print(f"Processed {len(batch_result.results)} items")
```

### State machine

Finite-state machine with optional durable persistence:

```python
from lexigram.workflow.state import StateMachine


class OrderStateMachine(StateMachine):
    def __init__(self) -> None:
        transitions = {
            "pending": {"approve": "approved", "cancel": "cancelled"},
            "approved": {"ship": "shipped", "cancel": "cancelled"},
            "shipped": {"deliver": "delivered"},
            "cancelled": {},
            "delivered": {},
        }
        super().__init__(initial="pending", transitions=transitions)


sm = OrderStateMachine()
assert sm.can_transition("approve")
new_state = await sm.transition("approve")
print(new_state)  # "approved"
```

## Common patterns

### Wiring via module

```python
from lexigram.workflow import WorkflowModule
from lexigram.workflow.config import BulkOperationConfig
from lexigram.contracts.workflow import SagaStoreProtocol

# With custom config and durable saga store
module = WorkflowModule.configure(
    config=BulkOperationConfig(batch_size=200),
    saga_store=my_saga_store,  # implements SagaStoreProtocol
)
app.add_module(module)
```

### Conditional pipeline step

```python
@conditional(
    name="route",
    condition=lambda ctx: ctx.get("is_premium", False),
)
async def premium_path(ctx: dict) -> str:
    return "premium_processing"


async def standard_path(ctx: dict) -> str:
    return "standard_processing"
```

### Workflow with versioning

```python
@workflow(name="onboarding", timeout=300.0, retries=1)
async def onboarding_workflow(ctx) -> None:
    ...
```

## Best practices

- **Start with pipelines** — graduate to graph workflows when you need branching
- **Use `WorkflowModule.configure()`** rather than wiring `WorkflowProvider` directly
- **Add `SagaStoreProtocol`** for durable saga state in production
- **Set `checkpoint_enabled=True`** in `GraphConfig` for resumable graph workflows
- **Version your workflows** — `WorkflowVersionMismatchError` prevents silent incompatibility
- **Use `@workflow` decorator** for timeout and retry metadata on long-running processes
