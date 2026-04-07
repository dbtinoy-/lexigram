---
title: lexigram-workflow Troubleshooting
description: Common errors, causes, and fixes
---

## `WorkflowNotFoundError`

**Error message:** `Workflow not found: <id>`

**Cause:** The workflow definition or instance ID doesn't exist.

**Fix:** Verify the workflow name or instance ID matches what was registered.

## `WorkflowStateError`

**Error message:** Raised when an operation is attempted on a workflow in an incompatible state.

**Cause:** The workflow is already running, completed, or failed, and the requested operation (e.g. resume, cancel) is not valid for that state.

**Fix:** Check the current workflow state before calling the operation. Use `WorkflowRunner` or `ExecutionHistory` to inspect state.

## `WorkflowStepError`

**Error message:** `Step '<name>' failed: <reason>`

**Cause:** A pipeline step or graph node raised an exception during `execute()`.

**Fix:** Inspect the step's logic. Wrap expected failures in `Result` types rather than letting them raise:

```python
async def my_step(ctx: dict) -> Result[str, MyError]:
    try:
        result = await risky_operation()
        return Ok(result)
    except KnownError as e:
        return Err(MyError(str(e)))
```

## `WorkflowTimeoutError`

**Error message:** Raised when a workflow or step exceeds its configured timeout.

**Cause:** The `timeout` or `pipeline_timeout` setting was exceeded.

**Fix:** Increase the timeout in config, or optimize the workflow to complete faster.

```yaml
workflow:
  timeout: 600.0  # Increase from default 300s
  pipeline_timeout: 120.0  # Increase from default 60s
```

## `WorkflowVersionMismatchError`

**Error message:** `Workflow '<name>' version mismatch: instance was started with v<N>, but definition is now v<M>`

**Cause:** Resuming an in-flight workflow instance whose definition version has changed.

**Fix:** Either migrate the instance or restart it under the current definition. Version the workflow definition:

```python
@workflow(name="onboarding", timeout=300.0)
async def onboarding(ctx) -> None:
    ...
```

## `WorkflowCompensationError`

**Error message:** Raised when a saga compensation handler fails.

**Cause:** A compensation callable raised an exception during saga rollback.

**Fix:** Compensations should be idempotent and handle infrastructure failures. If a compensation fails, manual intervention may be needed.

## `CycleDetectedError`

**Error message:** `Workflow exceeded max_iterations (<N>) at node '<name>'`

**Cause:** The graph engine reached the `max_iterations` guard, likely due to a cycle in the graph.

**Fix:** Check the graph structure. Increase `max_iterations` in `GraphConfig` if the workflow legitimately needs more steps:

```python
from lexigram.workflow.config import GraphConfig
GraphConfig(max_iterations=100)
```

## `NodeExecutionError`

**Error message:** A graph node's `execute()` method failed.

**Cause:** An exception was raised inside a node's `execute()` method.

**Fix:** Check the node implementation. Use `cause` attribute for the underlying exception:

```python
try:
    result = await engine.execute("start")
except NodeExecutionError as e:
    print(f"Node: {e.node}, Cause: {e.cause}")
```

## `GraphValidationError`

**Error message:** Graph structure validation failed.

**Cause:** The graph has missing nodes, dangling edges, or cycles during validation.

**Fix:** Ensure all edge targets reference existing nodes. Use `WorkflowBuilder.build()` to validate before creating the engine.

## `HumanInputRequiredError`

**Error message:** `Human input required at '<node>': <prompt>`

**Cause:** A `HumanNode` paused the workflow awaiting human input. This is expected behavior, not an error.

**Fix:** Provide input via `WorkflowRunner.resume()` with the checkpoint ID:

```python
result = await runner.resume(checkpoint_id=checkpoint_id, input={"approved": True})
```

## `SagaVersionMismatchError`

**Error message:** `Saga '<id>' version mismatch: code expects v<N>, stored state is v<M>`

**Cause:** The saga class `VERSION` attribute differs from the persisted saga state.

**Fix:** Either migrate saga instances or restart them. Set `VERSION` on your saga class:

```python
class MySaga(AbstractSaga):
    VERSION = 2
```

## Pipeline step not found

**Symptom:** `Pipeline` doesn't execute a registered step.

**Cause:** The step was added after `Pipeline` was used, or the step name was duplicated.

**Fix:** `add_step()` before `execute()`. Each step must have a unique name.
