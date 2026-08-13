# Architecture

Internal design of the `lexigram-ai` package — the AI orchestrator for the Lexigram Framework.

---

## Role in the System

`lexigram-ai` is an **optional orchestrator** that discovers and coordinates AI sub-packages via Python entry points. It does not implement LLM clients, RAG pipelines, or agent strategies — it registers, wires, and monitors them.

```mermaid
flowchart LR
    subgraph User[Application Code]
        C["@module(imports=[AIModule.configure(...)])"]
    end

    subgraph AI[lexigram-ai Orchestrator]
        AM[AIModule]
        AP[AIProvider]
    end

    subgraph Subsystems[Discovered via entry points]
        LLM[lexigram-ai-llm]
        RAG[lexigram-ai-rag]
        AGENTS[lexigram-ai-agents]
        MEM[lexigram-ai-memory]
        SKILL[lexigram-ai-skills]
        SESSION[lexigram-ai-session]
        FEEDBACK[lexigram-ai-feedback]
        WORKERS[lexigram-ai-workers]
        MCP[lexigram-ai-mcp]
        OBSERV[lexigram-ai-observability]
    end

    subgraph Optional[Optional deps]
        VECTOR[lexigram-vector]
    end

    User -->|AIModule.configure| AM
    AM -->|exports AIProviderProtocol| AP
    AP -->|register / boot / shutdown| LLM
    AP -->|register / boot / shutdown| RAG
    AP -->|register / boot / shutdown| AGENTS
    AP -.->|entry-point scan| MEM
    AP -.->|entry-point scan| SKILL
    AP -.->|entry-point scan| SESSION
    AP -.->|entry-point scan| FEEDBACK
    AP -.->|entry-point scan| WORKERS
    AP -.->|entry-point scan| MCP
    AP -.->|entry-point scan| OBSERV
    RAG -.-> VECTOR
```

**Key constraint:** Sub-packages import **only** from `lexigram` and `lexigram-contracts`. They never import from `lexigram-ai` or from each other. Cross-package communication goes through contracts resolved via the DI container.

---

## Subsystem Discovery

`lexigram-ai` discovers sub-packages through two entry-point groups:

| Entry Point Group | Purpose | Loaded By |
|---|---|---|
| `lexigram.ai.subsystems` | Runtime discovery at `AIProvider.register()` | `AIProvider.register()` |
| `lexigram.ai.modules` | Test-time only — `AIModule.stub()` | `AIModule.stub()` |

### Discovery Flow

```mermaid
flowchart TD
    subgraph Registration[AIProvider.register]
        EP[Scan lexigram.ai.subsystems groups] --> FILTER{name in}
        FILTER -->|llm / vector / rag| EXPLICIT["Wire with config injection"]
        FILTER -->|other| DYNAMIC["Load & call .register(container)"]
        EXPLICIT --> LLM["LLMProvider.register(container)"]
        EXPLICIT --> VEC["VectorProvider.register(container)"]
        EXPLICIT --> RAG["RAGProvider.register(container)"]
    end

    subgraph EP_Contract[Sub-package declares]
        TOML[pyproject.toml] -->|entry-points.lexigram.ai.subsystems| EP
    end

    TOML -->|example| EG[
        "[project.entry-points.&quot;lexigram.ai.subsystems&quot;]"
        "agents = &quot;lexigram.ai.agents.di.provider:AgentsProvider&quot;"
    ]
```

The three core subsystems (LLM, Vector, RAG) are handled explicitly with config injection (`provider.py:210-231`). All others enter a dynamic loop (`provider.py:254-274`) that loads the provider class and calls `register()`, passing config from a lookup dict keyed by entry-point name.

---

## Architecture Overview

### Module Layer

`AIModule` is the public entry point — a `@module()`-decorated class whose `configure()` returns a `DynamicModule` registering `AIProvider` and exporting `AIProviderProtocol`. Consumers pass the result to their own `@module(imports=[...])`.

### Internal Architecture

```mermaid
flowchart BT
    subgraph Public[Public API]
        INIT["__init__.py<br/>Lazy re-exports"]
        MOD["module.py<br/>AIModule"]
    end

    subgraph DI[DI Layer]
        PROVIDER["di/provider.py<br/>AIProvider"]
        FACTORIES["di/factories.py<br/>Factories"]
    end

    subgraph Config[Configuration]
        CONFIG["config.py<br/>AIConfig"]
        CONST["constants.py<br/>Defaults"]
    end

    subgraph Shared[Shared]
        TYPES["types.py"]
        PROTO["protocols.py"]
        EXC["exceptions.py"]
        EVT["events.py"]
        HOOKS["hooks.py"]
        DECO["decorators.py"]
    end

    subgraph Owned[Aggregated Services]
        OBSERV[observability/<br/>Metrics · Tracing · Health]
        GOVERNANCE[governance/<br/>Audit · Policy]
        FEEDBACK[feedback/<br/>Processor registry]
    end

    subgraph CLI[CLI]
        CLI_DIR["cli/<br/>commands · checks · doctor · shell"]
    end

    MOD --> PROVIDER
    CONFIG --> PROVIDER
    CONST --> CONFIG
    PROVIDER --> OBSERV
    PROVIDER --> GOVERNANCE
    PROVIDER --> FEEDBACK
    PROVIDER --> CLI_DIR
```

