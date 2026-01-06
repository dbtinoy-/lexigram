---
title: lexigram-ai-skills Troubleshooting
description: Common errors, causes, and fixes.
sidebar:
  order: 6
---

## Skill not found

```
SkillNotFoundError: Skill not found: 'my_skill'
```

**Cause:** The skill name was not registered in the registry.

**Fix:** Ensure the skill is registered before execution:

```python
registry.register(MySkill())
# Verify registration
assert registry.get("my_skill") is not None
```

If using auto-discovery, check `scan_packages` config and confirm the package is importable.

---

## Skill already registered

```
SkillAlreadyRegisteredError: Skill already registered: 'my_skill'
```

**Cause:** Two skills with the same name were registered.

**Fix:** Use unique skill names, or check registration with `"my_skill" in registry` before registering.

---

## Permission denied

```
SkillPermissionDeniedError: Permission denied for 'admin_skill'. Required: ['admin']
```

**Cause:** The caller lacks required permissions for this skill.

**Fix:** Grant the required permissions:

```python
checker.grant("user-42", {"admin", "files.read"})
```

Or skip the permission check by omitting `user_id`:

```python
result = await executor.execute("admin_skill", {})  # no permission check
```

---

## Parameter validation failed

```
SkillValidationError: Validation failed for 'greet': 'name' is a required property
```

**Cause:** Required parameters were missing or had the wrong type.

**Fix:** Check the skill's `parameters_schema` and supply all required parameters:

```python
schema = registry.get("greet").definition.parameters_schema
print(schema["required"])  # ['name']
result = await executor.execute("greet", {"name": "Alice"})
```

---

## Skill timeout

```
SkillTimeoutError: Skill 'web_search' timed out after 30.0s
```

**Cause:** The skill execution exceeded its configured timeout.

**Fix:** Increase the timeout in the skill definition or config:

```python
SkillDefinition(
    name="web_search",
    description="Search the web",
    timeout_seconds=60.0,
)
```

Or globally via config: `default_timeout_seconds: 60.0`.

---

## Execution failed after retries

```
SkillExecutionError: Skill 'api_call' failed after 3 retries
```

**Cause:** The skill raised an error on every attempt. Check the `cause` attribute for the underlying exception.

**Fix:** Inspect the error details and address the root cause. Consider increasing `max_retries` for transient failures.

---

## Router found no matching route

```
SkillRoutingError: No matching route
```

**Cause:** A `SkillRouter` was given input that did not match any registered route condition.

**Fix:** Review the router's route definitions and ensure the input satisfies at least one condition.

---

## Built-in skill not found during boot

```
WARNING  skills_unknown_builtin skill='some_skill'
```

**Cause:** The name in `builtin_skills` config is not in the built-in map.

**Fix:** Use one of the valid built-in skill names: `current_datetime`, `math_calculate`, `text_summarize`, `text_translate`, `web_search`, `http_request`, `file_read`, `file_write`, `code_execute`.
