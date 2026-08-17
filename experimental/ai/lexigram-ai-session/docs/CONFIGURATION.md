---
title: lexigram-ai-session Configuration
description: All configuration keys for the session management subsystem.
sidebar:
  order: 4
---

Config section: `ai_session`  
Env prefix: `LEX_AI_SESSION__`

```yaml
# application.yaml
ai_session:
  backend: database
  session_ttl: 86400
  auto_checkpoint_interval: 10
  max_turns_per_session: 1000
```

## Reference table

| Key | Type | Default | Env var | Description |
|---|---|---|---|---|
| `enabled` | `bool` | `True` | `LEX_AI_SESSION__ENABLED` | Enable the AI session subsystem |
| `name` | `str` | `"ai-session"` | `LEX_AI_SESSION__NAME` | Logical DI registration key |
| `default_system_prompt` | `str \| None` | `None` | `LEX_AI_SESSION__DEFAULT_SYSTEM_PROMPT` | System prompt injected into every new session |
| `session_ttl` | `int` | `86400` | `LEX_AI_SESSION__SESSION_TTL` | Max session age in seconds (0 to disable) |
| `cleanup_interval_s` | `int` | `600` | `LEX_AI_SESSION__CLEANUP_INTERVAL_S` | Cleanup sweep interval in seconds |
| `max_turns_per_session` | `int` | `1000` | `LEX_AI_SESSION__MAX_TURNS_PER_SESSION` | Hard cap on turns before session closes |
| `max_sessions_per_user` | `int` | `100` | `LEX_AI_SESSION__MAX_SESSIONS_PER_USER` | Maximum concurrent sessions per user |
| `auto_checkpoint_interval` | `int \| None` | `10` | `LEX_AI_SESSION__AUTO_CHECKPOINT_INTERVAL` | Checkpoint every N turns; `None` to disable |
| `max_checkpoints_per_session` | `int` | `50` | `LEX_AI_SESSION__MAX_CHECKPOINTS_PER_SESSION` | Maximum retained checkpoints per session |
| `max_branches_per_session` | `int` | `10` | `LEX_AI_SESSION__MAX_BRANCHES_PER_SESSION` | Maximum forked branches per session |
| `max_agents_per_group` | `int` | `10` | `LEX_AI_SESSION__MAX_AGENTS_PER_GROUP` | Maximum agents in a multi-agent group session |
| `default_turn_strategy` | `str` | `"round_robin"` | `LEX_AI_SESSION__DEFAULT_TURN_STRATEGY` | Default turn strategy (`round_robin`, `priority`, `llm_directed`) |
| `backend` | `str` | `"in_memory"` | `LEX_AI_SESSION__BACKEND` | Persistence backend (`in_memory`, `cache`, `database`) |
| `cookie_name` | `str \| None` | `"lexigram_session"` | `LEX_AI_SESSION__COOKIE_NAME` | Cookie name for web session ID; `None` disables cookies |
| `header_name` | `str` | `"X-Session-ID"` | `LEX_AI_SESSION__HEADER_NAME` | HTTP header name for session ID pass-through |
| `consolidate_on_close` | `bool` | `True` | `LEX_AI_SESSION__CONSOLIDATE_ON_CLOSE` | Trigger memory consolidation on session close |

## Env var override example

```bash
export LEX_AI_SESSION__BACKEND=database
export LEX_AI_SESSION__SESSION_TTL=43200
export LEX_AI_SESSION__MAX_TURNS_PER_SESSION=500
export LEX_AI_SESSION__AUTO_CHECKPOINT_INTERVAL=5
```

## Production example

```yaml
ai_session:
  backend: database
  session_ttl: 43200
  cleanup_interval_s: 300
  max_turns_per_session: 500
  max_sessions_per_user: 50
  auto_checkpoint_interval: 5
  max_checkpoints_per_session: 100
  consolidate_on_close: true
  cookie_name: session_id
  header_name: X-Session-ID
```

:::caution
In production, set `backend` to `"cache"` or `"database"`. The in-memory backend does not survive process restarts. `SessionConfig.validate_for_environment(Environment.PRODUCTION)` raises a `ConfigIssue` if the in-memory backend is used.
:::
