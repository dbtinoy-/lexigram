---
title: lexigram-ai-agents Guide
description: Mental model, core concepts, and end-to-end usage of the agent system.
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-ai-llm` | Optional | LLM client integration |
| `lexigram-ai-memory` | Optional | Memory system integration |
| `lexigram-ai-skills` | Optional | Skills system integration |
| `lexigram-ai-observability` | Optional | Observability |

## Problem & Mental Model

LLMs are powerful at generating text, but they can't query databases, call APIs, or remember past conversations without tooling. **lexigram-ai-agents** solves this by giving LLMs:

- **Tools** — typed async functions the LLM can invoke (search, compute, APIs)
- **Strategies** — reasoning loops (ReAct, plan-and-execute, reflexion, supervisor)
- **Execution** — a runtime that drives the loop, handles errors, and manages context
- **Observability** — metrics, tracing, and events for every execution

The mental model is a **thought-action-observation loop**: the LLM thinks, decides to either respond or call a tool, observes the result, and repeats until it has enough information to produce a final answer.

## Core Concepts

### Agent

An agent is defined by subclassing `AgentBase` and setting `name`, `system_prompt`, and `tools`:

```python
from lexigram.ai.agents import AgentBase, tool


@tool
async def search_kb(query: str) -> str:
    """Search the knowledge base."""
    return f"Results for: {query}"


class SupportAgent(AgentBase):
    name = "support_agent"
    system_prompt = "You are a technical support agent. Use the KB to answer questions."

    @property
    def tools(self):
        return [search_kb]
```

### Tools

Tools are async functions decorated with `@tool`. The decorator generates a JSON schema from the function signature (including docstring) for LLM function-calling:

```python
from lexigram.ai.agents import tool


@tool
async def get_order_status(order_id: str) -> dict:
    """Look up the status of an order.

    Args:
        order_id: The unique order identifier.
    """
    return {"order_id": order_id, "status": "shipped", "eta": "tomorrow"}
```

Tool schemas are auto-registered via `ToolRegistryImpl`. The registry supports module-visibility controls through `CompiledModuleGraph` when modules are used.

### Strategies

Strategies implement the reasoning loop. The package ships with four:

| Strategy | Description |
|----------|-------------|
| `ReActStrategy` | Thought → Action → Observation loop (default) |
| `PlanAndExecuteStrategy` | Generate a plan first, then execute each step |
| `ReflexionStrategy` | Self-critique and refine answers |
| `SupervisorStrategy` | Orchestrate sub-agents (multi-agent) |

Strategy selection is per-agent via `AgentStrategyRegistry`:

```python
from lexigram.ai.agents.strategies import ReActStrategy

class MyAgent(AgentBase):
    name = "my_agent"
    system_prompt = "..."
    # default strategy is ReActStrategy

    def __init__(self):
        super().__init__()
        self.strategy = ReActStrategy()
```

### Execution

`AgentExecutorImpl` drives the full loop:

```
LLM → Thought → Tool call / Respond → Observation → LLM → ... → Final answer
```

It integrates optional services resolved from the container at boot:

- **`LLMClientProtocol`** (required) — the LLM backend
- **`AIGovernanceProtocol`** (optional) — budget/rate limits
- **`WorkingMemoryProtocol`** (optional) — episodic/semantic memory context
- **`GuardPipelineProtocol`** (optional) — input/output guardrails
- **`EventBusProtocol`** (optional) — execution events
- **`SkillExecutorProtocol`** / **`SkillRegistryProtocol`** (optional) — skill integration
- **`SessionManagerProtocol`** (optional) — multi-turn session management
- **`MetricsRecorderProtocol`** / **`TracerProtocol`** (optional) — observability

## Typical Usage

### Quick wiring (no modules)

```python
from lexigram import Application
from lexigram.ai.agents import AgentsProvider, AgentConfig
from lexigram.contracts.ai import AgentExecutorProtocol

config = AgentConfig(max_iterations=15)
provider = AgentsProvider(config=config)

async with Application.boot(name="app", providers=[provider]) as app:
    executor = await app.container.resolve(AgentExecutorProtocol)
    result = await executor.run(agent=MyAgent(), message="Hello")
```

### With DI modules

```python
from lexigram import Application
from lexigram.ai.agents import AgentsModule, AgentConfig
from lexigram.contracts.ai import AgentExecutorProtocol

config = AgentConfig(max_iterations=15)

async with Application.boot(
    name="app",
    modules=[AgentsModule.configure(config)],
) as app:
    executor = await app.container.resolve(AgentExecutorProtocol)
    ...
```

### Multi-agent with SupervisorStrategy

```python
from lexigram.ai.agents.strategies import SupervisorStrategy

class Supervisor(AgentBase):
    name = "supervisor"
    system_prompt = "You route tasks to the right sub-agent."

    @property
    def tools(self):
        return [search_kb, billing_tool]

    def __init__(self):
        super().__init__()
        self.strategy = SupervisorStrategy(
            agents=[SupportAgent(), BillingAgent()]
        )
```

## Common Patterns

### Tool retries

Configurable via `tool_max_retries` (default 3). Transient errors (`ConnectionError`, `TimeoutError`) trigger retries automatically.

### Governance integration

When `AIGovernanceProtocol` is available, every execution is checked against budget limits before starting. If the budget is exceeded, `executor.run()` returns `Err(BudgetExceededError)`.

### Guard pipeline

When `GuardPipelineProtocol` is available, input is checked before execution and output after. Blocked input returns `Err` immediately; redacted content passes through with the redacted text.

## Result Handling

All execution methods return `Result[T, E]`:

```python
from lexigram.result import Result, Ok, Err
from lexigram.contracts.ai.agents import AgentResponse, AgentError

result: Result[AgentResponse, AgentError] = await executor.run(...)

if result.is_ok():
    response = result.unwrap()
    print(response.message)           # final answer
    print(response.total_tokens)      # token usage
    print(response.duration_ms)       # execution time
    print(response.tool_calls)        # all tool invocations
else:
    error = result.unwrap_err()
    print(f"Agent failed: {error}")
```

## Crew (Multi-Agent Orchestration)

For structured multi-agent workflows (not free-form supervision), use `Crew`:

```python
from lexigram.ai.agents import CrewBuilder, Process, CrewTask

crew = (
    CrewBuilder()
    .add_agent(ResearchAgent(), role="researcher")
    .add_agent(WriterAgent(), role="writer")
    .add_task(CrewTask(description="Research topic", agent_role="researcher"))
    .add_task(CrewTask(description="Write report", agent_role="writer"))
    .process(Process.SEQUENTIAL)
    .build()
)

result = await crew.kickoff()
print(result.tasks[0].output)
```

## Next Steps

- [How-Tos](./HOWTOS.md) — recipes for common scenarios
- [Architecture](./ARCHITECTURE.md) — internal design and extension points
- [API Reference](./API.md) — full API docs
