# Demo Spec — `ai-guardrails` (protect: guards + governance budgets, web UI)

**Date:** 2026-08-22
**Status:** Draft for review
**Showcases:** `lexigram-ai-guard` (input/output guard pipeline) + `lexigram-ai-governance` (model policy, cost budget, audit trail).
**Portfolio position:** Third AI demo — answers *"is it safe and cost-controlled in production?"*
**Structure rationale:** Flat house Pattern-2 package (`guard_gate` avoids namespace shadow). UI present ⇒ auth-web pattern verbatim: `ui/pages.py` co-located with `views/`+`static/`.

---

## 1. Scenario

One assistant request pipeline shown unprotected vs protected. Five acts:
(1) prompt-injection blocked outright, (2) PII redacted end-to-end
(`[REDACTED:EMAIL]` flows into the canned reply), (3) oversized input
blocked by the length guard, (4) restricted model switch denied by
governance policy, (5) budget exhausted mid-conversation — subsequent
requests denied with remaining budget reported. Ends with the queryable
audit trail rendered as a table.

## 2. Layout

```
demos/ai-guardrails/
├── conftest.py                        # sys.path shim (src/) + app/client fixtures
├── README.md
└── src/guard_gate/
    ├── __init__.py
    ├── main.py                        # python -m guard gate (see env below)
    ├── module.py                      # @module (see wiring)
    ├── di/provider.py                 # internal provider
    ├── controllers/
    │   ├── __init__.py
    │   └── api.py                     # JSON logic only
    └── ui/                            # auth-web pattern: assets beside static routes
        ├── __init__.py                # docstring only
        ├── pages.py                   # single static-serving controller
        ├── views/
        │   └── playground.html            # policy toggle · model picker · ask box · audit table
        └── static/
            ├── app.js
            └── style.css
tests/
├── __init__.py
├── test_assistant_service.py          # all five acts + bypass path
├── test_policy.py                     # toggle semantics
├── test_pages.py
└── test_api.py                        # e2e over HTTP incl. audit endpoint
```

## 3. Module wiring

```python
@module()
class GuardrailsModule(Module):
    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        return DynamicModule(
            module=cls,
            imports=[
                GuardModule.configure(GuardConfig(
                    injection_detection=True, injection_action="block",
                    pii_detection=True, pii_action="redact",
                    pii_redaction_output=True,
                    max_input_chars=500, length_action="block",
                )),
                GovernanceModule.configure(GovernanceConfig(
                    monthly_budget=0.50,
                    restricted_models=["gpt-5-restricted"],  # act 4's denial
                )),
                WebModule.configure(
                    controllers=[GuardApiController, PlaygroundPageController],
                    web_config=_web_config(port),
                ),
            ],
            providers=[GuardrailsProvider],
            exports=[GuardedAssistant, PolicyToggle],
        )
```

**Guards are configured, not hand-registered:** verified —
`GuardProvider._build_pipeline()` (di/provider.py:185+) constructs the
heuristic pipeline purely from `GuardConfig` fields. `enable_llm_guards`
stays `False`. `GovernanceConfig.enforce_budget` defaults `True`.

`GuardrailsProvider.boot()` resolves `GuardPipelineProtocol`,
`AIGovernanceProtocol`, and `AIAuditStore` (auto-bound as
`InMemoryAuditStore` by `GovernanceProvider.register()`, provider.py:96-99),
assembles `GuardedAssistant(scripted replies keyed by intent; fixed
COST_PER_TURN constant)`.

Port default 8084 via `GUARD_GATE_PORT`.

## 4. Request flow (`GuardedAssistant.handle(user_id, text, model)`)

1. If `PolicyToggle.off` ⇒ raw canned reply, no gate/guards/cost.
2. `await governance.check_request(model, provider, user_id)` → **returns
   `bool`** (manager.py:138-166 — the manager diverges from contracts'
   `GovernanceDecision`); `False` ⇒ denial (act 4). Reason string built
   from the resolved `GovernanceConfig.restricted_models` membership.
3. `await governance.check_budget(COST_PER_TURN, user_id)` → **`bool`**
   (manager.py:258) — `False` ⇒ budget denial (act 5).
4. `pipeline.check_input(text)` → blocked ⇒ denial-with-reason from
   `.blocking_result.details` (acts 1, 3); redacted ⇒ continue with
   `.final_content`.
5. Canned reply from the (possibly redacted) text →
   `pipeline.check_output(reply)` redaction pass.
6. `track_cost(COST_PER_TURN, model, user_id)`; service keeps a spend
   ledger so `remaining_budget = monthly_budget − spent` is computed
   locally for `/api/state` and act 5 messaging.

**Semantics surfaced:** guard denial-as-data — blocks arrive as
`Ok(AggregateGuardResult(passed=False, action=BLOCK))`, never exceptions;
severity merge BLOCK > REDACT > WARN > PASS. Governance gates are bools;
audit events (`model_denied` with status="denied", budget events) are
emitted inside the manager. Budget exhaustion is arithmetic — no runtime
mutation API.

| Component | Implementation |
|---|---|
| `acts.py` | `ACTS: dict[str, Act(key, label, text, model)]` registry for the five scripted requests |
| `policy.py` | `PolicyToggle` singleton with `enabled: bool` — container-managed knob (FaultController idiom) |
| `api.py` | `POST /api/ask {text, model}` → `{outcome: pass|blocked|redacted|denied, reply?, reason?, remaining_budget?}`; `POST /api/policy {enabled}`; `GET /api/state` → toggle/budget/spent; `GET /api/audit` → event rows |

## 5. Tests

- `test_assistant_service.py` — each act's outcome value; REDACT chaining
  contains `[REDACTED:EMAIL]`; exhaustion boundary exactness; bypass path
  skips gate+guards+cost.
- `test_policy.py` — toggle flips behavior both ways; default on.
- `test_pages.py` — `/` markers (toggle, model select ids, audit table);
  static content types.
- `test_api.py` — acts e2e byte-stable; state endpoint math across turns;
  audit rows include MODEL_DENIED/BUDGET_EXCEEDED after the acts.

## 6. Integration

Makefile:114-115 append entries; demos/README.md section (:8084).

## 7. Acceptance criteria

- [ ] Server boots offline at :8084; playground usable.
- [ ] Five acts replay byte-stable via API.
- [ ] `make check-demos` green; ruff/format clean; files <500 LOC;
      changes confined to `demos/**` + `Makefile`.
- [ ] Own commit(s) including tests.

## 8. Gotchas

- Package `guard_gate`, never `guard` (namespace shadow).
- `GuardDeniedError` belongs to the security subsystem — do not import it;
  AI-guard denies as data.
- Config actions are strings ("block"/"redact"); result actions are enum
  values (`GuardAction.BLOCK`) — compare against the enum.
- `check_request` gates on `(model, provider)` — thread model per request
  so act 4 is reachable. The manager's methods return **bool** (async),
  diverging from contracts' `GovernanceDecision` shape — pin against
  manager.py:138/258 at implementation; do not code against the protocol
  docstring.
- Audit store resolves only after governance boots; controller receives it
  constructor-injected like other deps. Remaining budget is computed from
  our spend ledger — the manager exposes no getter.
