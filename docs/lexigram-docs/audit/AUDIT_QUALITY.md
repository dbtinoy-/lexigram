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
| `Ruff` | **PASS** | 0 | 246 ms | `uv run ruff check .` |
| `Mypy` | **PASS** | 0 | 126392 ms | `uv run mypy src/ (per-package across 54 packages)` |

### Ruff

- Status: **PASS**
- Exit code: `0`
- Duration: `246 ms`
- Command: `uv run ruff check .`
- Output snippet:

```text
All checks passed!
```

### Mypy

- Status: **PASS**
- Exit code: `0`
- Duration: `126392 ms`
- Command: `uv run mypy src/ (per-package across 54 packages)`
- Output snippet:

```text
All per-package mypy checks passed.
```

## Package Metrics

| Package | Source Files | Test Files |
|---------|--------------|------------|
| `lexigram` | 295 | 252 |
| `lexigram-admin` | 453 | 430 |
| `lexigram-ai` | 25 | 41 |
| `lexigram-ai-agents` | 57 | 39 |
| `lexigram-ai-evaluation` | 18 | 20 |
| `lexigram-ai-feedback` | 26 | 27 |
| `lexigram-ai-governance` | 64 | 43 |
| `lexigram-ai-guard` | 34 | 21 |
| `lexigram-ai-llm` | 150 | 121 |
| `lexigram-ai-mcp` | 63 | 36 |
| `lexigram-ai-memory` | 49 | 32 |
| `lexigram-ai-observability` | 27 | 28 |
| `lexigram-ai-prompt` | 46 | 32 |
| `lexigram-ai-rag` | 186 | 41 |
| `lexigram-ai-relay` | 25 | 22 |
| `lexigram-ai-relay-gateway` | 41 | 35 |
| `lexigram-ai-session` | 46 | 35 |
| `lexigram-ai-skills` | 53 | 38 |
| `lexigram-ai-workers` | 34 | 34 |
| `lexigram-audit` | 46 | 34 |
| `lexigram-auth` | 128 | 81 |
| `lexigram-cache` | 86 | 65 |
| `lexigram-cli` | 96 | 74 |
| `lexigram-contracts` | 314 | 156 |
| `lexigram-events` | 153 | 88 |
| `lexigram-features` | 35 | 23 |
| `lexigram-graph` | 25 | 32 |
| `lexigram-graphql` | 74 | 62 |
| `lexigram-http` | 31 | 26 |
| `lexigram-monitor` | 81 | 51 |
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
| `lexigram-queue` | 43 | 35 |
| `lexigram-resilience` | 54 | 32 |
| `lexigram-search` | 86 | 59 |
| `lexigram-secrets` | 25 | 14 |
| `lexigram-sql` | 176 | 116 |
| `lexigram-storage` | 37 | 36 |
| `lexigram-tasks` | 82 | 60 |
| `lexigram-tenancy` | 64 | 43 |
| `lexigram-testing` | 151 | 39 |
| `lexigram-ui` | 152 | 74 |
| `lexigram-vector` | 63 | 41 |
| `lexigram-web` | 185 | 164 |
| `lexigram-webhook` | 42 | 34 |
| `lexigram-workflow` | 68 | 51 |

