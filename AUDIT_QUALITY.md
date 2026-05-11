# AUDIT_QUALITY.md — Lexigram Framework Quality Snapshot

> **Source**: Live command evidence from repository quality tools, with package counts as supporting context.

---

## Summary

- Tool checks run: 2
- Passing tools: 1
- Failing tools: 1
- Packages counted: 54
- Total mypy errors: 3
- Packages with errors: 2

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **PASS** | 0 | 252 ms | `uv run ruff check .` |
| `Mypy` | **FAIL** | 1 | 88536 ms | `uv run mypy src/ (per-package across 54 packages)` |

### Ruff

- Status: **PASS**
- Exit code: `0`
- Duration: `252 ms`
- Command: `uv run ruff check .`
- Output snippet:

```text
All checks passed!
```

### Mypy

- Status: **FAIL**
- Exit code: `1`
- Duration: `88536 ms`
- Command: `uv run mypy src/ (per-package across 54 packages)`
- Output snippet:

```text
[lexigram-tasks] 2 errors
[lexigram-testing] 1 errors
```

### Mypy Error Breakdown

#### By Error Code

| Code | Count | Description |
|------|-------|-------------|
| `misc` | 3 | Miscellaneous type checking error |
| `int` | 1 | Type checking error |
| `bool` | 1 | Type checking error |

#### By Package (Top 10)

| Package | Errors |
|---------|--------|
| `lexigram-tasks` | 2 |
| `lexigram-testing` | 1 |

## Package Metrics

| Package | Source Files | Test Files |
|---------|--------------|------------|
| `lexigram` | 294 | 251 |
| `lexigram-admin` | 452 | 404 |
| `lexigram-ai` | 25 | 41 |
| `lexigram-ai-agents` | 56 | 37 |
| `lexigram-ai-evaluation` | 18 | 20 |
| `lexigram-ai-feedback` | 26 | 27 |
| `lexigram-ai-governance` | 64 | 43 |
| `lexigram-ai-guard` | 34 | 20 |
| `lexigram-ai-llm` | 150 | 120 |
| `lexigram-ai-mcp` | 63 | 35 |
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
| `lexigram-contracts` | 311 | 151 |
| `lexigram-events` | 153 | 88 |
| `lexigram-features` | 35 | 23 |
| `lexigram-graph` | 25 | 32 |
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
| `lexigram-sql` | 176 | 113 |
| `lexigram-storage` | 37 | 35 |
| `lexigram-tasks` | 82 | 56 |
| `lexigram-tenancy` | 64 | 43 |
| `lexigram-testing` | 151 | 39 |
| `lexigram-ui` | 152 | 69 |
| `lexigram-vector` | 62 | 38 |
| `lexigram-web` | 187 | 160 |
| `lexigram-webhook` | 42 | 34 |
| `lexigram-workflow` | 68 | 51 |

