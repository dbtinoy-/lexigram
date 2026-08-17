---
title: lexigram-ai-skills Guide
description: Core concepts, common workflows, and best practices.
sidebar:
  order: 2
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-ai-llm` | Optional | LLM-powered skills |
| `lexigram-cache` | Optional | Skill result caching |

## Problem

AI agents and applications need to expose composable, discoverable capabilities — call an LLM, query a database, search the web, read a file. Each capability needs parameter validation, permission checks, result caching, timeout enforcement, and retry logic. **lexigram-ai-skills** provides a unified framework for defining, registering, discovering, and executing these capabilities.

## Mental model

Think of the skill system as a **toolbox**:

1. **Define** skills (each skill is a self-contained async function with a typed interface)
2. **Register** them in a `SkillRegistry` (the toolbox)
3. **Execute** them by name via a `SkillExecutor` (the hand that picks the right tool and uses it)

The executor handles every cross-cutting concern automatically — validation, permissions, caching, retries, timeouts — so your skill logic stays pure.

## Core concepts

### SkillProtocol

Every skill implements `SkillProtocol` from `lexigram.contracts.ai.skills`. It has three members:

- `definition` — a `SkillDefinition` with name, description, parameter schema, category, permissions
- `execute(**kwargs)` — the async implementation, returning `Result[SkillResult, SkillError]`
- `validate(params)` — parameter validation against the schema

There are **three ways to define a skill**:

#### 1. AbstractSkill subclass

```python
from lexigram.ai.skills import AbstractSkill
from lexigram.contracts.ai.skills import SkillDefinition, SkillResult
from lexigram.result import Ok


class GreetSkill(AbstractSkill):
    @property
    def definition(self) -> SkillDefinition:
        return SkillDefinition(
            name="greet",
            description="Greet someone by name",
            parameters_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            category="utility",
        )

    async def execute(self, **kwargs: dict) -> Result:
        name = kwargs.get("name", "World")
        return Ok(SkillResult(
            skill_name="greet",
            success=True,
            output=f"Hello, {name}!",
        ))
```

#### 2. @skill decorator (function-based)

```python
from lexigram.ai.skills import skill, skill_param


@skill_param("name", type="string", description="Name to greet", required=True)
@skill(name="greet_fn", description="Greet someone by name", category="utility")
async def greet_fn(name: str) -> str:
    return f"Hello, {name}!"
```

#### 3. ToolSkillAdapter (from ToolProtocol)

Existing `ToolProtocol` objects can participate in the skill system via `SkillRegistry.register_tool()`.

### SkillRegistry

The central catalog. Register skills, look them up by name, list by category or permissions, export OpenAI-compatible schemas for LLM function calling.

```python
from lexigram.ai.skills import SkillRegistry

registry = SkillRegistry()
registry.register(GreetSkill())

# Lookup
skill = registry.get("greet")

# List with filters
defs = registry.list_skills(category="utility")

# OpenAI-compatible schemas
schemas = registry.get_schemas()
```

### SkillExecutor

The production-grade execution engine with full lifecycle:

```python
from lexigram.ai.skills import SkillExecutor, SkillRegistry
from lexigram.ai.skills import PermissionChecker

registry = SkillRegistry()
registry.register(GreetSkill())

permissions = PermissionChecker()
permissions.grant("user-42", {"admin"})

executor = SkillExecutor(
    registry=registry,
    permission_checker=permissions,
)

result = await executor.execute("greet", {"name": "Alice"}, user_id="user-42")
if result.is_ok():
    print(result.unwrap().output)
```

The executor handles:
1. **Skill resolution** — `SkillNotFoundError` if missing
2. **Permission check** — `SkillPermissionDeniedError` if denied
3. **Parameter validation** — `SkillValidationError` if invalid
4. **Cache lookup** — returns cached result if cacheable
5. **Execution with retry** — exponential backoff up to `max_retries`
6. **Timeout enforcement** — `SkillTimeoutError` if exceeded
7. **Cache storage** — stores result if cacheable

### Built-in skills

The package ships with ready-to-use skills:

| Skill name | Class | Description |
|---|---|---|
| `current_datetime` | `DateTimeSkill` | Current date and time |
| `math_calculate` | `MathSkill` | Math expression evaluation |
| `text_summarize` | `TextSummarizeSkill` | Text summarization |
| `text_translate` | `TextTranslateSkill` | Text translation |
| `web_search` | `WebSearchSkill` | Web search |
| `http_request` | `HTTPRequestSkill` | HTTP requests |
| `file_read` | `FileReadSkill` | File reading |
| `file_write` | `FileWriteSkill` | File writing |
| `code_execute` | `CodeExecutionSkill` | Code execution |

Enable them via config: `SkillsConfig(enable_builtin=True, builtin_skills=["current_datetime", "math_calculate"])`.

### Skill composition

Skills can be composed into higher-level workflows:

- **SkillChain** — execute skills sequentially, passing output as input
- **ParallelSkills** — execute skills concurrently
- **SkillPipeline** — structured pipeline with transformation stages
- **SkillRouter** — route execution based on input conditions

```python
from lexigram.ai.skills import SkillChain

chain = SkillChain(["skill_a", "skill_b"], executor=executor)
result = await chain.execute({"input": "value"})
```

### Caching

Skill results can be cached with `SkillResultCache`. The cache uses a two-tier architecture — in-process dict and optional `CacheBackendProtocol` (e.g., Redis). Enable caching per skill by setting `cacheable=True` in the `SkillDefinition`.

```python
from lexigram.ai.skills import SkillResultCache

cache = SkillResultCache(ttl_seconds=3600)
executor = SkillExecutor(registry=registry, cache=cache)
```

### Permissions

The `PermissionChecker` provides user-level permission enforcement. Skills declare required permissions in their definition.

```python
from lexigram.ai.skills import PermissionChecker

checker = PermissionChecker()
checker.grant("user-42", {"admin", "files.read"})
checker.check("user-42", {"admin"})  # True
```

When `enforce_permissions` is enabled in config, the provider registers a `PermissionChecker` and the executor checks permissions before execution.

## Best practices

- **Use `@skill` for simple functions**, `AbstractSkill` for complex skills with custom validation
- **Always handle the `Result` type** — check `is_ok()` before accessing output
- **Enable caching for deterministic skills** — mark `cacheable=True` in the definition
- **Organize skills by category** — use meaningful category names for discoverability
- **Set appropriate timeouts** — override `timeout_seconds` per skill, not just globally
- **Use `SkillModule.stub()` in tests** — provides a lightweight in-memory setup

## Next steps

- [Architecture](/packages/lexigram-ai-skills/architecture/) — provider lifecycle, module mapping, extension points
- [Configuration](/packages/lexigram-ai-skills/configuration/) — full config reference
- [How-tos](/packages/lexigram-ai-skills/howtos/) — task-oriented recipes
- [Troubleshooting](/packages/lexigram-ai-skills/troubleshooting/) — common errors and fixes
