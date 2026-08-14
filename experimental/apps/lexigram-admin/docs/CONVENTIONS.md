# Conventions

This document records the standing conventions for admin code. These are
specific to admin; for the framework-wide Lexigram rules see the root
`AGENTS.md` and `CLAUDE.md`.

## Result vs. Exception

**Rule:**
- **Field-level validation** returns `Result[Ok, FieldError]`. Examples:
  `IsValidAdminEmail`, `StrongPassword`, `IsValidUsername`. See
  `src/lexigram/admin/validation/rules.py`.
- **Domain operations on aggregates and services** raise typed exceptions
  inheriting from `DomainError`. Examples: `NotFoundError`,
  `PermissionDeniedError`, `ConflictError`, `DataError`. See
  `src/lexigram/admin/exceptions.py:29-73`.
- **Infrastructure failures** (database connection, cache, queue) raise
  exceptions from the source package (`lexigram-sql`, `lexigram-cache`).
  Admin catches these only at the controller boundary and translates to
  `ErrorResponse` via `htmx_error_response()`.

**Why hybrid?** UI is HTML-rendered and benefits from exceptions surfacing
through HTMX response middleware automatically. Field validation runs in
bulk (whole-form-at-once) and needs to aggregate multiple errors per request,
which is awkward with exceptions.

**Examples — correct:**
```python
# Field validation: Result
class IsValidAdminEmail(AbstractRule):
    def __call__(self, value: Any, field_name: str) -> Result[Any, FieldError]:
        if "@" not in value:
            return Err(FieldError(field=field_name, message="invalid email"))
        return Ok(value)


# Domain: typed exception
async def get_user(self, user_id: UserId) -> AdminUser:
    user = await self._repo.find(user_id)
    if user is None:
        raise NotFoundError(f"user not found: {user_id}")
    return user
```

**Examples — wrong:**
```python
# WRONG: don't return Result for domain ops
async def get_user(self, user_id: UserId) -> Result[AdminUser, DomainError]:
    ...

# WRONG: don't raise for field validation
class IsValidAdminEmail(AbstractRule):
    def __call__(self, value, field_name):
        if "@" not in value:
            raise ValueError("invalid email")
```

## Logging

Always `get_logger(__name__)` from `lexigram.logging`. Never `print()`,
never `logging.getLogger`. Errors include structured fields, not
formatted strings:

```python
log.error("admin.resource_resolution_failed", resource=cls.__name__, error=str(exc))
```

## Async

All I/O is async. Background tasks use `asyncio.create_task()` and the
task reference is stored (no fire-and-forget): see
`src/lexigram/admin/services/background_jobs.py:137-138`.

## Frozen dataclasses

Value objects that cross package boundaries (events, configs, payloads)
use `@dataclass(frozen=True, kw_only=True)`. Internal mutable state
(stores, registries) is regular `@dataclass`.

## Enums

All enums inherit `(str, Enum)` so they JSON-serialize and compare to
strings. No bare `IntEnum` for domain enums.

## Imports

- Absolute imports only — no `from .` or `from ..`.
- No `Optional[X]` / `List[X]` — use `X | None` / `list[X]`.
- UI symbols come from `from lexigram.ui import X` only. Never deep-path
  into `lexigram.ui.atoms.*`, `lexigram.ui.molecules.*`, etc. The
  phantom-import guard test enforces this.

## Result pattern unwrapping

When unwrapping a `Result`, always check `is_ok()` first:
```python
result = await service.validate(payload)
if result.is_ok():
    value = result.unwrap()
else:
    error = result.unwrap_err()
```

Never `result.unwrap()` without the check — it raises on `Err`.
