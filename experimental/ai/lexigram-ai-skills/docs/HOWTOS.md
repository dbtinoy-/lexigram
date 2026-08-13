---
title: lexigram-ai-skills How-tos
description: Task-oriented recipes for common skill operations.
sidebar:
  order: 5
---

## Register and execute a skill directly

```python
from lexigram.ai.skills import SkillRegistry, SkillExecutor

registry = SkillRegistry()
registry.register(MySkill())

executor = SkillExecutor(registry=registry)
result = await executor.execute("my_skill", {"param": "value"})
if result.is_ok():
    print(result.unwrap().output)
```

## Create a skill with the @skill decorator

```python
from lexigram.ai.skills import skill, skill_param


@skill_param("a", type="number", description="First number", required=True)
@skill_param("b", type="number", description="Second number", required=True)
@skill(name="add", description="Add two numbers", category="math", cacheable=True)
async def add(a: float, b: float) -> float:
    return a + b
```

## Wire skills into your application

```python
from lexigram import Application, LexigramConfig
from lexigram.ai.skills import SkillsModule
from lexigram.ai.skills import SkillsConfig

config = LexigramConfig.from_yaml()
app = Application(name="my-app", config=config)
app.add_module(SkillsModule.configure(
    SkillsConfig(enable_builtin=True, builtin_skills=["current_datetime"]),
    enable_tool_bridge=True,
))
```

## Enable caching for deterministic skills

```python
from lexigram.contracts.ai.skills import SkillDefinition, SkillResult
from lexigram.result import Ok


class CachedWeatherSkill(AbstractSkill):
    @property
    def definition(self) -> SkillDefinition:
        return SkillDefinition(
            name="get_weather",
            description="Get weather for a city",
            parameters_schema={"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
            category="weather",
            cacheable=True,  # enables caching
        )

    async def execute(self, **kwargs):
        city = kwargs["city"]
        return Ok(SkillResult(skill_name="get_weather", success=True, output={"city": city, "temp": 22}))
```

## Use skills as agent tools

```python
from lexigram.ai.skills import SkillRegistry

registry = SkillRegistry()
registry.register(MySkill())

# Convert a skill to a tool for agent integration
skill_tool = MySkill().to_tool()

# Or register an existing tool as a skill
registry.register_tool(existing_tool)
```

## Chain skills sequentially

```python
from lexigram.ai.skills import SkillChain, SkillRegistry, SkillExecutor

registry = SkillRegistry()
registry.register(SkillA())
registry.register(SkillB())
executor = SkillExecutor(registry=registry)

chain = SkillChain(["skill_a", "skill_b"], executor=executor)
result = await chain.execute({"input": "value"})
```

## Validate skill parameters manually

```python
from lexigram.ai.skills import validate_params

errors = validate_params({"name": "Alice"}, {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
})
if errors:
    print("Validation failed:", errors)
```

## Run skills in parallel

```python
from lexigram.ai.skills import ParallelSkills, SkillRegistry, SkillExecutor

registry = SkillRegistry()
registry.register(AnalyzeSentimentSkill())
registry.register(ExtractEntitiesSkill())
executor = SkillExecutor(registry=registry)

parallel = ParallelSkills(["analyze_sentiment", "extract_entities"])
result = await parallel.execute(executor, {"text": "I love this product!"})
combined = result.unwrap().output
# combined == {"analyze_sentiment": {...}, "extract_entities": {...}}
```

## Build a transformation pipeline

```python
from lexigram.ai.skills import SkillPipeline

pipeline = SkillPipeline()
pipeline.add_stage("normalise_text", output_key="clean")
pipeline.add_stage("extract_entities", output_key="entities")
result = await pipeline.execute(executor, {"raw_text": "Hello from Lexigram!"})
# result.unwrap().output == {"raw_text": "...", "clean": "...", "entities": [...]}
```

## Auto-discover skills from modules

```python
from lexigram.ai.skills import SkillRegistry, ModuleScanner

registry = SkillRegistry()
scanner = ModuleScanner()
count = await scanner.scan(registry, "myapp.skills.builtin")
print(f"Registered {count} skills from myapp.skills.builtin")

# Recursively scan an entire package
total = await scanner.scan_package(registry, "myapp.skills")
print(f"Registered {total} skills across all sub-modules")
```

## Add permissions to skills

```python
from lexigram.ai.skills import PermissionChecker

checker = PermissionChecker()
checker.grant("user-42", {"admin", "files.read"})
checker.grant("user-99", {"files.read"})

# Use with executor
executor = SkillExecutor(registry=registry, permission_checker=checker)
result = await executor.execute("admin_skill", {}, user_id="user-42")
```
