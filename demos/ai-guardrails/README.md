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

## Layout

House flat structure with auth-web's co-located `ui/`. Package is named
`guard_gate` (never `guard` — namespace shadow).

## Run

```bash
PYTHONPATH=demos/ai-guardrails/src uv run python -m guard_gate
# → http://127.0.0.1:8084  (override: --port / GUARD_GATE_PORT)
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

