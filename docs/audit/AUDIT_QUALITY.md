# AUDIT_QUALITY.md — Lexigram Framework Quality Snapshot

> **Source**: Live command evidence from repository quality tools, with package counts as supporting context.

---

## Summary

- Tool checks run: 2
- Passing tools: 0
- Failing tools: 2
- Packages counted: 54
- Total mypy errors: 95
- Packages with errors: 12

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **FAIL** | 1 | 346 ms | `uv run ruff check .` |
| `Mypy` | **FAIL** | 1 | 142900 ms | `uv run mypy src/ (per-package across 54 packages)` |

### Ruff

- Status: **FAIL**
- Exit code: `1`
- Duration: `346 ms`
- Command: `uv run ruff check .`
- Output snippet:

```text
F401 [*] `lexigram.contracts.admin.StatContent` imported but unused
 --> packages/lexigram-events/src/lexigram/events/admin/handlers/events_throughput.py:7:54
  |
5 | from typing import TYPE_CHECKING
6 |
7 | from lexigram.contracts.admin import MessageContent, StatContent, Tone, WidgetParams
  |                                                      ^^^^^^^^^^^
8 | from lexigram.contracts.admin.errors import AdminError
...
```

### Mypy

- Status: **FAIL**
- Exit code: `1`
- Duration: `142900 ms`
- Command: `uv run mypy src/ (per-package across 54 packages)`
- Output snippet:

```text
[lexigram] 7 errors
[lexigram-admin] 4 errors
[lexigram-ai-mcp] 2 errors
[lexigram-cache] 6 errors
[lexigram-cli] 2 errors
[lexigram-events] 2 errors
[lexigram-graphql] 3 errors
[lexigram-monitor] 50 errors
[lexigram-resilience] 1 errors
[lexigram-search] 2 errors
[lexigram-sql] 1 errors
[lexigram-web] 15 errors
```

### Mypy Error Breakdown

#### By Error Code

| Code | Count | Description |
|------|-------|-------------|
| `unused-ignore` | 28 | Unused type: ignore comment |
| `import-not-found` | 25 | Type checking error |
| `arg-type` | 13 | Argument type mismatch |
| `no-redef` | 12 | Name already defined |
| `no-any-return` | 8 | Function returns Any when specific type declared |
| `import-untyped` | 4 | Type checking error |
| `attr-defined` | 3 | Attribute not defined on type |
| `unreachable` | 3 | Type checking error |
| `name-defined` | 2 | Type checking error |
| `union-attr` | 1 | Type checking error |

#### By Package (Top 10)

| Package | Errors |
|---------|--------|
| `lexigram-monitor` | 50 |
| `lexigram-web` | 15 |
| `lexigram` | 7 |
| `lexigram-cache` | 6 |
| `lexigram-admin` | 4 |
| `lexigram-graphql` | 3 |
| `lexigram-ai-mcp` | 2 |
| `lexigram-cli` | 2 |
| `lexigram-events` | 2 |
| `lexigram-search` | 2 |

## Package Metrics

| Package | Source Files | Test Files |
|---------|--------------|------------|
| `lexigram` | 311 | 282 |
| `lexigram-admin` | 568 | 478 |
| `lexigram-ai` | 24 | 101 |
| `lexigram-ai-agents` | 59 | 44 |
| `lexigram-ai-evaluation` | 22 | 24 |
| `lexigram-ai-feedback` | 24 | 29 |
| `lexigram-ai-governance` | 77 | 46 |
| `lexigram-ai-guard` | 33 | 22 |
| `lexigram-ai-llm` | 159 | 130 |
| `lexigram-ai-mcp` | 63 | 37 |
| `lexigram-ai-memory` | 48 | 32 |
| `lexigram-ai-observability` | 26 | 30 |
| `lexigram-ai-prompt` | 45 | 34 |
| `lexigram-ai-rag` | 188 | 52 |
| `lexigram-ai-relay` | 42 | 44 |
| `lexigram-ai-relay-gateway` | 66 | 66 |
| `lexigram-ai-session` | 45 | 36 |
| `lexigram-ai-skills` | 52 | 40 |
| `lexigram-ai-workers` | 34 | 34 |
| `lexigram-audit` | 45 | 37 |
| `lexigram-auth` | 136 | 91 |
| `lexigram-cache` | 93 | 73 |
| `lexigram-cli` | 111 | 78 |
| `lexigram-contracts` | 346 | 168 |
| `lexigram-events` | 157 | 111 |
| `lexigram-features` | 34 | 26 |
| `lexigram-graph` | 24 | 32 |
| `lexigram-graphql` | 82 | 63 |
| `lexigram-http` | 32 | 32 |
| `lexigram-monitor` | 93 | 59 |
| `lexigram-multimedia` | 20 | 23 |
| `lexigram-multimedia-beat` | 11 | 7 |
| `lexigram-multimedia-image` | 13 | 9 |
| `lexigram-multimedia-interpolate` | 12 | 7 |
| `lexigram-multimedia-music` | 15 | 9 |
| `lexigram-multimedia-tts` | 20 | 13 |
| `lexigram-multimedia-upscale` | 15 | 9 |
| `lexigram-multimedia-video` | 28 | 20 |
| `lexigram-nosql` | 42 | 47 |
| `lexigram-notification` | 59 | 38 |
| `lexigram-queue` | 43 | 42 |
| `lexigram-resilience` | 55 | 38 |
| `lexigram-search` | 96 | 61 |
| `lexigram-secrets` | 24 | 14 |
| `lexigram-sql` | 195 | 153 |
| `lexigram-storage` | 38 | 37 |
| `lexigram-tasks` | 90 | 62 |
| `lexigram-tenancy` | 63 | 44 |
| `lexigram-testing` | 170 | 41 |
| `lexigram-ui` | 164 | 79 |
| `lexigram-vector` | 64 | 42 |
| `lexigram-web` | 199 | 170 |
| `lexigram-webhook` | 41 | 36 |
| `lexigram-workflow` | 68 | 54 |

