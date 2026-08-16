---
title: lexigram-workflow Quickstart
description: Install, wire, and run your first pipeline in 5 minutes
---

:::note[What you'll need]
- Python 3.11+
- An existing Lexigram application
:::

> **Alpha (0.1.x)** — MIT licensed. Public API may change before 1.0.

## Install

```bash
pip install lexigram-workflow
```

## Minimal example — Pipeline

Create a simple multi-step pipeline, wire it via the module, and execute it.

```python
import asyncio

from lexigram import Application
from lexigram.workflow import Pipeline, step, WorkflowModule


async def main() -> None:
    app = Application(name="wf-demo")

    # Wire the workflow subsystem
    app.add_module(WorkflowModule.configure())

    async with Application.boot(name="wf-demo") as app:
        pipeline = Pipeline()

        @step(name="greet")
        async def greet(ctx: dict) -> str:
            return f"Hello, {ctx.get('name', 'world')}!"

        @step(name="shout")
        async def shout(ctx: dict) -> str:
            return str(ctx.get("greet", "")).upper()

        pipeline.add_step(greet)
        pipeline.add_step(shout)

        result = await pipeline.execute({"name": "Lexigram"})
        print(result)  # "HELLO, LEXIGRAM!"


asyncio.run(main())
```

## Minimal example — Graph workflow

For directed-graph workflows with branching and conditional routing:

```python
from lexigram.workflow import WorkflowBuilder, WorkflowEngine
from lexigram.workflow.graph.node import AbstractWorkflowNode


class GreetNode(AbstractWorkflowNode):
    name = "greet"
    async def execute(self, state: dict) -> dict:
        return {"message": f"Hello, {state.get('name', 'world')}!"}


class ShoutNode(AbstractWorkflowNode):
    name = "shout"
    async def execute(self, state: dict) -> dict:
        return {"message": state.get("message", "").upper()}


builder = WorkflowBuilder()
builder.add_node(GreetNode())
builder.add_node(ShoutNode())
builder.add_edge("greet", "shout")

engine = WorkflowEngine(builder.build())
result = await engine.execute("greet", initial_state={"name": "Lexigram"})
if result.is_ok():
    wf_result = result.unwrap()
    print(wf_result.final_state)
```

## Wiring

```python
from lexigram.workflow import WorkflowModule

app.add_module(WorkflowModule.configure())
```

`configure()` accepts an optional `BulkOperationConfig` and optional `SagaStoreProtocol` for durable saga state. The module exports `PipelineProtocol`.

## Next steps

- [GUIDE.md](./GUIDE) — pipelines, graph workflows, sagas, bulk operations
- [ARCHITECTURE.md](./ARCHITECTURE) — internal design, providers, container bindings
- [CONFIGURATION.md](./CONFIGURATION) — every config key with defaults
- [HOWTOS.md](./HOWTOS) — graph branching, sagas, state persistence, versioning
- [API.md](./API) — full reference