### Source mapping

| Path | Purpose |
|---|---|
| `lexigram/ai/__init__.py` | Lazy re-exports (`AIConfig`, `AIModule`, `AIProvider`) |
| `lexigram/ai/module.py` | `AIModule` — `@module()` entry point |
| `lexigram/ai/di/provider.py` | `AIProvider` orchestrator |
| `lexigram/ai/di/factories.py` | Reserved factory functions |
| `lexigram/ai/config.py` | `AIConfig` with try/except optional imports |
| `lexigram/ai/constants.py` | `ENV_PREFIX`, default limits, version |
| `lexigram/ai/types.py` | `AIBaseEvent`, contracts re-exports |
| `lexigram/ai/exceptions.py` | `AIError` (package base, code `LEX_ERR_AI_005`) |
| `lexigram/ai/observability/` | Health, Metrics, Tracing, CallbackManager |
| `lexigram/ai/governance/` | Audit store, policy manager, persistence backends |
| `lexigram/ai/feedback/` | `FeedbackProcessorRegistry` |
| `lexigram/ai/cli/` | Commands, health checks, doctor, shell |

---

## Provider Lifecycle

`AIProvider` follows the standard Lexigram three-phase lifecycle:

```python
class AIProvider(Provider, AIProviderProtocol):
    name = "ai"
    priority = ProviderPriority.DOMAIN       # 50
    config_key: str | None = "ai"
    config_model: type | None = AIConfig
    optional_dependencies: tuple[str, ...] = ("db", "cache")
```

```mermaid
sequenceDiagram
    participant App as Application
    participant Container as DI Container
    participant AI as AIProvider
    participant Sub as Sub-Providers
    participant Resolved as Resolved Dependencies

    App->>AI: AIProvider(config=...)
    AI->>AI: __init__()
    App->>Container: freeze()

    Note over AI: ── register() ──
    Container->>AI: register(registrar)
    AI->>AI: Register AIConfig, monitoring, FeedbackProcessorRegistry
    alt governance enabled
        AI->>AI: Register AIAuditStore, AIGovernanceManager
    end
    AI->>Sub: LLMProvider.register()
    AI->>Sub: VectorProvider.register()
    AI->>Sub: RAGProvider.register()
    AI->>AI: Scan entry points → register each

    Note over AI: ── boot() ──
    Container->>AI: boot(resolver)
    AI->>Resolved: resolve(DatabaseProviderProtocol) — optional
    AI->>Resolved: resolve(CacheBackendProtocol) — optional
    alt cache available
        AI->>AI: Init RAGCache
    end

    Note over AI: ── shutdown() ──
    App->>AI: shutdown()
    AI->>Sub: shutdown() each sub-provider
    AI->>AI: Clear references
```

### Phase details

| Phase | Method | Receives | Actions |
|---|---|---|---|
| Registration | `register(container)` | `ContainerRegistrarProtocol` | Registers config, monitoring, governance singletons; delegates to sub-providers; discovers entry-point subsystems |
| Boot | `boot(container)` | `ContainerResolverProtocol` | Resolves optional `DatabaseProviderProtocol` and `CacheBackendProtocol`; inits `RAGCache` |
| Shutdown | `shutdown()` | — | Calls `shutdown()` on each sub-provider; clears references |

Sub-providers run their lifecycle during `AIProvider.register()` — they do **not** get independent lifecycle phases. `AIProvider.boot()` resolves cross-cutting dependencies; `AIProvider.shutdown()` iterates sub-providers for cleanup.

### Health check

`health_check()` aggregates sub-provider health into a `HealthCheckResult` with per-component latency, delegating to each sub-provider's own `health_check()` method.

---

## Config Model

`AIConfig` uses try/except imports so missing sub-packages degrade gracefully:

```mermaid
flowchart LR
    subgraph Fields[AIConfig Fields]
        LLM_F["llm: ClientConfig | None"]
        VEC_F["vector: VectorConfig | None"]
        RAG_F["rag: RAGConfig | None"]
        OBS_F["observability: ObservabilityConfig"]
        SUBS_F["subsystems: dict[str, dict]"]
    end

    LLM_F -->|try import| P1[lexigram-ai-llm]
    RAG_F -->|try import| P2[lexigram-ai-rag]
    VEC_F -->|try import| P3[lexigram-vector]
    OBS_F -->|try import| P4[lexigram-ai-observability]

    P1 -->|import fails| N1["ClientConfig = None"]
    P1 -->|import succeeds| Y1["Full config model"]
    N1 --> SENTINEL["_DisabledSubsystem()<br/>enabled = False"]
```

