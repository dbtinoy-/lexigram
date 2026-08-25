# AUDIT_QUALITY.md — Lexigram Framework Quality Snapshot

> **Source**: Live command evidence from repository quality tools, with package counts as supporting context.

---

## Summary

- Tool checks run: 2
- Passing tools: 2
- Failing tools: 0
- Packages counted: 55
- Total mypy errors: 0
- Packages with errors: 0

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **PASS** | 0 | 239 ms | `uv run ruff check .` |
| `Mypy` | **PASS** | 0 | 46862 ms | `uv run mypy src/ (per-package across 55 packages)` |

### Ruff

- Status: **PASS**
- Exit code: `0`
- Duration: `239 ms`
- Command: `uv run ruff check .`
- Output snippet:

```text
All checks passed!
```

### Mypy

- Status: **PASS**
- Exit code: `0`
- Duration: `46862 ms`
- Command: `uv run mypy src/ (per-package across 55 packages)`
- Output snippet:

```text
All per-package mypy checks passed.
```

## Package Metrics

| Package | Source Files | Test Files |
|---------|--------------|------------|
| `lexigram` | 309 | 274 |
| `lexigram-admin` | 569 | 477 |
| `lexigram-ai` | 25 | 101 |
| `lexigram-ai-agents` | 60 | 44 |
| `lexigram-ai-evaluation` | 22 | 24 |
| `lexigram-ai-feedback` | 25 | 29 |
| `lexigram-ai-governance` | 78 | 46 |
| `lexigram-ai-guard` | 34 | 22 |
| `lexigram-ai-llm` | 160 | 130 |
| `lexigram-ai-mcp` | 64 | 36 |
| `lexigram-ai-memory` | 49 | 32 |
| `lexigram-ai-observability` | 27 | 30 |
| `lexigram-ai-prompt` | 46 | 34 |
| `lexigram-ai-rag` | 189 | 52 |
| `lexigram-ai-relay` | 43 | 44 |
| `lexigram-ai-relay-gateway` | 67 | 66 |
| `lexigram-ai-session` | 46 | 35 |
| `lexigram-ai-skills` | 53 | 38 |
| `lexigram-ai-workers` | 35 | 34 |
| `lexigram-audit` | 46 | 37 |
| `lexigram-auth` | 137 | 86 |
| `lexigram-builder` | 15 | 7 |
| `lexigram-cache` | 94 | 72 |
| `lexigram-cli` | 112 | 77 |
| `lexigram-contracts` | 350 | 166 |
| `lexigram-events` | 158 | 108 |
| `lexigram-features` | 35 | 25 |
| `lexigram-graph` | 25 | 32 |
| `lexigram-graphql` | 82 | 62 |
| `lexigram-http` | 33 | 31 |
| `lexigram-monitor` | 94 | 58 |
| `lexigram-multimedia` | 21 | 23 |
| `lexigram-multimedia-beat` | 11 | 7 |
| `lexigram-multimedia-image` | 13 | 9 |
| `lexigram-multimedia-interpolate` | 12 | 7 |
| `lexigram-multimedia-music` | 15 | 9 |
| `lexigram-multimedia-tts` | 20 | 13 |
| `lexigram-multimedia-upscale` | 15 | 9 |
| `lexigram-multimedia-video` | 28 | 20 |
| `lexigram-nosql` | 43 | 46 |
| `lexigram-notification` | 60 | 36 |
| `lexigram-queue` | 44 | 41 |
| `lexigram-resilience` | 56 | 37 |
| `lexigram-search` | 97 | 60 |
| `lexigram-secrets` | 25 | 14 |
| `lexigram-sql` | 194 | 151 |
| `lexigram-storage` | 39 | 36 |
| `lexigram-tasks` | 91 | 61 |
| `lexigram-tenancy` | 64 | 43 |
| `lexigram-testing` | 170 | 41 |
| `lexigram-ui` | 165 | 79 |
| `lexigram-vector` | 65 | 41 |
| `lexigram-web` | 200 | 169 |
| `lexigram-webhook` | 42 | 35 |
| `lexigram-workflow` | 69 | 53 |

