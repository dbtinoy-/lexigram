# Lexigram Framework — Consolidated Guidelines

> **Version**: 3.1 (Current) | **Scope**: Lexigram Framework (Python async platform)

This document is the **authoritative ruleset** for all development Every rule is mandatory unless explicitly
marked otherwise. When in doubt, follow the stricter interpretation.

---

## 1. Orientation

### 1.1 What This Repository Contains

A monorepo for the **Lexigram Framework** — a contract-based, async-first,
full-stack Python application platform built on DI, IoC, and the provider
pattern.

### 1.2 Package Hierarchy (Inviolable)

```
lexigram-contracts    Zero dependencies. Protocols, types, exceptions only.
    ↑   ↑
    ↑ lexigram           Depends ONLY on lexigram-contracts. Core framework.
    ↑   ↑
    lexigram-*         Extension packages. Depend on lexigram + lexigram-contracts.
```

**Dependency rules:**

- `lexigram-contracts` imports **nothing** from the ecosystem.
- `lexigram` imports **only** from `lexigram-contracts`.
- Extension packages import from `lexigram` and `lexigram-contracts` —
  normally **never from each other**.
- Cross-extension communication goes through **contracts, the container,
  providers, and IoC** — never direct imports.

**Documented Exceptions** (same-subsystem imports only):

- **`lexigram-admin`** may import directly from
  `lexigram-ui` (shared UI primitives).
- **`lexigram-admin`** may import from `lexigram-auth`, `lexigram-cache`,
  `lexigram-features`, and `lexigram-resilience` — these are fundamental to
  admin dashboard functionality and declared as explicit `pyproject.toml` deps.
- **`lexigram-ai`** (orchestrator) may import from **any** `lexigram-ai-*`
  subpackage and from `lexigram-vector` — all consumed packages must be
  declared as explicit `pyproject.toml` deps.
- **`lexigram-multimedia`** (orchestrator) may import from **any**
  `lexigram-multimedia-*` subpackage — all consumed packages must be declared
  as explicit `pyproject.toml` deps.
- **`lexigram-testing`** may import from any extension package — its purpose
  is cross-package test utilities; all used packages must be declared as optional
  deps in `lexigram-testing/pyproject.toml`.

**AI Subsystem Import Rules:**

The AI subsystem follows the **same IoC discipline** as the rest of the
framework. There are **no** free-for-all exceptions for AI packages.

```
lexigram-contracts     ← All protocols + shared value types
    ↑
lexigram               ← Core framework
    ↑
lexigram-ai-*          ← Implementation packages (agents, llm, rag, memory, etc.)
                          Depend ONLY on lexigram + lexigram-contracts
                          Do NOT import from each other
                          Do NOT import from lexigram-ai
    ↑ (entry points)
lexigram-ai            ← OPTIONAL orchestrator. Discovers sub-packages via
                          entry points. Never imported by sub-packages.
```

- All `lexigram-ai-*` packages depend **only** on `lexigram` and
  `lexigram-contracts`.
- `lexigram-ai-*` packages do **NOT** import from each other.
- `lexigram-ai-*` packages do **NOT** import from `lexigram-ai`.
- `lexigram-ai` discovers sub-packages via `lexigram.ai.subsystems`
  entry points.
- Shared value types (`ChatMessage`, `Role`, `Document`, `SearchResult`)
  live in `lexigram-contracts`.
- Cross-AI-package communication goes through protocols resolved via the
  container.

---

## 2. Contracts Boundary Rules

This section defines **what lives where** across the three layers:
`lexigram-contracts`, `lexigram`, and extension packages. These rules
eliminate the duplication and drift discovered during architectural review.

### 2.1 The Golden Rule

> **If two or more packages need to reference the same type, protocol,
> or exception, it lives in `lexigram-contracts`. No exceptions.**

A type that starts in an extension package and later gets imported by a
second extension package must be **moved to contracts** — never imported
cross-extension.

### 2.2 Protocol Placement

Protocols define service boundaries. Their placement determines the
entire dependency graph.

#### Decision Tree

```
Is this protocol consumed by more than one package?
  → YES → lexigram-contracts (always)

Is this protocol the contract for a service registered in the container?
  → YES → lexigram-contracts (container bindings must resolve against contracts)

Is this protocol part of a pluggable backend system (multiple implementations)?
  → YES → lexigram-contracts (backends are swappable across packages)

Is this protocol strictly internal to one package, never exposed outside,
and would not make semantic sense in contracts?
  → YES → Extension package (in a protocols.py file within the package)
  → UNSURE → lexigram-contracts (err on the side of contracts)
```

#### Where Protocols Live in `lexigram-contracts`

Protocols are organized by **domain**, not by AI-package name:

```
lexigram-contracts/src/lexigram/contracts/
├── ai/
│   ├── agents.py             # AgentProtocol, ToolProtocol, StrategyProtocol,
│   │                         # AgentExecutorProtocol, ToolRegistryProtocol
│   ├── llm.py                # LLMClientProtocol, EmbeddingClientProtocol,
│   │                         # ChatMessageProtocol, CompletionProtocol,
│   │                         # PromptTemplateProtocol, PromptRegistryProtocol,
│   │                         # TokenCounterProtocol, CostEstimatorProtocol,
│   │                         # StructuredExtractorProtocol
│   ├── memory.py             # MemoryStoreProtocol, WorkingMemoryProtocol,
│   │                         # EpisodicMemoryProtocol, SemanticMemoryProtocol,
│   │                         # MemoryConsolidatorProtocol
│   ├── skills.py             # SkillProtocol, SkillRegistryProtocol,
│   │                         # SkillExecutorProtocol
│   ├── session.py            # SessionManagerProtocol, SessionStoreProtocol
│   ├── governance/           # AIGovernanceProtocol, CostTrackingProtocol
│   │                         # (in governance/__init__.py)
│   ├── guards.py             # GuardPipelineProtocol, InputGuardProtocol,
│   │                         # OutputGuardProtocol
│   ├── feedback.py           # FeedbackProtocol, FeedbackStoreProtocol
│   ├── observability.py      # AITracerProtocol, AIMetricsProtocol
│   ├── rag.py                # RAGPipelineProtocol, SynthesizerProtocol,
│   │                         # DocumentLoaderProtocol, RetrievalStrategyProtocol
│   ├── routing.py            # LLMRouterProtocol, QuotaBackendProtocol,
│   │                         # InferenceLoggerProtocol
│   ├── providers.py          # ProviderRegistryProtocol, ModelSelectorProtocol
│   ├── vector.py             # RE-EXPORTS from data/vector/ only — no
│   │                         # duplicate definitions
│   └── models.py             # ModelRequest, ModelResponse
├── data/
│   ├── vector/protocols.py   # VectorStoreProtocol, VectorCollectionProtocol
│   │                         # (CANONICAL location — ai/vector.py re-exports)
│   ├── graph/protocols.py    # GraphStoreProtocol, GraphProtocol
│   └── ...
├── infra/
│   ├── cache/protocols.py    # CacheBackendProtocol
│   ├── resilience/protocols.py  # CircuitBreakerProtocol, RetryPolicyProtocol
│   └── ...
└── ...
```

