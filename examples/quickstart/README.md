# Lexigram Quickstart Examples

Getting started with Lexigram — working code examples that demonstrate core patterns.

## Prerequisites

These examples are part of the Lexigram monorepo. To run them:

```bash
cd /path/to/lexigram
uv sync  # Install all packages in dev mode
```

## Examples

### 01_simple_di.py — Dependency Injection Pattern

**What it shows:**
- Define a contract (Protocol)
- Implement the contract
- Register in a Provider (wrapped in @module)
- Inject via constructor
- Resolve and use

```bash
python examples/quickstart/01_simple_di.py
```

Output: `Hello, Alice!`

---

### 02_standard_module.py — Core Application Boot

**What it shows:**
- Boot StandardModule
- Resolve Invoker
- Invoke arbitrary functions with DI

```bash
python examples/quickstart/02_standard_module.py
```

---

### 03_result_pattern.py — Error Handling with Result[T, E]

**What it shows:**
- Define domain errors as exceptions
- Return Result[T, E] from operations
- Handle both success and error paths

```bash
python examples/quickstart/03_result_pattern.py
```

Output: 
```
✓ Hello, Alice!
✗ Error: User u99 not found
```

---

### 04_multiple_services.py — Service Composition

**What it shows:**
- Multiple services depending on each other
- Service-to-service injection
- Composable business logic

```bash
python examples/quickstart/04_multiple_services.py
```

---

### 05_module_composition.py — Composing Multiple Modules

**What it shows:**
- Build apps from independent modules
- Each module with its own provider
- Module dependencies and exports

```bash
python examples/quickstart/05_module_composition.py
```

---

### 06_structured_logging.py — Structured Logging Across Services

**What it shows:**
- Use lexigram.logging for structured logs
- Key-value logging (not f-strings)
- Logging across services

```bash
python examples/quickstart/06_structured_logging.py
```

---

## Adding More Examples

Follow the naming convention:
- `NN_description.py` where NN is the sequence number
- Examples should be complete, runnable scripts
- Add docstring explaining what it demonstrates
- Test before committing

## Links

- 📖 **README** — Back to project overview
- 🚀 **QUICKGUIDE** — Full architecture deep-dive
- 💻 **Code Examples** — See `/examples/` for more
