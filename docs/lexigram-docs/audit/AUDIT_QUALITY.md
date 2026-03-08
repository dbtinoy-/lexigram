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
| `Ruff` | **PASS** | 0 | 234 ms | `uv run ruff check .` |
| `Mypy` | **PASS** | 0 | 96789 ms | `uv run mypy src/ (per-package across 54 packages)` |

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

- Status: **PASS**
- Exit code: `0`
- Duration: `96789 ms`
- Command: `uv run mypy src/ (per-package across 54 packages)`
- Output snippet:

```text
All per-package mypy checks passed.
```

## Package Metrics

| Package | Source Files | Test Files |
|---------|--------------|------------|
| `lexigram` | 287 | 246 |
| `lexigram-admin` | 462 | 327 |
| `lexigram-ai` | 24 | 40 |
| `lexigram-ai-agents` | 56 | 37 |
| `lexigram-ai-evaluation` | 18 | 20 |
| `lexigram-ai-feedback` | 26 | 27 |
| `lexigram-ai-governance` | 50 | 38 |
| `lexigram-ai-guard` | 34 | 20 |
| `lexigram-ai-llm` | 149 | 120 |
| `lexigram-ai-mcp` | 63 | 33 |
| `lexigram-ai-memory` | 49 | 29 |
| `lexigram-ai-observability` | 27 | 28 |
| `lexigram-ai-prompt` | 46 | 32 |
| `lexigram-ai-rag` | 188 | 40 |
| `lexigram-ai-relay` | 25 | 22 |
| `lexigram-ai-relay-gateway` | 35 | 23 |
| `lexigram-ai-session` | 43 | 34 |
| `lexigram-ai-skills` | 53 | 37 |
| `lexigram-ai-workers` | 34 | 34 |
| `lexigram-audit` | 46 | 31 |
| `lexigram-auth` | 128 | 70 |
| `lexigram-cache` | 87 | 55 |
| `lexigram-cli` | 96 | 73 |
| `lexigram-contracts` | 302 | 141 |
| `lexigram-events` | 154 | 83 |
| `lexigram-features` | 35 | 23 |
| `lexigram-graph` | 25 | 31 |
| `lexigram-graphql` | 74 | 60 |
| `lexigram-http` | 31 | 25 |
| `lexigram-monitor` | 79 | 50 |
| `lexigram-multimedia` | 21 | 23 |
| `lexigram-multimedia-beat` | 11 | 6 |
| `lexigram-multimedia-image` | 13 | 9 |
| `lexigram-multimedia-interpolate` | 12 | 7 |
| `lexigram-multimedia-music` | 15 | 9 |
| `lexigram-multimedia-tts` | 20 | 12 |
| `lexigram-multimedia-upscale` | 15 | 8 |
| `lexigram-multimedia-video` | 24 | 19 |
| `lexigram-nosql` | 42 | 37 |
| `lexigram-notification` | 47 | 29 |
| `lexigram-queue` | 47 | 31 |
| `lexigram-resilience` | 53 | 31 |
| `lexigram-search` | 81 | 53 |
| `lexigram-secrets` | 24 | 11 |
| `lexigram-sql` | 179 | 104 |
| `lexigram-storage` | 37 | 35 |
| `lexigram-tasks` | 83 | 51 |
| `lexigram-tenancy` | 64 | 43 |
| `lexigram-testing` | 151 | 39 |
| `lexigram-ui` | 113 | 56 |
| `lexigram-vector` | 62 | 38 |
| `lexigram-web` | 189 | 151 |
| `lexigram-webhook` | 39 | 33 |
| `lexigram-workflow` | 68 | 51 |

