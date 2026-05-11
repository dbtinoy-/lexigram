# AUDIT_QUALITY.md — Lexigram Framework Quality Snapshot

> **Source**: Live command evidence from repository quality tools, with package counts as supporting context.

---

## Summary

- Tool checks run: 2
- Passing tools: 0
- Failing tools: 2
- Packages counted: 54
- Total mypy errors: 197
- Packages with errors: 23

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **FAIL** | 1 | 247 ms | `uv run ruff check .` |
| `Mypy` | **FAIL** | 1 | 75068 ms | `uv run mypy src/ (per-package across 54 packages)` |

### Ruff

- Status: **FAIL**
- Exit code: `1`
- Duration: `247 ms`
- Command: `uv run ruff check .`
- Output snippet:

```text
F401 [*] `lexigram.ui.raw` imported but unused
  --> lexigram-admin/src/lexigram/admin/ui/organisms/dashboard/widgets.py:15:40
   |
13 | from typing import Any
14 |
15 | from lexigram.ui import Component, el, raw
   |                                        ^^^
16 |
...
```

### Mypy

- Status: **FAIL**
- Exit code: `1`
- Duration: `75068 ms`
- Command: `uv run mypy src/ (per-package across 54 packages)`
- Output snippet:

```text
[lexigram-admin] 110 errors
[lexigram-ai-governance] 1 errors
[lexigram-ai-llm] 12 errors
[lexigram-ai-rag] 1 errors
[lexigram-ai-relay-gateway] 1 errors
[lexigram-auth] 2 errors
[lexigram-cli] 2 errors
[lexigram-events] 3 errors
[lexigram-multimedia-beat] 2 errors
[lexigram-multimedia-interpolate] 2 errors
[lexigram-multimedia-music] 4 errors
[lexigram-multimedia-tts] 9 errors
[lexigram-multimedia-upscale] 4 errors
[lexigram-multimedia-video] 6 errors
[lexigram-nosql] 2 errors
[lexigram-queue] 3 errors
[lexigram-resilience] 1 errors
[lexigram-search] 1 errors
[lexigram-secrets] 7 errors
[lexigram-storage] 4 errors
[lexigram-tasks] 3 errors
[lexigram-vector] 15 errors
[lexigram-workflow] 2 errors
```

### Mypy Error Breakdown

#### By Error Code

| Code | Count | Description |
|------|-------|-------------|
| `arg-type` | 72 | Argument type mismatch |
| `import-not-found` | 53 | Type checking error |
| `unused-ignore` | 39 | Unused type: ignore comment |
| `attr-defined` | 9 | Attribute not defined on type |
| `union-attr` | 7 | Type checking error |
| `assignment` | 4 | Type checking error |
| `no-redef` | 4 | Name already defined |
| `import-untyped` | 3 | Type checking error |
| `method-assign` | 2 | Type checking error |
| `name-defined` | 2 | Type checking error |
| `annotation-unchecked` | 2 | Type checking error |
| `str` | 1 | Type checking error |
| `return-value` | 1 | Type checking error |
| `misc` | 1 | Miscellaneous type checking error |

#### By Package (Top 10)

| Package | Errors |
|---------|--------|
| `lexigram-admin` | 110 |
| `lexigram-vector` | 15 |
| `lexigram-ai-llm` | 12 |
| `lexigram-multimedia-tts` | 9 |
| `lexigram-secrets` | 7 |
| `lexigram-multimedia-video` | 6 |
| `lexigram-multimedia-music` | 4 |
| `lexigram-multimedia-upscale` | 4 |
| `lexigram-storage` | 4 |
| `lexigram-events` | 3 |

## Package Metrics

| Package | Source Files | Test Files |
|---------|--------------|------------|
| `lexigram` | 294 | 251 |
| `lexigram-admin` | 452 | 399 |
| `lexigram-ai` | 25 | 41 |
| `lexigram-ai-agents` | 56 | 37 |
| `lexigram-ai-evaluation` | 18 | 20 |
| `lexigram-ai-feedback` | 26 | 27 |
| `lexigram-ai-governance` | 64 | 43 |
| `lexigram-ai-guard` | 34 | 20 |
| `lexigram-ai-llm` | 150 | 120 |
| `lexigram-ai-mcp` | 63 | 34 |
| `lexigram-ai-memory` | 49 | 29 |
| `lexigram-ai-observability` | 27 | 28 |
| `lexigram-ai-prompt` | 46 | 32 |
| `lexigram-ai-rag` | 186 | 41 |
| `lexigram-ai-relay` | 25 | 22 |
| `lexigram-ai-relay-gateway` | 41 | 34 |
| `lexigram-ai-session` | 46 | 35 |
| `lexigram-ai-skills` | 53 | 37 |
| `lexigram-ai-workers` | 34 | 34 |
| `lexigram-audit` | 46 | 31 |
| `lexigram-auth` | 128 | 77 |
| `lexigram-cache` | 85 | 59 |
| `lexigram-cli` | 96 | 74 |
| `lexigram-contracts` | 313 | 150 |
| `lexigram-events` | 153 | 88 |
| `lexigram-features` | 35 | 23 |
| `lexigram-graph` | 25 | 31 |
| `lexigram-graphql` | 74 | 60 |
| `lexigram-http` | 31 | 25 |
| `lexigram-monitor` | 79 | 51 |
| `lexigram-multimedia` | 21 | 23 |
| `lexigram-multimedia-beat` | 11 | 6 |
| `lexigram-multimedia-image` | 13 | 9 |
| `lexigram-multimedia-interpolate` | 12 | 6 |
| `lexigram-multimedia-music` | 15 | 8 |
| `lexigram-multimedia-tts` | 20 | 12 |
| `lexigram-multimedia-upscale` | 15 | 7 |
| `lexigram-multimedia-video` | 24 | 19 |
| `lexigram-nosql` | 42 | 38 |
| `lexigram-notification` | 53 | 33 |
| `lexigram-queue` | 43 | 35 |
| `lexigram-resilience` | 54 | 32 |
| `lexigram-search` | 86 | 57 |
| `lexigram-secrets` | 25 | 11 |
| `lexigram-sql` | 176 | 110 |
| `lexigram-storage` | 37 | 35 |
| `lexigram-tasks` | 82 | 56 |
| `lexigram-tenancy` | 64 | 43 |
| `lexigram-testing` | 151 | 39 |
| `lexigram-ui` | 152 | 69 |
| `lexigram-vector` | 62 | 38 |
| `lexigram-web` | 187 | 160 |
| `lexigram-webhook` | 42 | 34 |
| `lexigram-workflow` | 68 | 51 |