#### Prohibited Protocol Patterns

| Pattern | Why It's Wrong |
|---|---|
| Same protocol defined in two files | Import collision; consumers pick the wrong one |
| Protocol in extension package consumed by another extension | Forces cross-extension import; move to contracts |
| Re-export wrapper that adds nothing | Indirection without value |
| Protocol with implementation code | Contracts are interfaces only |
| File named `protocols.py` in `lexigram-contracts` containing dataclasses | Separate types from protocols |

### 2.3 Shared Value Type Placement

Value types are data carriers — dataclasses, frozen dataclasses, enums,
and type aliases. Their placement follows stricter rules than protocols
because they appear in function signatures across the entire framework.

#### Rule: Shared Types Live in Contracts

Any value type that appears in a **protocol method signature** or is
**used by more than one package** must live in `lexigram-contracts`.

**Types that MUST be in contracts:**

| Type | Location in Contracts | Consumed By |
|---|---|---|
| `ChatMessage` | `ai/llm.py` | llm, agents, rag, memory, prompt |
| `Role` | `ai/llm.py` | llm, agents, rag, prompt |
| `Completion` | `ai/llm.py` | llm, agents, rag |
| `StreamChunk` | `ai/llm.py` | llm, rag |
| `ToolCall`, `FunctionCall` | `ai/llm.py` | llm, agents |
| `TokenUsage` | `ai/llm.py` | llm, agents, rag |
| `Document` | `ai/vector.py` | rag, vector, memory |
| `SearchResult` | `data/vector/types.py` | rag, vector (ONE definition) |
| `MemoryEntry` | `ai/memory.py` | memory, agents |
| `MemoryQuery` | `ai/memory.py` | memory, agents |
| `MemorySearchResult` | `ai/memory.py` | memory, agents |
| `AgentResponse` | `ai/agents.py` | agents, ai (ONE definition) |
| `SkillDefinition` | `ai/skills.py` | skills, agents |
| `SkillResult` | `ai/skills.py` | skills, agents |
| `ModelRequest` | `ai/models.py` | llm, rag, routing |
| `ModelResponse` | `ai/models.py` | llm, rag, routing |
| `ThinkingConfig` | `ai/thinking.py` | llm (all providers) |
| `GovernanceDecision` | `ai/governance/__init__.py` | governance, agents |
| `SessionState` | `ai/session.py` | session, agents |
| `HealthCheckResult` | `core/health.py` | every provider |
| `DomainEvent` | `domain/events.py` | events, all aggregates |

**Types that STAY in extension packages:**

| Type | Location | Reason |
|---|---|---|
| `ConversationStats` | `lexigram-ai-llm` | LLM conversation management only |
| `CacheEntry`, `CacheStats` | `lexigram-ai-llm` | LLM cache internals |
| `PlanStep` | `lexigram-ai-agents` | Plan-and-execute strategy internal |
| `Chunk` | `lexigram-ai-rag` | RAG chunking internal (contracts has `ChunkProtocol`) |
| `HypotheticalDocument` | `lexigram-ai-rag` | HyDE internal |
| `CompressionResult` | `lexigram-ai-rag` | Context compression internal |
| `PipelineContext` | `lexigram-ai-rag` | Pipeline execution internal |
| `PromptVariable` | `lexigram-ai-prompt` | Prompt template internal |
| `FeedbackItem` | `lexigram-ai-feedback` | Feedback collection internal |
| `StoredFact` | `lexigram-ai-memory` | Semantic memory internal |
| Package config classes | Each package | Package-specific configuration |

#### The Duplication Test

Before adding a type to an extension package, ask:

1. Does this type appear in any protocol signature in contracts? → **Contracts**
2. Will another `lexigram-ai-*` package need to reference this type? → **Contracts**
3. Is this type a return value from a service resolved via the container? → **Contracts**
4. Is this type purely internal to one package's implementation? → **Extension package**

If in doubt → **contracts**. Moving a type from contracts to a package
is a safe narrowing. Moving it the other direction is a breaking change
to every consumer.

### 2.4 Exception Placement

Exceptions follow a two-level hierarchy: **base domain exceptions** in
contracts, **specific leaf exceptions** in extension packages.

#### Hierarchy Structure

```
lexigram-contracts                    Extension Package
──────────────────                    ─────────────────
LexigramError                        (never redefined)
├── DomainError                      (never redefined)
├── InfrastructureError              (never redefined)
├── ContainerError                   (never redefined)
│
├── ai/exceptions.py:                lexigram-ai-llm/exceptions.py:
│   ├── AIError                      ├── LLMError(AIError)
│   │                                ├── LLMRateLimitError(LLMError)
│   │                                ├── LLMModelNotFoundError(LLMError)
│   │                                ├── LLMContentFilterError(LLMError)
│   │                                └── LLMAuthenticationError(LLMError)
│   │
│   │                                lexigram-ai-rag/exceptions.py:
│   │                                ├── RAGError(AIError)
│   │                                ├── PreprocessingError(RAGError)
│   │                                ├── RetrievalError(RAGError)
│   │                                └── SynthesisError(RAGError)
│   │
│   │                                lexigram-ai-memory/exceptions.py:
│   │                                ├── MemorySystemError(AIError)
│   │                                ├── MemoryStoreError(MemorySystemError)
│   │                                └── ConsolidationError(MemorySystemError)
│   │
├── ai/agents.py:                    lexigram-ai-agents/exceptions.py:
│   ├── AgentError                   ├── AgentConfigurationError(AgentError)
│   ├── ToolError                    ├── AgentExecutionError(AgentError)
│   └── StrategyError               ├── ToolNotFoundError(ToolError)
│                                    ├── ToolExecutionError(ToolError)
│                                    └── MaxIterationsExceededError(AgentError)
```

#### Rules

