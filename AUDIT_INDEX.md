# AUDIT_INDEX.md — Lexigram Framework Audit Index

> **Source**: Registered audit generators and derived report summaries.
> **Generated JSON**: `AUDIT_INDEX.json`
> **Status buckets**: `correct`, `incomplete`, `suspect` default to `0` when a report does not expose them.

---

## Summary

- Registered audits: 13
- Reports present: 13
- Total rows/findings: 1936
- `correct`: 0
- `incomplete`: 0
- `suspect`: 0

## Tool Health

| Tool | Status | Source |
|------|--------|--------|
| `mypy` | FAIL | `quality` |
| `pytest` | PASS | `tests` |
| `ruff` | FAIL | `quality` |

## Rules Health

- Critical violations: 74
- Important violations: 36
- Minor violations: 0
- Top misalignments:
  - `no-cross-extension-import`: 74
  - `init-no-logic`: 35
  - `import-absolute-only`: 1

## Package Coverage

- Discovered packages: 54
- Covered packages: 54
- Missing packages: 0
- Coverage status: PASS
- Missing package list:
  - `(none)`

## Registered Reports

| Audit | Report Path | Rows | correct | incomplete | suspect | Status |
|-------|-------------|-----:|--------:|-----------:|--------:|--------|
| `docs-claims` | `AUDIT_DOC_CLAIMS.md` | 0 | 0 | 0 | 0 | present |
| `docs-imports` | `AUDIT_DOC_IMPORTS.md` | 0 | 0 | 0 | 0 | present |
| `docs-links` | `AUDIT_DOC_LINKS.md` | 0 | 0 | 0 | 0 | present |
| `env_vars` | `AUDIT_ENV_VARS.md` | 847 | 0 | 0 | 0 | present |
| `index` | `AUDIT_INDEX.md` | 0 | 0 | 0 | 0 | present |
| `integrations` | `AUDIT_INTEGRATIONS.md` | 23 | 0 | 0 | 0 | present |
| `optional-imports` | `AUDIT_OPTIONAL_IMPORTS.md` | 628 | 0 | 0 | 0 | present |
| `overview` | `AUDIT_OVERVIEW.md` | 54 | 0 | 0 | 0 | present |
| `protocols` | `AUDIT_PROTOCOLS.md` | 154 | 0 | 0 | 0 | present |
| `quality` | `AUDIT_QUALITY.md` | 56 | 0 | 0 | 0 | present |
| `rules` | `AUDIT_RULES.md` | 116 | 0 | 0 | 0 | present |
| `security` | `AUDIT_SECURITY.md` | 3 | 0 | 0 | 0 | present |
| `tests` | `AUDIT_TESTS.md` | 55 | 0 | 0 | 0 | present |

