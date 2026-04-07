---
title: "AI Skills"
description: "Register, compose, and execute callable skills for AI agents and MCP."
---

`lexigram-ai-skills` provides a registry-based skill system where agents can discover, validate, and execute composable capabilities. Skills are async functions or classes registered by name, with JSON Schema parameter validation, caching, permission checking, and execution lifecycle management.

For full configuration details, see the [`lexigram-ai-skills` package docs](/packages/lexigram-ai-skills/).

---

## 1. The Contracts

The skill system is built on three core protocols from `lexigram.contracts.ai.skills`:

```python
from typing import Any, Protocol, runtime_checkable
from lexigram.result import Result
from lexigram.contracts.ai.skills import (
    SkillDefinition, SkillResult, SkillError,
)


class SkillProtocol(Protocol):
    @property
    def definition(self) -> SkillDefinition: ...
    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]: ...
    def validate(self, params: dict[str, Any]) -> list[str]: ...


class SkillRegistryProtocol(Protocol):
    def register(self, skill: SkillProtocol) -> None: ...
    def get(self, name: str) -> SkillProtocol | None: ...
    def list_skills(
        self, category: str | None = None, permissions: list[str] | None = None,
    ) -> list[SkillDefinition]: ...
    def get_schemas(self) -> list[dict[str, Any]]: ...


class SkillExecutorProtocol(Protocol):
    async def execute(
        self,
        skill_name: str,
        params: dict[str, Any],
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> Result[SkillResult, SkillError]: ...
```

`SkillDefinition` and `SkillResult` are the core data types:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    description: str
    parameters_schema: dict[str, Any] = field(default_factory=dict)
    category: str = "general"
    requires_confirmation: bool = False
    cacheable: bool = False
    timeout_seconds: float = 30.0
    permissions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SkillResult:
    skill_name: str
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    cached: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
```

---

## 2. Configuration

Add `SkillsModule` and configure execution defaults:

```python
from lexigram import Application
from lexigram.ai.skills import SkillsModule, SkillsConfig

app = Application(name="my-app")
app.add_module(SkillsModule.configure(
    SkillsConfig(
        enable_builtin=True,
        builtin_skills=["current_datetime", "web_search", "math_calculate"],
        default_timeout_seconds=30.0,
    ),
))
```

```yaml title="application.yaml"
ai_skills:
  name: ai-skills
  default_timeout_seconds: 30.0
  max_retries: 2
  max_concurrent_executions: 10
  cache_enabled: true
  cache_ttl_seconds: 300
  cache_backend: in_memory
  enforce_permissions: false
  auto_discover: false
  enable_builtin: true
  builtin_skills:
    - current_datetime
    - math_calculate
    - web_search
    - web_fetch
```

:::note
Built-in skills are registered automatically when `enable_builtin: true`. The `builtin_skills` list filters which ones are active.
:::

---

## 3. Defining Skills

Use the `@skill` decorator to register a class as a skill:

```python
from lexigram.ai.skills import skill


@skill(
    name="generate_summary",
    description="Generate a summary of the given text",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The text to summarize"},
            "max_length": {"type": "integer", "description": "Max summary length"},
        },
        "required": ["text"],
    },
)
class GenerateSummary:
    async def execute(self, text: str, max_length: int = 100) -> str:
        # Implementation
        return text[:max_length] + "..."
```

For simple functions, use `FunctionSkill`:

```python
from lexigram.ai.skills import FunctionSkill


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    # Implementation
    return [{"title": "Result", "url": "https://example.com"}]


search_skill = FunctionSkill(
    name="web_search",
    description="Search the web for information",
    execute_fn=web_search,
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer"},
        },
        "required": ["query"],
    },
)
```

---

## 4. Registering and Executing

Register skills with the registry and execute them through the executor:

```python
from lexigram import Application
from lexigram.ai.skills import SkillsModule, SkillsConfig
from lexigram.contracts.ai.skills import (
    SkillRegistryProtocol,
    SkillExecutorProtocol,
)


async def skill_workflow() -> None:
    async with Application.boot(
        modules=[SkillsModule.configure(SkillsConfig(enable_builtin=True))]
    ) as app:
        registry = await app.container.resolve(SkillRegistryProtocol)
        executor = await app.container.resolve(SkillExecutorProtocol)

        for skill_def in registry.list_skills():
            print(f"{skill_def.name}: {skill_def.description}")

        result = await executor.execute(
            skill_name="current_datetime",
            params={"format": "%Y-%m-%d %H:%M:%S"},
        )
        if result.is_ok():
            sr = result.unwrap()
            print(f"Output: {sr.output}, Duration: {sr.duration_ms}ms")
```

---

## 5. Built-in Skills

The framework ships with several built-in skills:

| Skill | Description |
|-------|-------------|
| `current_datetime` | Get the current date and time |
| `math_calculate` | Evaluate mathematical expressions |
| `web_search` | Search the web for information |
| `web_fetch` | Fetch content from a URL |
| `text_summarize` | Summarize text content |
| `text_translate` | Translate text between languages |
| `code_execute` | Execute code in a sandbox |

Built-in skills are registered during boot when `enable_builtin: true` and their names appear in the `builtin_skills` list.

---

## 6. Skill Composition

Chain skills using `SkillPipeline`:

```python
from lexigram.ai.skills import SkillPipeline


async def composed_workflow() -> None:
    pipeline = SkillPipeline(steps=[
        ("web_search", {"query": "{query}"}),
        ("text_summarize", {"text": "{web_search.output}"}),
    ])
    result = await pipeline.execute(query="latest AI research")
```

`ParallelSkills` runs skills concurrently; `SkillRouter` dispatches based on input.

---

## 7. Testing

Use `SkillsModule.stub()` for isolated tests:

```python
from lexigram import Application
from lexigram.ai.skills import SkillsModule
from lexigram.contracts.ai.skills import SkillExecutorProtocol


async def test_skill_executor_resolves() -> None:
    async with Application.boot(modules=[SkillsModule.stub()]) as app:
        executor = await app.container.resolve(SkillExecutorProtocol)
        assert executor is not None
```

:::caution
The stub disables built-in skills and the tool bridge. Register test-specific skills manually when testing skill execution.
:::

---

## Next Steps

- [AI Agents](/guides/ai-agents/) — connecting skills to agent tool registries
- [AI RAG](/guides/ai-rag/) — retrieval-augmented generation
- [Dependency Injection](/fundamentals/dependency-injection/) — binding protocols
- [`lexigram-ai-skills` package](/packages/lexigram-ai-skills/) — MCP bridge, discovery, caching