| Rule | Rationale |
|---|---|
| **Base domain exceptions** (`AIError`, `AgentError`, `ToolError`) live in contracts | Callers catch at the domain boundary without importing extensions |
| **Leaf exceptions** (`LLMRateLimitError`, `ToolNotFoundError`) live in extension packages | Specific to one implementation; callers who need them import the extension |
| **No exception defined in two places** | One definition, one import path — always |
| **No flat exception dump files** | Exceptions organized by domain, not in monolithic files |
| **Extension exceptions extend contracts base** | `LLMRateLimitError(LLMError)` where `LLMError` is from contracts |
| **Package base exception required** | Every extension defines `<Domain>Error(ContractsBase)` as its catch-all |

#### Where Exceptions Live in `lexigram-contracts`

```
lexigram-contracts/src/lexigram/contracts/
├── exceptions/
│   ├── base.py          # LexigramError (root)
│   ├── domain.py        # DomainError, NotFoundError, ValidationError, etc.
│   ├── infra.py         # InfrastructureError, DatabaseError, LockError, etc.
│   ├── container.py     # ContainerError, CircularDependencyError, etc.
│   ├── provider.py      # ProviderError, ModuleError, etc.
│   ├── resilience.py    # ResilienceError, CircuitBreakerError, etc.
│   ├── security.py      # SecurityError, GuardDeniedError, etc.
│   ├── events.py        # EventError, HandlerNotFoundError, etc.
│   └── execution.py     # PipelineExecutionError, PipelineStepError
├── ai/agents.py         # AgentError, ToolError, StrategyError
├── ai/exceptions.py     # AIError + sub-domain bases (LLMError, RAGError, ...)
├── mcp/exceptions.py    # MCPError, MCPTransportError, etc.
└── ...
```

**`ai/exceptions.py` contains ONLY `AIError` and its immediate domain
children (`LLMError` base, `RAGError` base, etc.) — never leaf
exceptions.** Leaf exceptions belong in their extension package.

### 2.5 Enum Placement

All enums that appear in protocol signatures or are used across packages
live in contracts. Package-internal enums stay in the extension.

#### Mandatory: Use `enum.Enum`

Every enumeration-like class **must** derive from `Enum`. The base
type depends on the semantic of the values:

- **String enums** — use `class X(str, Enum):` or `class X(StrEnum):`.
  Members compare equal to their string value, serialize naturally to JSON,
  and work in `isinstance(x, str)` checks. `StrEnum` is the convention used
  throughout `lexigram-contracts` (e.g. `Role`, `CircuitState`).
- **Ordering / priority / status-code enums** — use `class X(int, Enum):`
  (or `IntEnum`). Required when members must support numeric comparison
  (`<`, `>`, `+`) or be passed directly to APIs that expect `int`.

No bare classes with string or integer constants. This is enforced in
contracts and every extension package.

```python
# ✅ Correct — string domain enum
class Role(StrEnum):
    SYSTEM = 'system'
    USER = 'user'
    ASSISTANT = 'assistant'
    TOOL = 'tool'

# ✅ Correct — ordering enum that requires numeric comparison / arithmetic
class HookPriority(int, Enum):
    EARLY = 50
    NORMAL = 100
    LATE = 200
    # callers can write: HookPriority.EARLY + 10

# ❌ Wrong — bare class with string attributes
class Role:
    SYSTEM = 'system'
    USER = 'user'

# ❌ Wrong — plain Enum without str or int base
class Status(Enum):
    ACTIVE = 'active'
```

#### Enums in Contracts (Cross-Package)

| Enum | Location | Used By |
|---|---|---|
| `Role` | `ai/llm.py` | llm, agents, rag, memory, prompt |
| `ModelProvider` | `ai/types.py` | llm, routing |
| `ModelCapability` | `ai/providers.py` | llm, routing |
| `SessionStatus` | `ai/session.py` | session, agents |
| `AuditEventType` | `ai/governance/__init__.py` | governance, agents |
| `Environment` | `core/config.py` | every package |
| `ProviderPriority` | `core/provider.py` | every provider |
| `HealthStatus` | `core/health.py` | every provider |
| `CircuitState` | `infra/resilience/enums.py` | resilience, llm |
| `DistanceMetric` | `data/vector/enums.py` | vector, rag |
| `SQLDialect` | `data/sql/sql_dialect.py` | db, search |

#### Enums in Extension Packages (Internal)

| Enum | Location | Reason |
|---|---|---|
| `ChunkingStrategy` | `lexigram-ai-rag` | RAG chunking internals |
| `CompressionStrategy` | `lexigram-ai-rag` | RAG compression internals |
| `SynthesisStrategy` | `lexigram-ai-rag` | RAG synthesis internals |
| `ReasoningStrategy` | `lexigram-ai-rag` | RAG reasoning internals |
| `OptimizationStrategy` | `lexigram-ai-prompt` | Prompt optimization internals |
| `RenderFormat` | `lexigram-ai-prompt` | Prompt rendering internals |
| `FeedbackType` | `lexigram-ai-feedback` | Feedback collection internals |
| `PlanStepStatus` | `lexigram-ai-agents` | Plan-and-execute internals |

### 2.6 No-Duplication Rule

> **Every protocol, type, exception, and enum has exactly ONE definition
> in the entire monorepo.**

If a name exists in `lexigram-contracts`, no extension package may
redefine it. Extension packages import from contracts.

If a name exists in an extension package and a second package needs it,
it moves to contracts. The extension package then imports from contracts.

**Re-export aliases** (e.g., `ai/vector.py` re-exporting from
`data/vector/protocols.py`) are permitted **only** for ergonomic import
paths, and must be simple re-exports with no added logic or modified
signatures.

### 2.7 `ai/exceptions.py` Structure (Contracts)

This file contains **only base exception classes** — one per AI
subdomain. Leaf exceptions live in their extension packages.

```python
# lexigram-contracts/src/lexigram/contracts/ai/exceptions.py

from lexigram.contracts.exceptions.domain import DomainError


class AIError(DomainError):
    """Base exception for all AI-domain errors."""

# -- Sub-domain bases (extended by leaf exceptions in extension packages) --

class LLMError(AIError):
    """Base for LLM client errors. Extended in lexigram-ai-llm."""

class RAGError(AIError):
    """Base for RAG pipeline errors. Extended in lexigram-ai-rag."""

class MemoryError(AIError):
    """Base for memory system errors. Extended in lexigram-ai-memory."""

class SkillError(AIError):
    """Base for skill execution errors. Extended in lexigram-ai-skills."""

class GovernanceError(AIError):
    """Base for governance and policy errors."""

class GuardError(AIError):
    """Base for input/output guard errors."""

class SessionError(AIError):
    """Base for session management errors."""

class ExtractionError(AIError):
    """Base for structured extraction errors. Extended in lexigram-ai-llm."""
```

