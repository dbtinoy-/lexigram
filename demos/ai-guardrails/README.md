# 🛡️ ai-guardrails — guards + budgets, five acts live

> One support-request pipeline, shown unprotected vs protected. The
> browser playground flips protection on/off, fires the five acts, and
> renders outcomes plus the governance audit trail.

## What it proves

- **Guards from config** — `GuardConfig` alone builds the pipeline
  (injection block, PII redact, length block, output redaction)
- **Denial-as-data** — blocks arrive as `Ok(AggregateGuardResult(passed=False))`
  values; REDACT chains `[REDACTED:EMAIL]` into the reply
- **Governance gates** — restricted models denied via
  `check_request`; budget exhausts after three paid turns
  (`check_budget` + `track_cost`, in-memory persistence)
- **Audit trail** — fire-and-forget events (`model_denied`,
  `budget_exceeded`) queryable from the resolved store
- **Live toggle** — policy off bypasses gate, guards, and cost tracking

## How results are derived (no LLM)

This demo uses **no language model**. The `_canned()` function in
`domain/guarded_assistant.py` echoes the (possibly redacted) input back in a
fixed format: `"(demo reply) You asked about: {snippet}"`. The demo proves
the guard pipeline, governance gates, and audit trail work — not LLM
quality. All outputs are deterministic and byte-stable across runs.

## Lexigram patterns used

| Pattern | Where | What to reuse |
|---|---|---|
| Composition root | `app.py` | Single wiring file for your app |
| Module.configure() | `app.py` | Declarative framework capabilities |
| Provider register/boot | `di/provider.py` | Two-phase service lifecycle |
| Registry dispatch | `repository/acts.py` | Replace if/elif with Registry |
| Result-typed controllers | `controllers/api.py` | Automatic error→ProblemDetail mapping |
| Protocol-based DI | `domain/guarded_assistant.py` | Swap implementations without code changes |
| Frozen dataclasses | `domain/`, `repository/` | Immutable value types |
| Container singleton | `domain/policy.py` | Live config shared across services |

## Layout — read it in this order

Start at the composition root and follow the wiring outward.
Each file has teaching comments explaining the Lexigram convention it follows.

| # | File | Lesson |
|---|------|--------|
| 1 | `src/guard_gate/app.py` | ⭐ Composition root: config → modules → providers |
| 2 | `src/guard_gate/main.py` | Lifecycle: `Application.start/stop`, graceful shutdown |
| 3 | `src/guard_gate/di/provider.py` | `register()` (bind) vs `boot()` (initialize); two-phase DI |
| 4 | `src/guard_gate/domain/policy.py` | Container singleton for live config shared across services |
| 5 | `src/guard_gate/domain/guarded_assistant.py` | Protocol-based DI: swap implementations without code changes |
| 6 | `src/guard_gate/repository/acts.py` | Registry dispatch replacing if/elif chains |
| 7 | `src/guard_gate/controllers/api.py` | Result-typing: automatic error→ProblemDetail mapping |
| 8 | `src/guard_gate/ui/` | Page controllers: serve HTML/assets only, no logic |

```
demos/ai-guardrails/
├── src/guard_gate/
│   ├── app.py                # composition root (start here)
│   ├── main.py               # entry point / lifecycle
│   ├── di/provider.py        # DI wiring + boot() assembly
│   ├── domain/
│   │   ├── guarded_assistant.py  # the guarded pipeline
│   │   └── policy.py            # live toggle
│   ├── controllers/api.py    # JSON API: ask/policy/state/audit
│   ├── repository/acts.py    # scripted demo acts
│   └── ui/                   # pages controller + views/ + static/
├── application.yaml          # web/guard/governance config
└── tests/                    # e2e flow via ASGITransport
```

## Run

```bash
cd demos/ai-guardrails
PYTHONPATH=src uv run python -m guard_gate
# → http://127.0.0.1:8084
```

| Act | Outcome |
|---|---|
| Injection | blocked (`instruction_override` reason) |
| PII | redacted end-to-end, still costed |
| Oversize | blocked by length guard |
| Restricted model | denied before guards |
| Drain budget | 3 paid turns ⇒ 4th denied with remaining $ |

## Tests

```bash
uv run pytest demos/ai-guardrails/tests -q
```

