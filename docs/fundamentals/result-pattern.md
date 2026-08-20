---
title: "Result Pattern"
description: "Functional error handling using Result[T, E] for predictable application flow."
---

Lexigram discourages the use of exceptions for expected, recoverable business failures (e.g., "User Not Found" or "Validation Failed"). Instead, we use the **Result Pattern**, which forces explicit handling of failure states at the type level.

## 1. Ok and Err

The `Result` type is a union of two states: `Ok` (success) and `Err` (failure).

```python
from lexigram.result import Result, Ok, Err

def divide(a: int, b: int) -> Result[float, str]:
    if b == 0:
        return Err("Cannot divide by zero")
    return Ok(a / b)
```

### Result Type Origin

`Result`, `Ok`, and `Err` live in `lexigram.contracts.core.result` and are re-exported via:

```python
from lexigram.result import Result, Ok, Err  # Canonical import
from lexigram import Result, Ok, Err          # Also available from top-level
```

---

## 2. Handling Results

There are several ways to interact with a `Result` object.

### Checking State

```python
result = divide(10, 2)

if result.is_ok():
    value = result.unwrap()

if result.is_err():
    error = result.unwrap_err()
```

### Safe Accessors

```python
# Safe unwrap with default
value = result.unwrap_or(0.0)

# Unwrap with callback for error case
value = result.unwrap_or_else(lambda err: compute_fallback(err))
```

### Pattern Matching (Python 3.10+)

```python
result = await service.find_user("user-42")

match result:
    case Ok(user):
        print(f"Found: {user.name}")
    case Err(error):
        print(f"Error: {error}")
```

### Fluent Mapping

```python
from lexigram.result import pipeline

# Chain operations with ResultPipeline
name = (
    pipeline(user)
    .then(lambda u: validate_permissions(u, required_role))
    .map(lambda u: u.name)
    .finalize()
)
```

---

## 3. Functional Chaining

You can chain operations without explicit error checks at every step. If any step returns an `Err`, the entire chain stops and propagates that error.

### Map and Then

```python
from lexigram.result import Result, Ok, Err

async def fetch_user(user_id: str) -> Result[User, DomainError]: ...
async def check_permissions(user: User) -> Result[User, PermissionError]: ...

# Chain with and_then (async)
result = (
    await fetch_user("user-123")
    .and_then(check_permissions)
)

# Chain with map (sync transformation)
result = (
    await fetch_user("user-123")
    .map(lambda user: user.to_dict())
    .map_err(lambda e: str(e))
)
```

### Async Chaining

```python
# map — async transformation on Ok value
profile = await result.map(fetch_profile).and_then(enrich_profile)

# Filter — convert Ok to Err if predicate fails
valid = result.filter(lambda u: u.is_active, InactiveUserError())
```

---

## 4. Result Utilities

### Decorators

```python
from lexigram.result import as_result, as_result_sync

@as_result(IOError, TimeoutError)
async def fetch(url: str) -> bytes:
    return await client.get(url)

@as_result_sync(ValueError, KeyError)
def parse(data: str) -> int:
    return int(data)
```

### Collect and Partition

```python
from lexigram.result import collect, partition

results = [ok1, err1, ok2, err2]

# collect — short-circuits on first error
all_ok: Result[list[T], E] = collect(results)

# partition — splits into successes and failures
oks, errs = partition(results)
```

### Try/Catch

```python
from lexigram.result import try_catch, try_catch_sync

# Async
result = await try_catch((IOError, TimeoutError), fetch, url)

# Sync
result = try_catch_sync((ValueError, KeyError), parse, "42")
```

---

## 5. Error Types

### Domain Errors (Expected Failures)

```python
from lexigram.result import Result
from lexigram.contracts.exceptions.domain import DomainError, NotFoundError

async def find_user(self, user_id: str) -> Result[User, DomainError]:
    user = await self.repo.get(user_id)
    if not user:
        return Err(NotFoundError(f"User {user_id} not found"))
    return Ok(user)
```

### Infrastructure Errors (Propagate as Exceptions)

```python
# Database connection lost — let it propagate, don't wrap
try:
    await self.db.connect()
except DatabaseError as e:
    raise  # Infrastructure errors propagate, not wrapped in Result
```

| Use `Result[T, E]` | Use Exceptions |
|---------------------|----------------|
| User not found | Database connection lost |
| Validation failed | Serialization bug |
| Payment declined | Out of memory |
| Business rule violation | Missing API key |

---

## 6. Why not Exceptions?

- **Type Safety**: The return type clearly indicates that a function can fail.
- **Traceability**: Errors flow through the logic like data, rather than jumping "up" the stack.
- **Predictability**: You never have to guess which `try/except` block is needed.
- **Exhaustive Checking**: With pattern matching, the compiler can verify all cases are handled.