No other exception classes in this file. No leaf exceptions. No flat
dumps of 30+ exceptions.

### 2.8 Contracts File Organization Checklist

Before adding anything to `lexigram-contracts`, verify:

- [ ] Is it a protocol, shared type, base exception, or cross-package enum?
  If not, it doesn't belong in contracts.
- [ ] Does a definition with this name already exist anywhere in contracts?
  If yes, don't create a second one — extend or re-export the existing one.
- [ ] Is it organized by **domain** (agents, ai/llm, data/vector), not by
  package name (not `ai-llm/`, not `ai-rag/`)?
- [ ] Does the file separate protocols from types? Protocols in
  `protocols.py`, types in `types.py`, errors in `exceptions.py` (or
  `errors.py` for domain-specific leaves).
- [ ] Is the type frozen/immutable where appropriate? Value types that
  cross package boundaries should be `@dataclass(frozen=True)`.

---

## 3. Build, Lint & Test Commands

### 3.1 Package Management (UV)

```bash
uv sync                # Install all dependencies
uv add <package>       # Add a dependency
uv lock                # Regenerate lockfile
```

### 3.2 Linting & Formatting

```bash
uv run ruff check .              # Lint (report only)
uv run ruff check . --fix        # Lint + auto-fix
uv run ruff format .             # Format
uv run ruff format --check .     # Format check (CI mode, no writes)
```

### 3.3 Type Checking

```bash
uv run mypy core/lexigram/src/        # Type-check core
```

> Reminder: prevent common mypy failures by always declaring return types, typing function arguments and attributes, avoiding `Any` return values, keeping overrides type-compatible, fixing missing imports, and keeping methods reachable and correctly named. This helps avoid `attr-defined`, `no-untyped-def`, `no-any-return`, `arg-type`, `override`, `unreachable`, `name-defined`, `assignment`, `return-value`, `call-arg`, `type-arg`, `union-attr`, `str`, and `import-not-found` errors.

### 3.4 Testing

```bash
# Full suite
uv run pytest

# Scoped runs
uv run pytest lexigram-web/tests/                                        # One package
uv run pytest lexigram-web/tests/unit/test_controller.py -v              # One file
uv run pytest lexigram-web/tests/unit/test_controller.py::test_create -v # One test
uv run pytest -k "test_user"                                             # Pattern match

# Markers
uv run pytest -m "not integration"    # Exclude integration tests
uv run pytest -m integration          # Only integration tests

# Coverage
uv run pytest --cov --cov-report=html
uv run pytest --cov-fail-under=80
```

> **Development testing rule:** during development, run **narrow** tests
> scoped to your changed files/packages (see "Scoped runs" above) and
> **exclude integration tests** (`-m "not integration"`). Run the full
> framework suite only when really needed (e.g. pre-PR / `make ci`
> aggregate or a change with cross-package ripples).

> **Note:** `--cov-fail-under=80` above applies to the **aggregate**
> suite run from the repo root (`make test` / `make ci`). Individual
> packages set their own, often lower, floor in their own
> `pyproject.toml` `addopts` for scoped/local runs (e.g.
> `lexigram-ai-mcp` at 35%, most `lexigram-ai-*` packages at 60%,
> `lexigram-ai-agents` at 80%). A package below 80% locally is not a
> violation as long as the root aggregate run stays ≥80%.

### 3.5 Full CI Pipeline (Run Before Every PR)

```bash
uv run ruff check . \
  && uv run ruff format --check . \
  && uv run mypy core/lexigram/src/ \
  && uv run pytest --tb=short --cov-fail-under=80
```

### 3.6 Versioning

```bash
# Scheme: 0.<minor>.<patch><build>   e.g. 0.1.2001, 0.1.3002
#   minor = release branch
#   patch = semver patch (2, 3, ...)
#   build = monotonically increasing build number
#
# After publishing 0.Y.Z, next version is 0.Y.<Z+1>001.
# Example: 0.1.2 → 0.1.3001 → 0.1.3002

# Set version (pyproject.toml only — __init__.py reads it from metadata)
uvx yj set version "0.1.3001" < lexigram/pyproject.toml

# Build & publish
cd lexigram && uv build
uv publish dist/lexigram-*.whl dist/lexigram-*.tar.gz --token pypi-xxxx
```

---

## 4. Architectural Mandates

These are non-negotiable. Violating any of these is a blocking issue.

### 4.1 Always Use

| Mandate | Rationale |
|---------|-----------|
| **Contracts and protocols** for all service boundaries | Decoupling; swappable implementations |
| **Constructor injection** for all dependencies | Explicit dependency graph; testability |
| **Provider pattern** for all service registration | Centralized lifecycle; priority ordering |
| **IoC via the container** for all resolution | No hidden coupling; framework-managed lifecycle |
| **`Result[T, E]`** for expected, recoverable domain failures | Explicit error handling; type-level failure signals |
| **Exceptions** for unexpected infrastructure failures | Crash-level errors propagate; no silent swallowing |
| **Registry-based dispatch** instead of `if/elif` chains | Extensible; declarative; key classes stay prominent |
| **Absolute imports** everywhere | Unambiguous; refactor-safe |
| **`lexigram.contracts.domain`** for domain models | Not Pydantic directly — use the framework's domain layer |
| **Google-style docstrings** with accurate, detailed first line | Consistency; generated documentation quality |
| **`class X(str, Enum)`** for string enums; **`class X(int, Enum)`** for ordering/priority/status-code enums | Type safety; iteration; membership checking; correct numeric or string semantics |
| **Typed constructor parameters** on all services | No `Any` on injected dependencies; use protocols |

### 4.2 Result Pattern Rules

The `Result[T, E]` type from `lexigram.result` is
the **standard return type for domain operations that can fail in
expected, recoverable ways**.

```python
from lexigram.result import Result
from lexigram.result import Ok, Err

```

| Use `Result[T, E]` | Use Exceptions |
|---------------------|----------------|
| User not found, validation failed | Database connection lost |
| Payment declined, insufficient permissions | Serialization bug, null pointer |
| Business rule violation | Out of memory, disk full |
| Skill execution failed (expected) | Container resolution failed |
| LLM content filter triggered | Network timeout (infrastructure) |
| Memory capacity exceeded | Missing API key (configuration) |
| Any failure the **caller is expected to handle** | Any failure that should **propagate up the stack** |

**Mandatory patterns:**