When a sub-package is not installed, its config field becomes `_DisabledSubsystem()` — a falsy sentinel returning `None` for all attribute access. The provider gates sub-provider delegation on `if intelligence_config.llm:`.

---

## Contracts Used

| Contract | Source | Bound By |
|---|---|---|
| `AIProviderProtocol` | `lexigram.contracts.ai` | `AIProvider` |
| `LLMClientProtocol` | `lexigram.contracts.ai.llm` | Delegated to `lexigram-ai-llm` |
| `VectorStoreProtocol` | `lexigram.contracts.data.vector` | Delegated to `lexigram-vector` |
| `RAGPipelineProtocol` | `lexigram.contracts.ai.rag` | Delegated to `lexigram-ai-rag` |
| `CacheBackendProtocol` | `lexigram.contracts.cache` | Resolved at `boot()` — optional |
| `DatabaseProviderProtocol` | `lexigram.contracts.data` | Resolved at `boot()` — optional |
| `CallbackManagerProtocol` | `lexigram.contracts.ai.callbacks` | `CallbackManagerImpl` |
| `AIHealthMonitorProtocol` | `lexigram.contracts.ai.observability` | `AIHealthMonitor` |
| `AIMetricsProtocol` | `lexigram.contracts.ai.observability` | `AIMetrics` |
| `AITracerProtocol` | `lexigram.contracts.ai.observability` | `AITracer` |
| `AgentExecutorProtocol` | `lexigram.contracts.agents` | Delegated to `lexigram-ai-agents` |
| `SessionManagerProtocol` | `lexigram.contracts.ai.session` | Delegated to `lexigram-ai-session` |
| `MemoryStoreProtocol` | `lexigram.contracts.ai.memory` | Delegated to `lexigram-ai-memory` |
| `SkillRegistryProtocol` | `lexigram.contracts.ai.skills` | Delegated to `lexigram-ai-skills` |
| `FeedbackProtocol` | `lexigram.contracts.ai.feedback` | Delegated to `lexigram-ai-feedback` |

---

## CLI Integration

`AICliContributor` registers with the `lexigram` CLI framework:

| Contribution | Description |
|---|---|
| `ai` command group | `lexigram ai ...` — subsystem management |
| `ai_llm_provider` health check | Verifies LLM provider reachable |
| `ai_subsystem_discovery` health check | Verifies entry-point discovery works |
| `ai_api_keys_configured` doctor check | Checks AI API keys are configured |
| `ai` shell context | Interactive AI client for REPL |

---

## Extension Points

| Point | Mechanism | Example |
|---|---|---|
| New AI subsystem | `lexigram.ai.subsystems` entry point | `agents = "lexigram.ai.agents.di.provider:AgentsProvider"` |
| New LLM provider | Register in `lexigram-ai-llm`'s `ProviderRegistry` | `ProviderRegistry.register("openai", OpenAIProvider)` |
| New RAG chunking strategy | `lexigram.chunking.strategies` entry point | `semantic = "..."` |
| New agent strategy | `lexigram.agent.strategies` entry point | `react = "..."` |
| Feedback processor | `FeedbackProcessorRegistry.register()` | `processor_registry.register("sentiment", ...)` |
| Governance backend | Implement persistence for `AIGovernanceManager` | `DatabaseGovernancePersistence` |
| Observability extension | Implement `AITracerProtocol` / `AIMetricsProtocol` | Custom tracing backend |

To add a new subsystem: create a provider with `register()`/`boot()`/`shutdown()`, declare the `lexigram.ai.subsystems` entry point in `pyproject.toml`, and configuration flows through `AIConfig.subsystems[name]`. If the subsystem exposes a protocol consumed by other packages, the protocol **must** live in `lexigram-contracts`.

---

## Constants

| Symbol | Value | Description |
|---|---|---|
| `ENV_PREFIX` | `LEX_AI__` | Env var prefix for AI config |
| `ENV_NESTED_DELIMITER` | `__` | Nested key delimiter for env vars |
| `DEFAULT_MAX_TOKENS` | `4096` | Default max tokens per completion |
| `DEFAULT_TEMPERATURE` | `0.7` | Default temperature |
| `DEFAULT_REQUEST_TIMEOUT_S` | `60` | Default request timeout |
| `DEFAULT_CONTEXT_WINDOW_MESSAGES` | `50` | Max messages in context |
| `__version__` | `0.1.1` | Package version |
