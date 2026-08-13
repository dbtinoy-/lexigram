# Architecture

Internal design of the `lexigram-ai-governance` package.

---

## Role in the System

`lexigram-ai-governance` provides AI governance policies that gate which LLM requests are allowed, denied, or throttled based on budget, rate, model, content, and data-classification rules.

```mermaid
flowchart TB
    App[Application Layer<br/>AI Agent · Pipeline · Chat]
    Gov[Governance<br/>Policy Engine · BudgetTracker<br/>ContentPolicyService]
    LLM[LLM Provider<br/>OpenAI · Anthropic · etc.]
    Audit[Audit Store<br/>InMemory · Database]
    Persist[Persistence<br/>InMemory · Redis · Database]
    Events[Event Bus<br/>BudgetAlertEvent · PolicyEvaluatedEvent]

    App -->|check_request| Gov
    Gov -->|evaluate policies| Gov
    Gov -->|record / query| Persist
    Gov -->|emit| Events
    Gov -->|record| Audit
    App -->|if ALLOW| LLM
```

**Import direction:** Application code depends on `AIGovernanceProtocol` from `lexigram-contracts`. The governance package implements that contract. No other governance package imports from the application layer.

---

## Policy Model

Policies are declarative rules composed of scope-constrained conditions evaluated in priority order.

```mermaid
flowchart LR
    subgraph Store[PolicyStore]
        P1[Policy: cost-guard<br/>priority: 10]
        P2[Policy: model-blocklist<br/>priority: 20]
    end

    subgraph Engine[PolicyEngine]
        Eval[Evaluate enabled policies<br/>sorted by priority]
        Match{Match rule?}
        Deny[Return Err PolicyViolation]
        Allow[Return Ok PolicyDecision]
        Eval -->|next policy| Match
        Match -->|yes + effect=DENY| Deny
        Match -->|yes + effect=ALLOW| Allow
        Match -->|no rule matches| Allow
    end

    subgraph Types[Domain Types]
        Rule[PolicyRule<br/>scope · effect · condition · roles]
        Ctx[GovernanceContext<br/>model · role · cost · classification]
    end

    Ctx --> Engine
    Store --> Engine
    Deny --> Dec[PolicyDecision<br/>allowed · matched_policy · reason]
    Allow --> Dec
```

### Rule Scopes

| Scope | Condition Keys | Example |
|-------|---------------|---------|
| `MODEL` | `model_pattern` (glob) | `{"model_pattern": "gpt-4*"}` |
| `COST` | `max_cost` | `{"max_cost": 0.50}` |
| `GUARDRAIL` | `required` (list) | `{"required": ["pii_filter"]}` |
| `DATA_CLASSIFICATION` | `classification` | `{"classification": "pii"}` |