```python
# ✅ Return Result for domain operations
async def find_user(self, user_id: str) -> Result[User, DomainError]:
    user = await self.repo.get(user_id)
    if not user:
        return Err(UserNotFound(user_id))
    return Ok(user)

# ✅ Handle both cases explicitly
result = await service.find_user("123")
if result.is_ok():
    user = result.unwrap()
else:
    error = result.unwrap_err()

# ✅ Use safe accessors
user = result.unwrap_or(default_user)
message = result.match(
    ok=lambda u: f"Found {u.name}",
    err=lambda e: f"Error: {e}",
)

# ✅ Chain with map_sync / and_then_sync for sync composition
email = result.map_sync(lambda u: u.email)
profile = result.and_then_sync(load_profile)

# ✅ Async chaining for I/O-dependent transforms
enriched = await result.map(enrich_from_api)
profile = await result.and_then(load_from_db)
```

**Prohibited patterns:**

```python
# ❌ Never unwrap() without checking
user = result.unwrap()  # Raises on Err — you reinvented exceptions

# ❌ Never catch infrastructure exceptions just to wrap in Result
try:
    data = await db.query(sql)
except DatabaseError as e:
    return Err(e)  # Let infrastructure errors propagate

# ❌ Never use Result for infallible operations
def add(a: int, b: int) -> Result[int, Never]:
    return Ok(a + b)  # Pointless overhead

# ❌ Never return Result from __init__ or lifecycle hooks
async def boot(self, container) -> Result[None, Error]:  # Wrong — raise

# ❌ Never use Any as the error type
async def execute(self) -> Result[SkillResult, Any]:  # Defeats purpose
    ...  # Use the specific error: Result[SkillResult, SkillError]
```

### 4.3 Never Use

| Anti-Pattern | Why |
|--------------|-----|
| **Service Locator** (passing the container into services) | Hides real dependencies; untestable |
| **Direct cross-extension imports** (`lexigram-web` → `lexigram-sql`) | Violates dependency architecture; creates lateral coupling |
| **Shims, aliases, re-export wrappers** | Indirection without value; maintenance burden |
| **Backward-compatibility layers or deprecation shims** | Clean breaks only; no dead code |
| **Ad-hoc code to satisfy tests** | Tests validate the design — fix the design, not tests |
| **Singletons (module-level or class-level)** | Use container-managed `singleton` registrations |
| **Manual instantiation** of services | Always resolve through the container |
| **`try/except` around framework imports** | `lexigram` and `lexigram-contracts` are always available |
| **Relative imports** | Use absolute imports exclusively |
| **Duplicate or redundant code** | Extract, don't copy |
| **Blind `result.unwrap()`** without `is_ok()` check | Defeats the purpose of Result |
| **`if/elif` chains for type dispatch** | Use `Registry` with declarative registration |
| **`Any` on injected constructor parameters** | Use the protocol type from contracts |
| **Bare classes masquerading as enums** | Use `class X(str, Enum):` |
| **Protocol definitions in extension packages that are consumed elsewhere** | Move to contracts |
| **Same type/protocol/exception defined in two places** | One definition per name in the entire monorepo |
| **Module-level `_handle_error` legacy methods** | Clean breaks; remove dead code |
| **`_assert_protocol()` scattered across modules** | Runtime checks belong at registration boundary only |
| **Self-registering defaults in `__init__`** | Use `with_defaults()` classmethod or provider registration |
| **Business logic on Provider classes** | Providers register and boot — domain logic goes on services |
| **Mock/test classes in production `src/` trees** | Test doubles belong in `tests/` or `lexigram-testing` |

### 4.4 Database Provider Rules

All database access in extension packages must use
`DatabaseProviderProtocol` from `lexigram-contracts`.

| Rule | Implementation |
|------|----------------|
| **Use protocol, not driver** | Import `DatabaseProviderProtocol` from contracts |
| **Constructor injection** | Accept `provider: DatabaseProviderProtocol` |
| **No direct pool creation** | Never call `asyncpg.create_pool()` directly |
| **Use scoped context** | `async with provider.scoped_context():` |
| **Cross-package is violation** | Never import from `lexigram.sql` |

**Exceptions** — Direct database access acceptable for:
- CLI administrative tools (`lexigram-admin/tools/*.py`)
- Monitoring/health check utilities

### 4.5 `__init__.py` Policy

`__init__.py` files contain **only exports** (`__all__`, re-exports from
submodules). If an `__init__.py` contains logic, classes, or functions,
extract them into a dedicated module and re-export.

**Specifically prohibited in `__init__.py`:**
- Function definitions (including "convenience" functions)
- Class definitions
- Business logic of any kind
- Conditional imports with `try/except`

---

## 5. Code Style

### 5.1 Type Annotations (Python 3.11+)

All functions, methods, and class attributes must have type annotations.
Use modern syntax exclusively:

```python
# ✅ Correct
def process(items: list[str], counts: dict[str, int]) -> str | None: ...
async def find(self, id: str) -> Result[User, DomainError]: ...

# ❌ Wrong — legacy typing
def process(items: List[str], counts: Dict[str, int]) -> Optional[str]: ...
```

**No `Any` on service boundaries.** Every constructor parameter that
accepts an injected dependency must use its protocol type:

```python
# ✅ Correct
class SkillExecutor:
    def __init__(
        self,
        registry: SkillRegistryProtocol,
        cache: SkillResultCache | None = None,
        permission_checker: PermissionChecker | None = None,
    ): ...

# ❌ Wrong — hides dependencies behind Any
class SkillExecutor:
    def __init__(
        self,
        registry: Any,
        cache: Any | None = None,
        permission_checker: Any | None = None,
    ): ...
```

### 5.2 Async / Await

All I/O operations must be async. Never block the event loop.

**Store task references** (Ruff RUF006):

```python
# ✅ Correct
task = asyncio.create_task(self._execute_batch())
self._background_tasks.add(task)
task.add_done_callback(self._background_tasks.discard)

# ❌ Wrong — fire-and-forget
asyncio.create_task(self._execute_batch())
```

### 5.3 Exception Handling

**Never use blind `except`** (Ruff BLE001). Always specify exception
types. Always chain with `from`:

```python
# ✅ Correct
try:
    result = await container.resolve(MyService)
except ResolutionError as e:
    logger.error("resolution_failed", service="MyService", error=str(e))
    raise StartupError("Cannot resolve MyService") from e

# ❌ Wrong
try:
    result = await container.resolve(MyService)
except Exception:
    pass
```

### 5.4 Logging

Use structlog via the framework's logging module. Never `print()`.

