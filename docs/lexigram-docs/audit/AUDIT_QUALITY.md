# AUDIT_QUALITY.md — Lexigram Framework Quality Snapshot

> **Source**: Live command evidence from repository quality tools, with package counts as supporting context.

---

## Summary

- Tool checks run: 2
- Passing tools: 2
- Failing tools: 0
- Packages counted: 54
- Total mypy errors: 0
- Packages with errors: 0

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **PASS** | 0 | 249 ms | `uv run ruff check .` |
| `Mypy` | **PASS** | 0 | 94201 ms | `uv run mypy src/ (per-package across 54 packages)` |

### Ruff

- Status: **PASS**
- Exit code: `0`
- Duration: `249 ms`
- Command: `uv run ruff check .`
- Output snippet:

```text
All checks passed!
```

### Mypy

- Status: **PASS**
- Exit code: `0`
- Duration: `94201 ms`
- Command: `uv run mypy src/ (per-package across 54 packages)`
- Output snippet:

```text
All per-package mypy checks passed.
```

## Package Metrics

| Package | Source Files | Test Files |
|---------|--------------|------------|
| `lexigram` | 304 | 259 |
| `lexigram-admin` | 455 | 433 |
| `lexigram-ai` | 25 | 41 |
| `lexigram-ai-agents` | 57 | 39 |
| `lexigram-ai-evaluation` | 18 | 20 |
| `lexigram-ai-feedback` | 25 | 29 |
| `lexigram-ai-governance` | 65 | 46 |
| `lexigram-ai-guard` | 34 | 22 |
| `lexigram-ai-llm` | 150 | 121 |
| `lexigram-ai-mcp` | 63 | 36 |
| `lexigram-ai-memory` | 49 | 32 |
| `lexigram-ai-observability` | 27 | 30 |
| `lexigram-ai-prompt` | 46 | 32 |
| `lexigram-ai-rag` | 186 | 41 |
| `lexigram-ai-relay` | 25 | 22 |
| `lexigram-ai-relay-gateway` | 41 | 35 |
| `lexigram-ai-session` | 46 | 35 |
| `lexigram-ai-skills` | 53 | 38 |
| `lexigram-ai-workers` | 34 | 34 |
| `lexigram-audit` | 46 | 35 |
| `lexigram-auth` | 129 | 82 |
| `lexigram-cache` | 86 | 66 |
| `lexigram-cli` | 96 | 74 |
| `lexigram-contracts` | 316 | 158 |
| `lexigram-events` | 157 | 95 |
| `lexigram-features` | 35 | 23 |
| `lexigram-graph` | 25 | 32 |
| `lexigram-graphql` | 74 | 62 |
| `lexigram-http` | 31 | 26 |
| `lexigram-monitor` | 83 | 55 |
| `lexigram-multimedia` | 21 | 23 |
| `lexigram-multimedia-beat` | 11 | 7 |
| `lexigram-multimedia-image` | 13 | 9 |
| `lexigram-multimedia-interpolate` | 12 | 7 |
| `lexigram-multimedia-music` | 15 | 9 |
| `lexigram-multimedia-tts` | 20 | 13 |
| `lexigram-multimedia-upscale` | 15 | 9 |
| `lexigram-multimedia-video` | 24 | 20 |
| `lexigram-nosql` | 43 | 43 |
| `lexigram-notification` | 53 | 35 |
| `lexigram-queue` | 44 | 38 |
| `lexigram-resilience` | 54 | 33 |
| `lexigram-search` | 86 | 60 |
| `lexigram-secrets` | 25 | 14 |
| `lexigram-sql` | 176 | 117 |
| `lexigram-storage` | 37 | 36 |
| `lexigram-tasks` | 82 | 61 |
| `lexigram-tenancy` | 64 | 43 |
| `lexigram-testing` | 151 | 39 |
| `lexigram-ui` | 152 | 74 |
| `lexigram-vector` | 63 | 41 |
| `lexigram-web` | 186 | 165 |
| `lexigram-webhook` | 42 | 34 |
| `lexigram-workflow` | 68 | 51 |

