# AUDIT_QUALITY.md — Lexigram Framework Quality Snapshot

> **Source**: Live command evidence from repository quality tools, with package counts as supporting context.

---

## Summary

- Tool checks run: 2
- Passing tools: 1
- Failing tools: 1
- Packages counted: 43
- Total mypy errors: 0
- Packages with errors: 0

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **FAIL** | 1 | 203 ms | `uv run ruff check .` |
| `Mypy` | **PASS** | 0 | 50350 ms | `uv run mypy src/ (per-package across 43 packages)` |

### Ruff

- Status: **FAIL**
- Exit code: `1`
- Duration: `203 ms`
- Command: `uv run ruff check .`
- Output snippet:

```text
RUF022 [*] `__all__` is not sorted
   --> lexigram-ai-governance/src/lexigram/ai/governance/__init__.py:177:11
    |
177 |   __all__ = [
    |  ___________^
178 | |     "AIAuditEvent",
179 | |     "AIAuditStore",
180 | |     "AIAuditStoreProtocol",
...
```

### Mypy

- Status: **PASS**
- Exit code: `0`
- Duration: `50350 ms`
- Command: `uv run mypy src/ (per-package across 43 packages)`
- Output snippet:

```text
All per-package mypy checks passed.
```

## Package Metrics

| Package | Source Files | Test Files |
|---------|--------------|------------|
| `lexigram` | 283 | 242 |
| `lexigram-admin` | 465 | 318 |
| `lexigram-ai` | 20 | 40 |
| `lexigram-ai-agents` | 54 | 30 |
| `lexigram-ai-evaluation` | 18 | 15 |
| `lexigram-ai-feedback` | 26 | 20 |
| `lexigram-ai-governance` | 35 | 23 |
| `lexigram-ai-guard` | 30 | 19 |
| `lexigram-ai-llm` | 139 | 106 |
| `lexigram-ai-mcp` | 63 | 32 |
| `lexigram-ai-memory` | 49 | 28 |
| `lexigram-ai-observability` | 27 | 26 |
| `lexigram-ai-prompt` | 46 | 30 |
| `lexigram-ai-rag` | 185 | 37 |
| `lexigram-ai-session` | 43 | 33 |
| `lexigram-ai-skills` | 53 | 35 |
| `lexigram-ai-workers` | 34 | 33 |
| `lexigram-audit` | 42 | 30 |
| `lexigram-auth` | 123 | 70 |
| `lexigram-cache` | 84 | 54 |
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
| `lexigram-sql` | 172 | 99 |
| `lexigram-storage` | 37 | 35 |
| `lexigram-tasks` | 78 | 51 |
| `lexigram-tenancy` | 54 | 32 |
| `lexigram-testing` | 148 | 39 |
| `lexigram-ui` | 103 | 42 |
| `lexigram-vector` | 58 | 33 |
| `lexigram-web` | 186 | 148 |
| `lexigram-webhook` | 35 | 33 |
| `lexigram-workflow` | 62 | 41 |