```python
from lexigram.logging import get_logger

logger = get_logger(__name__)

# Structured key-value pairs — not f-strings
logger.info("user_created", user_id=user.id, email=user.email)
```

### 5.5 Imports

- **Absolute imports only** — no relative imports.
- **No unused imports** (Ruff F401).
- **Grouping order**: stdlib → third-party → `lexigram-contracts` →
  `lexigram` → local.
- Ruff handles sort order — do not manually reorder.
- Every file begins with `from __future__ import annotations`.
- Use `if TYPE_CHECKING:` for imports needed only by type annotations.

### 5.6 Dependency Injection

Services declare dependencies as typed constructor parameters:

```python
from lexigram.contracts.cache import CacheBackendProtocol
from lexigram.contracts.data.sql.database import DatabaseProviderProtocol

class UserService:
    @inject
    def __init__(
        self,
        db: DatabaseProviderProtocol,
        cache: CacheBackendProtocol | None = None,
    ):
        self.db = db
        self.cache = cache
```

**Never instantiate services directly.**

### Ambient Capabilities (Exception to DI Rule)

A few capabilities are **ambient** by design — they are process-level, not per-instance, and would require explicit injection in every function signature if using DI. These are exceptions to the DI-first rule:

| Capability | Import Path | Usage |
|------------|--------------|-------|
| **Clock** | `from lexigram.primitives import clock` | `clock.now()`, `clock.monotonic()`, `clock.use(FixedClock())` |
| **Identity** | `from lexigram.identity import ambient as identity` | `identity.new_uuid()`, `identity.generate_for("user")` |
| **Hashing** | `from lexigram.security.hashing import ambient as hashing` | `hashing.hash_hex(data)`, `hashing.verify_hex(data, digest)` |

**Design rationale:** These are truly ambient — every code path needs the same clock, the same identity generator, the same hasher. Forcing DI would add ~100+ constructor parameters and fixture changes across the codebase with no benefit.

**Test override:** All ambient capabilities support `use()` context manager for test override:
```python
from lexigram.testing.clock import FixedClock
from lexigram.primitives import clock

with clock.use(FixedClock("2026-01-01")):
    assert clock.now().year == 2026
```

For type-hinting test fakes, use the protocols from `lexigram-contracts`:
```python
from lexigram.contracts.core.clock import ClockProtocol
from lexigram.testing.clock import FixedClock  # implements ClockProtocol
```

**All other services use constructor injection.**

### 5.7 Naming Conventions

| Element       | Convention             | Example                    |
|---------------|------------------------|----------------------------|
| Files         | `snake_case.py`        | `user_service.py`          |
| Classes       | `PascalCase`           | `UserService`              |
| Functions     | `snake_case`           | `create_user`              |
| Variables     | `snake_case`           | `active_count`             |
| Constants     | `SCREAMING_SNAKE_CASE` | `MAX_RETRY_COUNT`          |
| Protocols     | `PascalCase`           | `CacheBackendProtocol`     |
| Providers     | `*Provider`            | `CacheProvider`            |
| Modules       | `*Module`              | `AuthModule`               |
| Enums (string)   | `PascalCase(str, Enum)` | `Role`, `CircuitState`           |
| Enums (ordering) | `PascalCase(int, Enum)` | `HookPriority`, `StatusCode`     |

### 5.8 Class Naming Decision Tree

```
Protocol (interface)?     → *Protocol suffix (or recognized role noun)
ABC with @abstractmethod? → Abstract* prefix
Template base class?      → *Base suffix
Single canonical impl?    → *Impl suffix
DI provider?              → *Provider suffix
IoC module?               → *Module suffix
Registry dispatch?        → *Registry suffix
```

See the Class Naming Standards document for the full decision tree
and anti-pattern table.

### 5.9 File Size

- **Target**: under 500 lines.
- **Hard limit**: 700 lines. If exceeded, decompose into a package - root files excluded.

### 5.10 Docstring Formatting — Google Style

All Python docstrings must follow **Google style**. Use fenced code blocks with language identifiers for syntax highlighting.

**Structure:** One-liner → blank line → extended description → Args → Returns → Raises → Example → Note.

```python
# ✅ Minimal
def find_user(user_id: str) -> User | None:
    """Find a user by ID."""

# ✅ Complete
async def execute_skill(
    self, skill_name: str, context: dict[str, Any], timeout: int = 30
) -> Result[SkillResult, SkillError]:
    """
    Execute a skill with runtime context.

    Args:
        skill_name: Name of the skill (must exist in registry).
        context: Runtime context dict.
        timeout: Max execution time in seconds. Defaults to 30.

    Returns:
        Ok(result) on success, Err(error) on failure.

    Raises:
        SkillNotFoundError: If skill not in registry.
        PermissionError: If caller lacks permission.

    Example:
        ```python
        result = await executor.execute_skill("summarize", {"text": "..."})
        if result.is_ok():
            print(result.unwrap().output)
        ```

    Note:
        Execution is cancelled on timeout. No partial results returned.
    """
```

**Args Rules:**
- Don't repeat type annotations (they're in the signature)
- Describe **what** the parameter is and **how** it's used
- For Optional params, state what happens if omitted

**Returns Rules:**
- For `Result[T, E]`, describe both Ok and Err cases
- For None/empty, state explicitly
- Keep short unless structure is complex

**Raises Rules:**
- List only exceptions raised directly (not from callees)
- Infrastructure errors only (connection, timeout, auth)
- Domain errors → use Result type instead

**Examples Rules (Mandatory for public APIs):**
- Always use fenced code blocks with `python` identifier
- Include imports if needed
- Show both success and error cases for Result-returning functions
- Keep concise and realistic

**Other Sections:**
- **Attributes** (for classes): List public attributes with descriptions
- **Note** (optional): Caveats, performance considerations
- **See Also** (optional): Cross-references to related functions/docs
- **Deprecated** (optional): `Deprecated: As of vX, use Y instead.`

**Common Patterns:**

| Pattern | Usage |
|---------|-------|
| No return | Omit Returns or write `Returns: None.` |
| Async | Include `async` in Example code; format unchanged |
| Private method | Still document; no Example required |
| No args | Omit Args section |
| Multiple errors | List separately in Raises |

**Don't repeat type hints:**
```python
# ❌ Wrong
async def fetch(self, id: str) -> list[Event]:
    """Fetch events.

    Args:
        id (str): Event ID.

    Returns:
        list[Event]: List of events.
    """

# ✅ Correct
async def fetch(self, id: str) -> list[Event]:
    """Fetch events.

    Args:
        id: Event ID.

    Returns:
        List of events, most recent first.
    """
```

---

