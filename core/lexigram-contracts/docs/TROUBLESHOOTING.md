---
title: "lexigram-contracts Troubleshooting"
description: "Solutions to common issues with lexigram-contracts."
---
# Troubleshooting

---

## ImportError: cannot import name 'X' from 'lexigram.contracts'

**Error:**
```
ImportError: cannot import name 'MyType' from 'lexigram.contracts'
```

**Cause:** The name doesn't exist in `lexigram.contracts.__init__` or the lazy imports dict, or it's been moved to a different module.

**Solution:**
1. Check `lexigram/contracts/__init__.py` for the correct import path
2. Search the contracts source tree for the definition
3. If it's a type from an extension package, import from that package instead

```python
# ✅ Check the contracts __init__.py for lazy imports
from lexigram.contracts.core import ContainerRegistrarProtocol
from lexigram.contracts.infra.cache import CacheBackendProtocol
```

---

## Circular Import Error

**Error:**
```
ImportError: cannot import name 'X' from partially initialized module 'lexigram.contracts'
```

**Cause:** A type in contracts is trying to import from an extension package, violating the zero-dependency rule.

**Solution:** Ensure `lexigram-contracts` only imports from stdlib and its own submodules — never from `lexigram` or any extension:

```python
# ✅ Correct — stdlib only
from typing import Protocol
from dataclasses import dataclass

# ❌ Wrong — pulls in lexigram
from lexigram.result import Result
```

The `Result` type in contracts is defined in `lexigram.contracts.core.result` — independent of the `lexigram` package's re-export.

---

## Protocol Not Recognized by isinstance()

```python
isinstance(my_cache, CacheBackendProtocol)  # Returns False unexpectedly
```

**Cause:** The protocol class is missing the `@runtime_checkable` decorator, or the implementation doesn't structurally match the protocol signature.

**Solution:**
1. Ensure the protocol has `@runtime_checkable`:
   ```python
   from typing import Protocol, runtime_checkable

   @runtime_checkable
   class CacheBackendProtocol(Protocol):
       ...
   ```
2. Verify your implementation has all the required methods with matching signatures
3. Use `ProtocolValidator` (in `lexigram`) at registration time to catch mismatches

---

## Type Defined in Two Places

**Symptom:** Two different import paths for what should be the same type, leading to `isinstance()` failures and type errors.

**Cause:** A type was defined both in `lexigram-contracts` and in an extension package (violating the no-duplication rule).

**Solution:** Remove the extension package's copy and import from contracts:

```python
# ❌ Wrong — duplicate definition in extension package
class CacheBackendProtocol(Protocol):
    ...

# ✅ Correct — import from contracts
from lexigram.contracts.infra.cache import CacheBackendProtocol
```

---

## Wrong Domain Directory

**Symptom:** Protocol or type is hard to find, or import paths don't match the domain organization.

**Cause:** A type was placed in a directory named after the extension package (e.g. `ai-llm/`) instead of the domain (e.g. `ai/llm.py`).

**Solution:** Organize by domain, not by consumer:

```
# ✅ Correct — by domain
lexigram/contracts/ai/llm.py

# ❌ Wrong — by package
lexigram/contracts/ai-llm/
```

---

## Extension Exception Doesn't Extend Contracts Base

**Error:**
```python
# In extension package
class LLMRateLimitError(Exception):  # ❌ Should extend AIError or LLMError
    ...
```

**Cause:** Leaf exceptions in extension packages must extend the corresponding base exception from contracts.

**Solution:**
```python
# ✅ Correct
from lexigram.contracts.ai.exceptions import LLMError


class LLMRateLimitError(LLMError):
    """Raised when rate-limited by the LLM provider."""
```

This ensures callers can catch `AIError` and get all AI subsystem errors without importing extension packages.

---

## Debug Tips

1. **List all available exports:**
   ```python
   import lexigram.contracts
   print(dir(lexigram.contracts))
   ```

2. **Find where a protocol is defined:**
   ```python
   from lexigram.contracts.core.di import ContainerRegistrarProtocol
   print(ContainerRegistrarProtocol.__module__)
   ```

3. **Verify no cross-imports:**
   ```bash
   grep -rn "from lexigram\." core/lexigram-contracts/src/ --include="*.py" | grep -v "contracts" | grep -v "^Binary"
   ```
   Should return no results (contracts only imports from itself).

4. **Check for duplicate definitions:**
   ```bash
   grep -rn "class CacheBackendProtocol" framework/ --include="*.py"
   ```
   Should only appear in `lexigram-contracts`.
