# lexigram-ai-governance

AI governance for the Lexigram Framework — policy enforcement, audit trails, budget tracking

---

## Overview

AI usage governance for the Lexigram Framework. Enforces budget caps, rate limits, and model access policies on LLM requests — with a full audit trail, soft-limit callbacks, TPM/cost sliding windows, and hot-reloadable configuration. Zero-config usage starts with sensible defaults.

## Install

```bash
uv add lexigram-ai-governance
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module

from lexigram.ai.governance import GovernanceModule
from lexigram.ai.governance.config import GovernanceConfig

@module(imports=[
    GovernanceModule.configure(
        GovernanceConfig(
            monthly_budget=50.0,
            enforce_budget=True,
            soft_limit_pct=0.8,
            rpm_limit=60,
            restricted_models=["gpt-4o"],
        )
    )
])
class AppModule(Module):
    pass

app = Application(modules=[AppModule])
if __name__ == "__main__":
    app.run()
```

## Configuration

> **Zero-config usage:** Call `GovernanceModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
ai_governance:
  enabled: true
  monthly_budget: 100.0
  enforce_budget: true
  soft_limit_pct: 0.8
  rpm_limit: 60
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_AI_GOVERNANCE__MONTHLY_BUDGET=100.0
# Environment variables for each field
```

### Option 3 — Python

```python
from lexigram.ai.governance.config import GovernanceConfig
from lexigram.ai.governance import GovernanceModule

config = GovernanceConfig(
    monthly_budget=100.0,
    enforce_budget=True,
    soft_limit_pct=0.8,
    rpm_limit=60,
)
GovernanceModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `enabled` | `True` | `LEX_AI_GOVERNANCE__ENABLED` | Master on/off switch for governance enforcement |
| `monthly_budget` | `None` | `LEX_AI_GOVERNANCE__MONTHLY_BUDGET` | Monthly budget cap in dollars |
| `enforce_budget` | `True` | `LEX_AI_GOVERNANCE__ENFORCE_BUDGET` | Hard-block requests when budget is reached |
| `soft_limit_pct` | `None` | `LEX_AI_GOVERNANCE__SOFT_LIMIT_PCT` | Warn at this fraction of budget |
| `max_request_cost` | `None` | `LEX_AI_GOVERNANCE__MAX_REQUEST_COST` | Per-request cost cap in dollars |
| `rpm_limit` | `None` | `LEX_AI_GOVERNANCE__RPM_LIMIT` | Requests per minute cap |
| `tpm_limit` | `None` | `LEX_AI_GOVERNANCE__TPM_LIMIT` | Tokens per minute cap |
| `max_tokens_per_request` | `None` | `LEX_AI_GOVERNANCE__MAX_TOKENS_PER_REQUEST` | Hard token ceiling per request |
| `restricted_models` | `[]` | `LEX_AI_GOVERNANCE__RESTRICTED_MODELS` | Models blocked for all users |
| `model_allowlist` | `{}` | `LEX_AI_GOVERNANCE__MODEL_ALLOWLIST` | Per-user/role allowlist with glob patterns |
| `model_denylist` | `{}` | `LEX_AI_GOVERNANCE__MODEL_DENYLIST` | Per-user/role denylist |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `GovernanceModule.configure(config)` | Configure with explicit config |
| `GovernanceModule.stub(config)` | Minimal config for testing |

## Key Features

- **Budget enforcement**: Monthly budget caps with soft-limit callbacks
- **Rate limiting**: RPM and TPM sliding windows via `BudgetTracker`
- **Model access control**: Per-user and per-role allowlist/denylist with glob patterns
- **Audit trail**: Full governance decision recording via `AIAuditStore`
- **Hot reload**: Update limits at runtime without restarting
- **Persistence backends**: In-memory, Redis, and database backends

## Testing

```python
async with Application.boot(modules=[GovernanceModule.stub(
    GovernanceConfig(restricted_models=["gpt-4o"])
)]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/ai/governance/module.py` | `GovernanceModule.configure()`, `.stub()` |
| `src/lexigram/ai/governance/config.py` | `GovernanceConfig` |
| `src/lexigram/ai/governance/services/manager.py` | `AIGovernanceManager` core logic |
| `src/lexigram/ai/governance/budget/tracker.py` | `BudgetTracker` TPM / cost enforcement |
| `src/lexigram/ai/governance/audit/` | `AIAuditStore`, `AIAuditEvent`, query models |
| `src/lexigram/ai/governance/persistence/persistence.py` | Persistence backends |
| `src/lexigram/ai/governance/di/provider.py` | `GovernanceProvider` boot and registration |
