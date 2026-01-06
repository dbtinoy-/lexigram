# AUDIT_INDEX.md — Lexigram Framework Audit Index

> **Source**: Registered audit generators and derived report summaries.
> **Generated JSON**: `AUDIT_INDEX.json`
> **Status buckets**: `correct`, `incomplete`, `suspect` default to `0` when a report does not expose them.

---

## Summary

- Registered audits: 9
- Reports present: 8
- Total rows/findings: 281
- `correct`: 0
- `incomplete`: 0
- `suspect`: 0

## Tool Health

| Tool | Status | Source |
|------|--------|--------|
| `mypy` | PASS | `quality` |
| `pytest` | PASS | `tests` |
| `ruff` | PASS | `quality` |

## Rules Health

- Critical violations: 0
- Important violations: 0
- Minor violations: 0
- Top misalignments:
  - `(none)`

## Package Coverage

- Discovered packages: 37
- Covered packages: 37
- Missing packages: 1
- Coverage status: PASS
- Missing package list:
  - `No resolutions needed. No rule findings detected.`

## Registered Reports

| Audit | Report Path | Rows | correct | incomplete | suspect | Status |
|-------|-------------|-----:|--------:|-----------:|--------:|--------|
| `env_vars` | `AUDIT_ENV_VARS.md` | 0 | 0 | 0 | 0 | missing |
| `index` | `AUDIT_INDEX.md` | 0 | 0 | 0 | 0 | present |
| `integrations` | `AUDIT_INTEGRATIONS.md` | 20 | 0 | 0 | 0 | present |
| `overview` | `AUDIT_OVERVIEW.md` | 37 | 0 | 0 | 0 | present |
| `protocols` | `AUDIT_PROTOCOLS.md` | 141 | 0 | 0 | 0 | present |
| `quality` | `AUDIT_QUALITY.md` | 39 | 0 | 0 | 0 | present |
| `rules` | `AUDIT_RULES.md` | 4 | 0 | 0 | 0 | present |
| `security` | `AUDIT_SECURITY.md` | 3 | 0 | 0 | 0 | present |
| `tests` | `AUDIT_TESTS.md` | 37 | 0 | 0 | 0 | present |

