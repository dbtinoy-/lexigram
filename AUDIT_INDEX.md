# AUDIT_INDEX.md — Lexigram Framework Audit Index

> **Source**: Registered audit generators and derived report summaries.
> **Generated JSON**: `AUDIT_INDEX.json`
> **Status buckets**: `correct`, `incomplete`, `suspect` default to `0` when a report does not expose them.

---

## Summary

- Registered audits: 9
- Reports present: 8
- Total rows/findings: 335
- `correct`: 0
- `incomplete`: 0
- `suspect`: 0

## Tool Health

| Tool | Status | Source |
|------|--------|--------|
| `mypy` | PASS | `quality` |
| `pytest` | PASS | `tests` |
| `ruff` | FAIL | `quality` |

## Rules Health

- Critical violations: 9
- Important violations: 30
- Minor violations: 0
- Top misalignments:
  - `init-no-logic`: 29
  - `no-cross-extension-import`: 9
  - `import-absolute-only`: 1

## Package Coverage

- Discovered packages: 43
- Covered packages: 43
- Missing packages: 3
- Coverage status: PASS
- Missing package list:
  - `import-absolute-only`: Replace relative imports (for example `from .module import ...`) with absolute imports rooted at `lexigram...` so module ownership stays explicit.`
  - `init-no-logic`: Keep `__init__.py` export-only. Move functions/classes to dedicated modules and re-export symbols through `__all__` from `__init__.py`.`
  - `no-cross-extension-import`: Move shared contracts to `lexigram-contracts`, register implementations via providers, and resolve dependencies through the container instead of direct extension imports.`

## Registered Reports

| Audit | Report Path | Rows | correct | incomplete | suspect | Status |
|-------|-------------|-----:|--------:|-----------:|--------:|--------|
| `env_vars` | `AUDIT_ENV_VARS.md` | 0 | 0 | 0 | 0 | missing |
| `index` | `AUDIT_INDEX.md` | 0 | 0 | 0 | 0 | present |
| `integrations` | `AUDIT_INTEGRATIONS.md` | 21 | 0 | 0 | 0 | present |
| `overview` | `AUDIT_OVERVIEW.md` | 43 | 0 | 0 | 0 | present |
| `protocols` | `AUDIT_PROTOCOLS.md` | 134 | 0 | 0 | 0 | present |
| `quality` | `AUDIT_QUALITY.md` | 45 | 0 | 0 | 0 | present |
| `rules` | `AUDIT_RULES.md` | 45 | 0 | 0 | 0 | present |
| `security` | `AUDIT_SECURITY.md` | 3 | 0 | 0 | 0 | present |
| `tests` | `AUDIT_TESTS.md` | 44 | 0 | 0 | 0 | present |

