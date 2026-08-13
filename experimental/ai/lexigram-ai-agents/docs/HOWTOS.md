---
title: lexigram-ai-agents How-Tos
description: Task-oriented recipes for common agent patterns.
---

## How to define a tool

```python
from lexigram.ai.agents import tool


@tool
async def calculate_total(items: list[dict]) -> float:
    """Calculate the total price of items in a cart.

    Args:
        items: List of items with "price" and "quantity" keys.
    """
    return sum(item["price"] * item["quantity"] for item in items)
```

## How to create an agent with multiple tools

```python
from lexigram.ai.agents import AgentBase, tool


@tool
async def search(query: str) -> str:
    """Search the knowledge base."""
    return f"Results for {query}"


@tool
async def get_stock(sku: str) -> int:
    """Check stock level for a SKU."""
    return 42


class StoreAgent(AgentBase):
    name = "store_agent"
    system_prompt = "You help customers with product questions."

    @property
    def tools(self):
        return [search, get_stock]
```

## How to use plan-and-execute strategy

```python
from lexigram.ai.agents import AgentBase
from lexigram.ai.agents.strategies import PlanAndExecuteStrategy


class ResearchAgent(AgentBase):
    name = "research_agent"
    system_prompt = "Research topics thoroughly."

    def __init__(self):
        super().__init__()
        self.strategy = PlanAndExecuteStrategy()

    @property
    def tools(self):
        return [search_tool]
```

## How to run an agent with governance and memory

```python
from lexigram import Application
from lexigram.ai.agents import AgentsModule, AgentConfig
from lexigram.ai.memory import MemoryModule, MemoryConfig
from lexigram.contracts.ai import AgentExecutorProtocol

config = AgentConfig(max_iterations=15)
memory_config = MemoryConfig()

async with Application.boot(
    name="app",
    modules=[
        AgentsModule.configure(config),
        MemoryModule.configure(memory_config),
    ],
) as app:
    executor = await app.container.resolve(AgentExecutorProtocol)
    result = await executor.run(
        agent=MyAgent(),
        message="What was my last order?",
        session_id="user-42",
        user_id="user-42",
    )
```

## How to handle execution errors

```python
from lexigram.contracts.ai.agents import AgentError
from lexigram.ai.agents.exceptions import (
    BudgetExceededError,
    MaxIterationsExceededError,
    ToolExecutionError,
)

result = await executor.run(agent=agent, message="Hello")

if result.is_err():
    error = result.unwrap_err()
    if isinstance(error, BudgetExceededError):
        print("Budget exceeded — top up and retry")
    elif isinstance(error, MaxIterationsExceededError):
        print("Agent got stuck — increase max_iterations or simplify")
    elif isinstance(error, ToolExecutionError):
        print(f"Tool {error.tool_name} failed: {error}")
    else:
        print(f"Agent error: {error}")
```

## How to configure strategy registry with custom strategy

```python
from lexigram.ai.agents import AgentStrategyRegistry
from lexigram.ai.agents.strategies import AbstractStrategy


class CustomStrategy(AbstractStrategy):
    async def execute(self, agent, llm, messages, **kwargs):
        # Custom reasoning loop
        ...


registry = AgentStrategyRegistry()
registry.register("custom", CustomStrategy)
```

## How to delegate agents as tools

```python
from lexigram.ai.agents import AgentAsToolAdapter

billing_tool = AgentAsToolAdapter(
    agent=billing_agent,
    executor=executor,
    user_id="user-42",
)


class SupervisorAgent(AgentBase):
    name = "supervisor"
    system_prompt = "Route tasks to the right sub-agent."

    @property
    def tools(self):
        return [billing_tool, support_tool]
```

## How to stream agent execution events

```python
from lexigram.ai.agents import AgentExecutorImpl
from lexigram.contracts.ai.agents import AgentEventType

executor = AgentExecutorImpl(llm=llm_client)

async for event in executor.astream(
    agent=my_agent,
    message="Where is my order?",
    session_id="session-123",
):
    if event.type == AgentEventType.THOUGHT:
        print(f"Thinking: {event.data['thought']}")
    elif event.type == AgentEventType.TOOL_START:
        print(f"Calling tool: {event.data['tool_name']}")
    elif event.type == AgentEventType.MESSAGE:
        print(f"Final: {event.data['message']}")
    elif event.type == AgentEventType.ERROR:
        print(f"Error: {event.data['error']}")
```

## How to react to agent lifecycle hooks

```python
from lexigram.ai.agents import AgentStartedHook, AgentCompletedHook, AgentToolCalledHook
from lexigram.contracts.core.hooks import HookRegistryProtocol


async def on_agent_started(payload: AgentStartedHook) -> None:
    print(f"Agent '{payload.agent_name}' started")


async def on_tool_called(payload: AgentToolCalledHook) -> None:
    print(f"Tool '{payload.tool_name}' called by '{payload.agent_name}'")


async def on_agent_completed(payload: AgentCompletedHook) -> None:
    print(f"Agent '{payload.agent_name}' finished")


hooks: HookRegistryProtocol = await container.resolve(HookRegistryProtocol)
hooks.register_action("agent_started", on_agent_started)
hooks.register_action("agent_tool_called", on_tool_called)
hooks.register_action("agent_completed", on_agent_completed)
```

## How to use Crew for multi-agent workflows

```python
from lexigram.ai.agents import CrewBuilder, CrewTask, Process

crew = (
    CrewBuilder()
    .add_agent(ResearchAgent(), role="researcher")
    .add_agent(WriterAgent(), role="writer")
    .add_task(CrewTask(
        description="Research quantum computing trends",
        agent_role="researcher",
    ))
    .add_task(CrewTask(
        description="Write summary based on research",
        agent_role="writer",
        depends_on=["researcher"],
    ))
    .process(Process.SEQUENTIAL)
    .build()
)

result = await crew.kickoff()
for task_result in result.tasks:
    print(task_result.output)
```
