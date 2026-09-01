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
| `Ruff` | **PASS** | 0 | 236 ms | `uv run ruff check .` |
| `Mypy` | **PASS** | 0 | 57116 ms | `uv run mypy src/ (per-package across 55 packages)` |

### Ruff

- Status: **PASS**
- Exit code: `0`
- Duration: `236 ms`
- Command: `uv run ruff check .`
- Output snippet:

```text
All checks passed!
```

### Mypy

- Status: **PASS**
- Exit code: `0`
- Duration: `57116 ms`
- Command: `uv run mypy src/ (per-package across 55 packages)`
- Output snippet:

```text
All per-package mypy checks passed.
```

## Package Metrics

| Package | Source Files | Test Files |
|---------|--------------|------------|
| `lexigram` | 311 | 282 |
| `lexigram-admin` | 575 | 531 |
| `lexigram-ai` | 24 | 101 |
| `lexigram-ai-agents` | 59 | 44 |
| `lexigram-ai-evaluation` | 22 | 24 |
| `lexigram-ai-feedback` | 24 | 29 |
| `lexigram-ai-governance` | 77 | 46 |
| `lexigram-ai-guard` | 33 | 22 |
| `lexigram-ai-llm` | 160 | 131 |
| `lexigram-ai-mcp` | 63 | 37 |
| `lexigram-ai-memory` | 48 | 32 |
| `lexigram-ai-observability` | 26 | 30 |
| `lexigram-ai-prompt` | 45 | 34 |
| `lexigram-ai-rag` | 188 | 52 |
| `lexigram-ai-relay` | 42 | 44 |
| `lexigram-ai-relay-gateway` | 66 | 66 |
| `lexigram-ai-session` | 46 | 37 |
| `lexigram-ai-skills` | 52 | 40 |
| `lexigram-ai-workers` | 34 | 34 |
| `lexigram-audit` | 46 | 38 |
| `lexigram-auth` | 136 | 91 |
| `lexigram-builder` | 51 | 1 |
| `lexigram-cache` | 93 | 73 |
| `lexigram-cli` | 97 | 80 |
| `lexigram-contracts` | 346 | 168 |
| `lexigram-events` | 158 | 114 |
| `lexigram-features` | 34 | 26 |
| `lexigram-graph` | 25 | 33 |
| `lexigram-graphql` | 82 | 63 |
| `lexigram-http` | 32 | 32 |
| `lexigram-monitor` | 93 | 59 |
| `lexigram-multimedia` | 20 | 23 |
| `lexigram-multimedia-beat` | 12 | 7 |
| `lexigram-multimedia-image` | 14 | 9 |
| `lexigram-multimedia-interpolate` | 12 | 7 |
| `lexigram-multimedia-music` | 16 | 9 |
| `lexigram-multimedia-tts` | 21 | 13 |
| `lexigram-multimedia-upscale` | 16 | 9 |
| `lexigram-multimedia-video` | 29 | 20 |
| `lexigram-nosql` | 42 | 47 |
| `lexigram-notification` | 61 | 38 |
| `lexigram-queue` | 45 | 43 |
| `lexigram-resilience` | 55 | 38 |
| `lexigram-search` | 97 | 62 |
| `lexigram-secrets` | 25 | 15 |
| `lexigram-sql` | 197 | 157 |
| `lexigram-storage` | 38 | 38 |
| `lexigram-tasks` | 92 | 64 |
| `lexigram-tenancy` | 63 | 44 |
| `lexigram-testing` | 170 | 41 |
| `lexigram-ui` | 169 | 90 |
| `lexigram-vector` | 65 | 43 |
| `lexigram-web` | 202 | 176 |
| `lexigram-webhook` | 41 | 36 |
| `lexigram-workflow` | 68 | 54 |

