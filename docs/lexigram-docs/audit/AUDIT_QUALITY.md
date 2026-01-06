# AUDIT_QUALITY.md — Lexigram Framework Quality Snapshot

> **Source**: Live command evidence from repository quality tools, with package counts as supporting context.

---

## Summary

- Tool checks run: 2
- Passing tools: 2
- Failing tools: 0
- Packages counted: 37
- Total mypy errors: 0
- Packages with errors: 0

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **PASS** | 0 | 202 ms | `uv run ruff check .` |
| `Mypy` | **PASS** | 0 | 37429 ms | `uv run mypy src/ (per-package across 37 packages)` |

### Ruff

- Status: **PASS**
- Exit code: `0`
- Duration: `202 ms`
- Command: `uv run ruff check .`
- Output snippet:

```text
All checks passed!
```

### Mypy

- Status: **PASS**
- Exit code: `0`
- Duration: `37429 ms`
- Command: `uv run mypy src/ (per-package across 37 packages)`
- Output snippet:

```text
All per-package mypy checks passed.
```

## Package Metrics

| Package | Source Files | Test Files |
|---------|--------------|------------|
| `lexigram` | 283 | 242 |
| `lexigram-ai` | 20 | 40 |
| `lexigram-ai-agents` | 54 | 30 |
| `lexigram-ai-feedback` | 26 | 20 |
| `lexigram-ai-llm` | 139 | 106 |
| `lexigram-ai-mcp` | 63 | 32 |
| `lexigram-ai-memory` | 49 | 28 |
| `lexigram-ai-observability` | 27 | 26 |
| `lexigram-ai-rag` | 185 | 37 |
| `lexigram-ai-session` | 43 | 33 |
| `lexigram-ai-skills` | 53 | 35 |
| `lexigram-ai-workers` | 34 | 33 |
| `lexigram-audit` | 42 | 30 |
| `lexigram-auth` | 123 | 70 |
| `lexigram-cache` | 84 | 55 |
| `lexigram-cli` | 96 | 42 |
| `lexigram-contracts` | 273 | 115 |
| `lexigram-events` | 146 | 78 |
| `lexigram-features` | 35 | 20 |
| `lexigram-graph` | 22 | 21 |
| `lexigram-graphql` | 74 | 39 |
| `lexigram-http` | 31 | 23 |
| `lexigram-monitor` | 74 | 45 |
| `lexigram-nosql` | 42 | 21 |
| `lexigram-notification` | 47 | 28 |
| `lexigram-queue` | 43 | 30 |
| `lexigram-resilience` | 53 | 31 |
| `lexigram-search` | 81 | 41 |
| `lexigram-sql` | 173 | 99 |
| `lexigram-storage` | 37 | 35 |
| `lexigram-tasks` | 78 | 51 |
| `lexigram-tenancy` | 54 | 32 |
| `lexigram-testing` | 148 | 39 |
| `lexigram-vector` | 58 | 33 |
| `lexigram-web` | 186 | 148 |
| `lexigram-webhook` | 35 | 33 |
| `lexigram-workflow` | 62 | 41 |