## 6. Provider & Module Standards

### 6.1 Provider Lifecycle

```python
class CacheProvider(Provider):
    name = "cache"
    priority = ProviderPriority.INFRASTRUCTURE

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind contracts to implementations. No resolution here."""
        container.singleton(CacheBackend, RedisCacheBackend)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Run after freeze. Resolution is safe."""
        cache = await container.resolve(CacheBackend)
        await cache.connect()

    async def shutdown(self) -> None:
        """Tear down in reverse priority order."""
        await self._cache.disconnect()
```

**Rules:**
- `register()` receives `ContainerRegistrarProtocol` — **never**
  `ContainerResolverProtocol`.
- `boot()` receives `ContainerResolverProtocol` — **never**
  `ContainerRegistrarProtocol`.
- Providers contain **no business logic** — only registration, boot
  wiring, and shutdown cleanup.
- Provider files live at `<package>/di/provider.py`. or can be `<package>/di/bundle_provider.py` if more applicable.

### 6.2 Module Pattern

```python
@module()
class AgentsModule(Module):
    @classmethod
    def configure(cls, config: AgentConfig | None = None) -> DynamicModule:
        from lexigram.ai.agents.di.provider import AgentsProvider
        return DynamicModule(
            module=cls,
            providers=[AgentsProvider(config=config)],
            exports=[AgentExecutorProtocol, ToolRegistryProtocol],
        )
```

**Rules:**
- Must use `@module()` decorator and extend `Module`.
- Must have `configure()` classmethod returning `DynamicModule`.
- `exports` must list the contracts consumers can resolve — never empty
  unless intentionally private.
- Module file lives at `<package>/module.py`.
- `configure()` returns `DynamicModule` — **never** a bare `Provider`.

### 6.3 Registry Pattern

```python
class AgentStrategyRegistry:
    def __init__(self) -> None:
        # Empty — no self-registration
        self._strategies: dict[str, type] = {}

    @classmethod
    def with_defaults(cls) -> AgentStrategyRegistry:
        registry = cls()
        registry.register("react", ReActStrategy)
        registry.register("plan_execute", PlanAndExecuteStrategy)
        return registry

    def register(self, key: str, strategy_cls: type) -> None: ...
    def get(self, key: str) -> type | None: ...
```

**Rules:**
- `__init__` creates an **empty** registry. No `_register_defaults()`.
- `with_defaults()` classmethod for pre-populated instances.
- Provider calls `with_defaults()` during `register()` for DI-managed
  registries.

---

## 7. Testing Standards

### 7.1 File & Naming Conventions

| Element      | Pattern                |
|--------------|------------------------|
| Test files   | `test_*.py`            |
| Test classes | `Test*`                |
| Test methods | `test_*`               |

### 7.2 Async Tests

All async tests use `pytest.mark.asyncio` (or `asyncio_mode = "auto"`):

```python
class TestUserService:
    @pytest.fixture
    def mock_db(self) -> MagicMock:
        db = MagicMock()
        db.save = AsyncMock(return_value=True)
        return db

    @pytest.mark.asyncio
    async def test_create_user_persists(self, mock_db: MagicMock) -> None:
        service = UserService(db=mock_db)
        user = await service.create(email="test@example.com")
        assert user.id is not None
        mock_db.save.assert_awaited_once()
```

### 7.3 Testing Result-Returning Methods

```python
@pytest.mark.asyncio
async def test_find_user_returns_ok(self) -> None:
    result = await service.find_user("user-123")
    assert result.is_ok()
    assert result.unwrap().id == "user-123"

@pytest.mark.asyncio
async def test_find_user_returns_err(self) -> None:
    result = await service.find_user("nonexistent")
    assert result.is_err()
    assert isinstance(result.unwrap_err(), UserNotFound)
```

### 7.4 Test Integrity Rules

- **Tests validate the design.** No shims or ad-hoc code paths.
- **Fake at the contract boundary.** Mock the protocol, not internals.
- **No global state.** Each test is independent.
- **Mock clients in `tests/`**, never in `src/`.

---

## 8. Public Root files — exempt from the 700-line rule; these files should contain the actual contents and not re-exports

- `__init__.py` — streamlined and lazy exports
- `di/` — di submodules must be enriched and complete with di related files
- `config.py` (or a `config/` package) — place all config; no re-exports
- `constants.py` — place all constants
- `exceptions.py` — place all exceptions; no re-exports
- `module.py` — module must be enriched and complete
- `types.py` — place all types; no re-exports
- `decorators.py` (or `di/decorators.py`) — decorators, if any
- `protocols.py` (or `di/protocols.py`) — protocols that should be importable
  by the application consumer directly

---

## 9. Ruff Rules — Quick Reference

| Rule    | Description                              | Severity |
|---------|------------------------------------------|----------|
| BLE001  | No blind `except Exception`              | Error    |
| RUF006  | Store `asyncio.create_task()` references | Error    |
| T201    | No `print()` in production code          | Error    |
| F401    | No unused imports                        | Error    |

---

## 10. Utilize Package `__init__.py` in Imports

- Always utilize the module `__init__.py` in importing and not the actual file that houses the class to simplify the imports path.

---


## 11. Decision Checklist

Before writing or modifying code, verify:

- [ ] Does this import only from `lexigram` or `lexigram-contracts`
      (not cross-extension)?
- [ ] Are all dependencies declared as **typed** constructor parameters
      (no `Any` on injected services)?
- [ ] Is there a contract/protocol for every service boundary?
- [ ] Does the protocol live in `lexigram-contracts` (not the extension)?
- [ ] Is the registration happening in a provider?
- [ ] Does the provider's `register()` take `ContainerRegistrarProtocol`
      and `boot()` take `ContainerResolverProtocol`?
- [ ] Is dispatch registry-based (not `if/elif`)?
- [ ] Are all I/O paths async?
- [ ] Are all exceptions specific (not blind `except`)?
- [ ] Do domain operations return `Result[T, E]` with a **specific**
      error type (not `Any`)?
- [ ] Is `Result.unwrap()` only called after `is_ok()` check?
- [ ] Are infrastructure failures raised as exceptions (not wrapped
      in `Result`)?
- [ ] Is the file under 700 lines?
- [ ] Do all functions have complete type annotations?
- [ ] Are all enums using `class X(str, Enum):`?
- [ ] Does every type/protocol/exception have exactly **one** definition
      in the monorepo?
- [ ] Is this type in the right layer (contracts vs extension)?
- [ ] Is the solution not an Ad Hoc or not a rigid patch?
- [ ] Is the module `__init__.py` being used in imports?
- [ ] Does this pass `ruff check`, `ruff format --check`, and `mypy`?

