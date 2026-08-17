---
title: lexigram-ai-session Troubleshooting
description: Common errors, causes, and fixes.
sidebar:
  order: 6
---

## Session not found

```
SessionNotFoundError: Session not found: 'abc-123'
```

**Cause:** The session ID does not exist in the store.

**Fix:** Verify the session was created. For missing IDs, create a new session or check the correct ID:

```python
state = await manager.get_state(session_id)
if state is None:
    state = await manager.create(user_id)
```

---

## Session closed

```
SessionClosedError: Session is closed and cannot be modified: 'abc-123'
```

**Cause:** An operation (add_turn, resume, etc.) was attempted on a closed session.

**Fix:** Create a new session instead. Sessions cannot be reopened after closing.

---

## Session expired

```
SessionExpiredError: Session has expired: 'abc-123'
```

**Cause:** The session's TTL was exceeded and it was automatically expired.

**Fix:** Increase `session_ttl` in config, or disable expiry (set to `0`). Create a new session for the user.

---

## Session capacity exceeded

```
SessionCapacityError: Session capacity exceeded: session 'abc-123' has reached the turn limit (1000)
SessionCapacityError: Session capacity exceeded: user 'user-42' already has 100 active sessions (max 100)
```

**Cause:** Either the per-session turn limit or per-user session limit was reached.

**Fix:** Increase `max_turns_per_session` or `max_sessions_per_user` in config. Alternatively, close unused sessions.

---

## Invalid state transition

```
SessionTransitionError: Invalid transition for session 'abc-123': 'active' → 'active'
```

**Cause:** An invalid state transition was attempted (e.g., resuming an already-active session).

**Fix:** Check the session's current status before calling state-changing methods:

```python
state = await manager.get_state(session_id)
if state.status == SessionStatus.SUSPENDED:
    await manager.resume(session_id)
elif state.status == SessionStatus.ACTIVE:
    print("Already active")
```

---

## Checkpoint not found

```
CheckpointNotFoundError: Checkpoint not found: 'cp-456'
```

**Cause:** The checkpoint ID does not exist.

**Fix:** Verify the checkpoint ID. List checkpoints for the session:

```python
from lexigram.ai.session import CheckpointManager

cp_mgr = CheckpointManager(store=store)
checkpoints = await cp_mgr.list_checkpoints(session_id)
```

---

## In-memory backend in production

```
ConfigIssue: severity=error, field=backend, message=In-memory session backend used in production
```

**Cause:** `SessionConfig.backend` is set to `"in_memory"` in a production environment.

**Fix:** Set `backend: cache` or `backend: database` in your production config:

```yaml
ai_session:
  backend: database
```

---

## Cleanup scheduler failed to start

```
WARNING  failed_to_start_session_cleanup error='...'
```

**Cause:** The background cleanup loop could not start, often because the session store does not support listing all active sessions.

**Fix:** This is non-fatal — sessions will still work, they just won't be automatically expired. Use a store that supports `list_all_active()` or implement it in a custom store.
