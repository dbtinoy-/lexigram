---
title: lexigram-ai-skills Configuration
description: All configuration keys for the skills subsystem.
sidebar:
  order: 4
---

Config section: `ai_skills`  
Env prefix: `LEX_AI_SKILLS__`

```yaml
# application.yaml
ai_skills:
  enable_builtin: true
  builtin_skills:
    - current_datetime
    - math_calculate
  cache_enabled: true
  cache_ttl_seconds: 3600
```

## Reference table

| Key | Type | Default | Env var | Description |
|---|---|---|---|---|
| `name` | `str` | `"ai-skills"` | `LEX_AI_SKILLS__NAME` | Logical DI registration key |
| `default_timeout_seconds` | `float` | `30.0` | `LEX_AI_SKILLS__DEFAULT_TIMEOUT_SECONDS` | Default execution timeout per skill |
| `max_retries` | `int` | `2` | `LEX_AI_SKILLS__MAX_RETRIES` | Default max retry attempts |
| `max_concurrent_executions` | `int` | `10` | `LEX_AI_SKILLS__MAX_CONCURRENT_EXECUTIONS` | Semaphore cap on concurrent executions |
| `cache_enabled` | `bool` | `True` | `LEX_AI_SKILLS__CACHE_ENABLED` | Whether result caching is globally enabled |
| `cache_ttl_seconds` | `int` | `3600` | `LEX_AI_SKILLS__CACHE_TTL_SECONDS` | Default TTL for cached results |
| `cache_backend` | `str` | `"in_memory"` | `LEX_AI_SKILLS__CACHE_BACKEND` | Cache backend (`in_memory`, `cache`) |
| `enforce_permissions` | `bool` | `True` | `LEX_AI_SKILLS__ENFORCE_PERMISSIONS` | Whether permission checks are enforced |
| `auto_discover` | `bool` | `False` | `LEX_AI_SKILLS__AUTO_DISCOVER` | Whether to auto-scan packages on boot |
| `scan_packages` | `list[str]` | `[]` | `LEX_AI_SKILLS__SCAN_PACKAGES` | Package names to scan for skills |
| `enable_builtin` | `bool` | `True` | `LEX_AI_SKILLS__ENABLE_BUILTIN` | Register built-in skills on boot |
| `builtin_skills` | `list[str]` | `["current_datetime", "math_calculate", "text_summarize"]` | `LEX_AI_SKILLS__BUILTIN_SKILLS` | Built-in skill names to register |
| `enable_skill_sources` | `bool` | `True` | `LEX_AI_SKILLS__ENABLE_SKILL_SOURCES` | Scan for external skill sources on boot |
| `skill_paths` | `list[str]` | `["~/.claude/skills", "~/.opencode/skills", "./skills"]` | `LEX_AI_SKILLS__SKILL_PATHS` | Paths to scan for SKILL.md folders |
| `enabled_directories` | `list[str]` | `["claude_code", "opencode", "codex", "gemini_cli", "aider", "cursor", "copilot", "windsurf", "custom"]` | `LEX_AI_SKILLS__ENABLED_DIRECTORIES` | Which skill directories to enable |
| `script_timeout_seconds` | `int` | `30` | `LEX_AI_SKILLS__SCRIPT_TIMEOUT_SECONDS` | Timeout for skill script execution |
| `allowed_script_types` | `list[str]` | `["py", "sh", "js"]` | `LEX_AI_SKILLS__ALLOWED_SCRIPT_TYPES` | Allowed script types for external skills |
| `lazy_load_context` | `bool` | `True` | `LEX_AI_SKILLS__LAZY_LOAD_CONTEXT` | Lazily load skill context files |

## Env var override example

```bash
export LEX_AI_SKILLS__ENABLE_BUILTIN=false
export LEX_AI_SKILLS__CACHE_TTL_SECONDS=7200
export LEX_AI_SKILLS__AUTO_DISCOVER=true
export LEX_AI_SKILLS__SCAN_PACKAGES='["my_app.skills"]'
```

## Production example

```yaml
ai_skills:
  enable_builtin: true
  builtin_skills:
    - current_datetime
    - math_calculate
    - text_summarize
    - http_request
  cache_enabled: true
  cache_ttl_seconds: 1800
  enforce_permissions: true
  auto_discover: true
  scan_packages:
    - my_app.skills
  enable_skill_sources: false
```