## Note to always remember

- Make things work, make things right, and make them fast

---


## Development Guide

**Do not create Worktrees** Do not create worktrees during development unless ask.
**Do not create Branch** Do not create branch during development unless ask.
**No Co-authored in commit message** Strictly no Co-authored-by: Copilot <xxx+Copilot@users.noreply.github.com>

### Commit Message Convention (MANDATORY)

Every commit message must carry the emoji matching its task type, placed **before**
the conventional-commit prefix: `git commit -m "<emoji> <type>(<scope>): <summary>"`.

| Type       | Emoji | Meaning                          | Example                                          |
|------------|-------|----------------------------------|--------------------------------------------------|
| `feat`     | ✨    | New user-visible feature         | `✨ feat(monitor): capture unhandled exceptions` |
| `fix`      | 🐛    | Bug fix                          | `🐛 fix(auth): refresh token expiry race`        |
| `perf`     | ⚡    | Performance improvement          | `⚡ perf(cache): single-flight stampede guards`  |
| `refactor` | ♻️    | Code restructure, no behavior change | `♻️ refactor(scripts): delegate discovery`    |
| `test`     | ✅    | Tests added or updated           | `✅ test(sql): assert tier boundary violations`  |
| `docs`     | 📝    | Documentation only               | `📝 docs(monitor): Sentry fallback behavior`     |
| `style`    | 🎨    | Format/whitespace, no logic change | `🎨 style(web): normalize quotes`              |
| `chore`    | 🔧    | Maintenance/tooling              | `🔧 chore(git): allowlist tiered paths`          |
| `ci`       | 👷    | CI workflows and config          | `👷 ci: derive members from shared inventory`    |
| `build`    | 📦    | Build system / packaging         | `📦 build: publish lexigram 0.1.3008`            |
| `deps`     | ⬆️    | Dependency upgrade               | `⬆️ deps: uv sync to 0.8.14`                     |
| `security` | 🔒    | Security hardening fix           | `🔒 security(auth): pin JWT algorithm`           |
| `revert`   | ⏪    | Reverts a previous commit        | `⏪ revert: undo glob members experiment`        |
| `wip`      | 🚧    | Checkpoint / in-progress         | `🚧 wip(auth-lane): checkpoint 2026-08-20`       |

Rules:

- One emoji only; the type always matches the emoji. No bare `chore:` or `feat:` without
  the prefix emoji.
- `wip` is reserved for shared-tree checkpoint commits (Safe Sync below) and must be in
  the format `🚧 wip(<lane>): checkpoint <date>`.
- Scope (`<scope>`) is optional and names the affected package, e.g. `feat(monitor)`.
- The public-mirror `make publish-* m="<message>"` commands accept the same
  emoji-prefixed message; plain descriptions are still allowed there.

### History Discipline (MANDATORY)

Build a **longer, verifiable commit history** with tests alongside features.
`git_stats` shows `total_commits 1938` but `span_days 1` and `human_authors 1`,
which reads as a single burst rather than sustained engineering; buyers weight
history discipline highest.

1. **Ship features together with their tests, in small focused commits.** Each
   new feature or bugfix commit includes its test file in the same change —
   e.g. `lexigram-features/src` plus `lexigram-features/tests/unit/test_*.py`
   together — so every commit is independently verifiable.
2. **Push commits over multiple days/sessions** instead of one continuous
   window, keeping the conventional commit prefixes (already at a 0.98 rate per
   `git_stats`).
3. **Tag intermediate releases** (`v0.1.4`, `v0.1.5`) as milestones land instead
   of a single `v0.1.3` tag, to show cadence over time.

### Git Working-Tree Safety (MANDATORY)

This is a *shared* working tree used by concurrent agent sessions. Destructive
git commands from one session have previously wiped another session's
uncommitted edits (incident: 2026-08-16, stash `tmp-admin-conflict-restore`
orphaned by a `git stash` + `git checkout .` dance).

**Never** run these while ANY uncommitted change exists in the tree
(interrupt in-flight work first; if you must sync, see the Safe Sync below):

```
git checkout .            git checkout -- .        git reset --hard <ref>
git clean -f              git clean -fdx            git stash drop
```

Safe Sync (when you need a clean tree to pull/rebase):

1. `git add -A && git commit -m "🚧 wip(<lane>): checkpoint <date>"` — prefer a
   checkpoint commit over stashing; it is crash-proof and keeps the reflog.
2. Only if a commit is impossible (mid-edit secrets, huge diff):
   `git stash push -u -m "<lane>-<date>"` then IMMEDIATELY `git stash pop`
   in the same command chain — never leave an orphaned stash behind.
3. Sync: `git pull --ff-only` (never `--rebase` on a dirty tree).
4. If `git stash pop` conflicts: RESOLVE the conflicts in place. Never
   discard with `git checkout .` / `git reset --hard`; recover via
   `git checkout stash@{0} -- <path>` instead.
 5. `git status --short` before and after any sync; uncommitted work you did
    not recognize as yours belongs to another lane — do not touch it.

### Staging & Commit Isolation (MANDATORY)

The shared index is shared state too. Two incidents on 2026-08-21:

- A lane's `git commit` swept **another lane's pre-staged files** into its
  commit (2 unrelated admin files landed under a demos test message).
- A lane's uncommitted edits were **wiped from the working tree** by a
  concurrent lane running a forbidden command above.

Rules:

1. **Never leave changes pre-staged.** Stage and commit in one chain,
   immediately after your verification passes. The window between
   `git add` and `git commit` is where cross-lane contamination happens.
2. **Inspect the index before every commit:** `git status --short`. Staged
   entries (`M `/`A ` in the first column) you did not create belong to
   another lane — never include them, never unstage them either.
3. **Commit by pathspec**, not by bare `git commit`: 
   `git commit <your-paths> -m "<emoji> <type>(<scope>): <summary>"`.
   A pathspec commit takes exactly those paths from the working tree and
   leaves the rest of the index untouched. Untracked files must be
   `git add`ed first or the pathspec will not match them.
4. **Commit early, commit small.** Uncommitted work in this tree is
   vulnerable to other lanes' violations, not just your own mistakes. The
   moment a task's tests pass, commit it before starting the next task.
5. **If foreign files land in your just-created commit:** fix immediately —
   `git reset --soft HEAD~1`, `git restore --staged .`, re-`git add` the
   foreign files to restore their prior staged state, then re-commit only
   your paths per rule 3. Never amend over it, never discard their changes.