**Evaluation:** Load enabled policies sorted by priority. For each, iterate rules (skip if `roles` doesn't match). First DENY match short-circuits → `Err(PolicyViolation)`. No DENY → `Ok(PolicyDecision(allowed=True))`.

---

## Enforcement

Governance checks fire at two points before an LLM call: request-level (model access / rate limits) and budget-level (per-request cap + monthly spend). Content gating is a third layer via `ContentPolicyService` + `CompositeGate`.

```mermaid
sequenceDiagram
    participant Caller as AI Pipeline
    participant Gov as AIGovernanceManager
    participant Persist as GovernancePersistence
    participant Audit as AIAuditStore

    Caller->>Gov: check_request(model, provider, user_id)
    Gov->>Gov: restricted_models + allowlist/denylist
    alt Blocked by model policy
        Gov-->>Caller: False
    else Model allowed
        Gov->>Persist: incr_requests(key, 60s)
        Persist-->>Gov: RPM count
        alt RPM exceeded
            Gov-->>Caller: False
        else RPM OK
            Gov-->>Caller: True
        end
    end

    Caller->>Gov: check_request_budget(est_cost)
    Gov->>Gov: per-request cap?
    alt Over cap
        Gov-->>Caller: Err(GovernanceError)
    else Within cap
        Gov->>Persist: get_spend(month_key)
        Persist-->>Gov: monthly spend
        alt Budget exceeded
            Gov-->>Caller: Err(GovernanceError)
        else Within budget
            Gov-->>Caller: Ok(None)
        end
    end
    Gov-)Audit: record decision (async)
```

---

## Provider Lifecycle

```mermaid
sequenceDiagram
    participant Container as DI Container
    participant Prov as GovernanceProvider
    participant Config as GovernanceConfig
    participant Mgr as AIGovernanceManager

    Container->>Prov: register(container)
    Prov->>Container: singleton(GovernanceConfig, config)
    Prov->>Container: singleton(AIGovernanceManager)
    Prov-->>Container: done

    Container->>Prov: boot(container)
    Prov->>Prov: (no-op — in-process domain provider)
    Prov-->>Container: ready

    Container->>Mgr: resolve AIGovernanceManager
    Mgr->>Mgr: persist = InMemory | Redis | Database
    Mgr-->>Container: ready for calls

    Note over Container,Mgr: Runtime — check_request, check_budget, track_cost

    Container->>Prov: shutdown()
    Prov-->>Container: done
```

`GovernanceProvider` (priority `DOMAIN`) registers `GovernanceConfig` + `AIGovernanceManager` as singletons. The manager auto-selects persistence: explicit `persistence=` → use it; `cache=` (implements `CacheBackendProtocol`) → `RedisGovernancePersistence`; neither → `InMemoryGovernancePersistence`.

---

## Contracts Used

| Contract Symbol | Source | Role |
|----------------|--------|------|
| `AIGovernanceProtocol` | `lexigram.contracts.ai.governance` | Primary service contract for `check_request`, `check_budget`, `track_cost`, `reload_config` |
| `CostTrackingProtocol` | `lexigram.contracts.ai.governance` | Cost recording (`track_cost`) |
| `AIAuditStoreProtocol` | `lexigram.contracts.ai.governance` | Audit event persistence (`record`, `query`, `aggregate`) |
| `GovernanceError` | `lexigram.contracts.ai.governance` | Base domain exception |
| `BudgetExceededError` | `lexigram.contracts.ai.governance` | Monthly spend cap breached |
| `CacheBackendProtocol` | `lexigram.contracts.infra.cache` | Distributed counter/spend storage (optional) |
| `DatabaseProviderProtocol` | `lexigram.contracts.data` | SQL-backed persistence (optional) |
| `EventBusProtocol` | `lexigram.contracts.events` | Budget alert emission (optional) |
| `ContainerRegistrarProtocol` | `lexigram.contracts.core.di` | Provider registration |
| `ContainerResolverProtocol` | `lexigram.contracts.core.di` | Provider boot-time resolution |

---

## Extension Points

| Point | Mechanism | Example |
|-------|-----------|---------|
| Custom policy rule | `PolicyScope` enum + `PolicyRule` condition | Add a `JURISDICTION` scope |
| Custom policy store | Implement `PolicyStore`-like CRUD | Database-backed policy storage |
| Custom persistence | Implement `GovernancePersistence` protocol | S3-backed spend counters |
| Custom content gate | Implement `ContentPolicyGateProtocol` | Abuse detection gate |
| Custom audit store | Implement `AIAuditStore` protocol | Elasticsearch audit sink |
| Policy observer | Implement `PolicyObserverProtocol` | Metrics counter on every evaluation |
| Budget alert handler | Subscribe to `BudgetAlertEvent` via `EventBusProtocol` | PagerDuty at 90% spend |
| Hot-reload config | Call `AIGovernanceManager.reload_config()` | Runtime policy change without restart |
| Composite gate composition | Add gates to `CompositeGate(gates=[...])` | Abuse + quota + jurisdiction |
