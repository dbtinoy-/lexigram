# AUDIT_QUALITY.md — Lexigram Framework Quality Snapshot

> **Source**: Live command evidence from repository quality tools, with package counts as supporting context.

---

## Summary

- Tool checks run: 2
- Passing tools: 1
- Failing tools: 1
- Packages counted: 54
- Total mypy errors: 33
- Packages with errors: 7

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **PASS** | 0 | 230 ms | `uv run ruff check .` |
| `Mypy` | **FAIL** | 1 | 76156 ms | `uv run mypy src/ (per-package across 54 packages)` |

### Ruff

- Status: **PASS**
- Exit code: `0`
- Duration: `230 ms`
- Command: `uv run ruff check .`
- Output snippet:

```text
All checks passed!
```

### Mypy

- Status: **FAIL**
- Exit code: `1`
- Duration: `76156 ms`
- Command: `uv run mypy src/ (per-package across 54 packages)`
- Output snippet:

```text
[lexigram-admin] 2 errors
[lexigram-ai-mcp] 2 errors
[lexigram-cache] 1 errors
[lexigram-monitor] 18 errors
[lexigram-sql] 1 errors
[lexigram-testing] 2 errors
[lexigram-web] 7 errors
```

### Mypy Error Breakdown

#### By Error Code

| Code | Count | Description |
|------|-------|-------------|
| `unused-ignore` | 15 | Unused type: ignore comment |
| `import-not-found` | 11 | Type checking error |
| `name-defined` | 2 | Type checking error |
| `unreachable` | 2 | Type checking error |
| `assignment` | 2 | Type checking error |
| `truthy-function` | 1 | Type checking error |

#### By Package (Top 10)

| Package | Errors |
|---------|--------|
| `lexigram-monitor` | 18 |
| `lexigram-web` | 7 |
| `lexigram-admin` | 2 |
| `lexigram-ai-mcp` | 2 |
| `lexigram-testing` | 2 |
| `lexigram-cache` | 1 |
| `lexigram-sql` | 1 |

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

