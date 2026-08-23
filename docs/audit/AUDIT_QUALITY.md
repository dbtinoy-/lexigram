# AUDIT_QUALITY.md — Lexigram Framework Quality Snapshot

> **Source**: Live command evidence from repository quality tools, with package counts as supporting context.

---

## Summary

- Tool checks run: 2
- Passing tools: 1
- Failing tools: 1
- Packages counted: 54
- Total mypy errors: 106
- Packages with errors: 4

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **PASS** | 0 | 234 ms | `uv run ruff check .` |
| `Mypy` | **FAIL** | 1 | 49306 ms | `uv run mypy src/ (per-package across 54 packages)` |

### Ruff

- Status: **PASS**
- Exit code: `0`
- Duration: `234 ms`
- Command: `uv run ruff check .`
- Output snippet:

```text
All checks passed!
```

### Mypy

- Status: **FAIL**
- Exit code: `1`
- Duration: `49306 ms`
- Command: `uv run mypy src/ (per-package across 54 packages)`
- Output snippet:

```text
[lexigram] 35 errors
[lexigram-admin] 69 errors
[lexigram-ai] 1 errors
[lexigram-cli] 0 errors
[lexigram-testing] 1 errors
```

### Mypy Error Breakdown

#### By Error Code

| Code | Count | Description |
|------|-------|-------------|
| `misc` | 42 | Miscellaneous type checking error |
| `no-any-return` | 18 | Function returns Any when specific type declared |
| `attr-defined` | 15 | Attribute not defined on type |
| `unreachable` | 13 | Type checking error |
| `var-annotated` | 9 | Variable missing type annotation |
| `no-untyped-def` | 4 | Function missing return type annotation |
| `func-returns-value` | 1 | Type checking error |
| `name-defined` | 1 | Type checking error |
| `return-value` | 1 | Type checking error |
| `union-attr` | 1 | Type checking error |
| `syntax` | 1 | Type checking error |
| `unused-ignore` | 1 | Unused type: ignore comment |

#### By Package (Top 10)

| Package | Errors |
|---------|--------|
| `lexigram-admin` | 69 |
| `lexigram` | 35 |
| `lexigram-ai` | 1 |
| `lexigram-testing` | 1 |

## Package Metrics

| Package | Source Files | Test Files |
|---------|--------------|------------|
| `lexigram` | 304 | 266 |
| `lexigram-admin` | 498 | 461 |
| `lexigram-ai` | 25 | 53 |
| `lexigram-ai-agents` | 57 | 41 |
| `lexigram-ai-evaluation` | 22 | 24 |
| `lexigram-ai-feedback` | 25 | 29 |
| `lexigram-ai-governance` | 65 | 46 |
| `lexigram-ai-guard` | 34 | 22 |
| `lexigram-ai-llm` | 150 | 123 |
| `lexigram-ai-mcp` | 63 | 36 |
| `lexigram-ai-memory` | 49 | 32 |
| `lexigram-ai-observability` | 27 | 30 |
| `lexigram-ai-prompt` | 46 | 32 |
| `lexigram-ai-rag` | 186 | 46 |
| `lexigram-ai-relay` | 43 | 35 |
| `lexigram-ai-relay-gateway` | 65 | 55 |
| `lexigram-ai-session` | 46 | 35 |
| `lexigram-ai-skills` | 53 | 38 |
| `lexigram-ai-workers` | 34 | 34 |
| `lexigram-audit` | 46 | 35 |
| `lexigram-auth` | 132 | 86 |
| `lexigram-cache` | 88 | 68 |
| `lexigram-cli` | 96 | 76 |
| `lexigram-contracts` | 324 | 165 |
| `lexigram-events` | 157 | 108 |
| `lexigram-features` | 35 | 25 |
| `lexigram-graph` | 25 | 32 |
| `lexigram-graphql` | 82 | 62 |
| `lexigram-http` | 33 | 31 |
| `lexigram-monitor` | 88 | 58 |
| `lexigram-multimedia` | 21 | 23 |
| `lexigram-multimedia-beat` | 11 | 7 |
| `lexigram-multimedia-image` | 13 | 9 |
| `lexigram-multimedia-interpolate` | 12 | 7 |
| `lexigram-multimedia-music` | 15 | 9 |
| `lexigram-multimedia-tts` | 20 | 13 |
| `lexigram-multimedia-upscale` | 15 | 9 |
| `lexigram-multimedia-video` | 24 | 20 |
| `lexigram-nosql` | 43 | 46 |
| `lexigram-notification` | 53 | 35 |
| `lexigram-queue` | 44 | 41 |
| `lexigram-resilience` | 54 | 37 |
| `lexigram-search` | 94 | 60 |
| `lexigram-secrets` | 25 | 14 |
| `lexigram-sql` | 192 | 148 |
| `lexigram-storage` | 37 | 36 |
| `lexigram-tasks` | 86 | 61 |
| `lexigram-tenancy` | 64 | 43 |
| `lexigram-testing` | 153 | 40 |
| `lexigram-ui` | 158 | 75 |
| `lexigram-vector` | 63 | 41 |
| `lexigram-web` | 186 | 169 |
| `lexigram-webhook` | 42 | 35 |
| `lexigram-workflow` | 68 | 53 |

