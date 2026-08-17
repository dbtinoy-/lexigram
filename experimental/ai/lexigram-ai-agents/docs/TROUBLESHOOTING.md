---
title: lexigram-ai-agents Troubleshooting
description: Common errors, causes, and fixes.
---

## `AgentConfigurationError: AgentBase must have a name`

**Cause:** An `AgentBase` subclass was defined without setting `name`.

**Fix:** Set `name` on the class:

```python
class MyAgent(AgentBase):
    name = "my_agent"
    ...
```

**Exception:** `lexigram.ai.agents.exceptions.AgentConfigurationError`

---

## `AgentExecutionError: LLM not configured`

**Cause:** `AgentExecutorImpl.run()` was called but no `LLMClientProtocol` was registered in the container.

**Fix:** Ensure an LLM provider (e.g., `lexigram-ai-llm`) is wired before agent execution:

```python
# Register LLMProvider before AgentsProvider
app.add_provider(LLMProvider(config=LLMConfig(api_key=...)))
```

**Exception:** `lexigram.ai.agents.exceptions.AgentExecutionError`

---

## `BudgetExceededError`

**Cause:** The governance system denied execution because the token or cost budget was exceeded.

**Fix:** Increase the budget or reduce token usage:

```python
from lexigram.ai.agents.exceptions import BudgetExceededError

result = await executor.run(agent=agent, message="...")
if result.is_err() and isinstance(result.unwrap_err(), BudgetExceededError):
    print("Budget limit reached")
```

**Exception:** `lexigram.ai.agents.exceptions.BudgetExceededError`

---

## `MaxIterationsExceededError`

**Cause:** The agent reached `max_iterations` without producing a final response — it's stuck in a loop.

**Fix:** Increase `max_iterations` in config or simplify the task:

```yaml
ai_agents:
  max_iterations: 25
```

**Exception:** `lexigram.ai.agents.exceptions.MaxIterationsExceededError`

---

## `ToolNotFoundError: Tool not found: <name>`

**Cause:** The LLM tried to call a tool that isn't registered.

**Fix:** Ensure the tool is in the agent's `tools` list and registered:

```python
class MyAgent(AgentBase):
    name = "my_agent"
    system_prompt = "..."
    _tools = [my_tool]  # must return from tools property

    @property
    def tools(self):
        return self._tools
```

**Exception:** `lexigram.ai.agents.exceptions.ToolNotFoundError`

---

## `ToolExecutionError: Tool execution failed: <name>`

**Cause:** The tool function raised an exception during execution.

**Fix:** Wrap tool logic in try/except or add input validation:

```python
@tool
async def safe_tool(data: dict) -> dict:
    try:
        return await process(data)
    except ValueError as e:
        return {"error": str(e)}
```

**Exception:** `lexigram.ai.agents.exceptions.ToolExecutionError`

---

## Agent execution returns `Err` with generic `AgentError`

**Cause:** A non-`AgentError` exception was raised during execution (e.g., network failure in the strategy loop).

**Fix:** Check `result.unwrap_err()` for details. Ensure all strategy and LLM dependencies are properly configured.

**Exception:** `lexigram.contracts.ai.agents.AgentError`
