# AUDIT_QUALITY.md — Lexigram Framework Quality Snapshot

> **Source**: Live command evidence from repository quality tools, with package counts as supporting context.

---

## Summary

- Tool checks run: 2
- Passing tools: 0
- Failing tools: 2
- Packages counted: 54
- Total mypy errors: 54
- Packages with errors: 54

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **FAIL** | 1 | 299 ms | `uv run ruff check .` |
| `Mypy` | **FAIL** | 2 | 16247 ms | `uv run mypy src/ (per-package across 54 packages)` |

### Ruff

- Status: **FAIL**
- Exit code: `1`
- Duration: `299 ms`
- Command: `uv run ruff check .`
- Output snippet:

```text
W292 [*] No newline at end of file
   --> experimental/apps/lexigram-ui/src/lexigram/ui/__init__.py:162:60
    |
161 | def __dir__() -> list[str]:
162 |     return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))
    |                                                            ^
help: Add trailing newline
    |
...
```

### Mypy

- Status: **FAIL**
- Exit code: `2`
- Duration: `16247 ms`
- Command: `uv run mypy src/ (per-package across 54 packages)`
- Output snippet:

```text
[lexigram] 1 errors
[lexigram-admin] 1 errors
[lexigram-ai] 1 errors
[lexigram-ai-agents] 1 errors
[lexigram-ai-evaluation] 1 errors
[lexigram-ai-feedback] 1 errors
[lexigram-ai-governance] 1 errors
[lexigram-ai-guard] 1 errors
[lexigram-ai-llm] 1 errors
[lexigram-ai-mcp] 1 errors
[lexigram-ai-memory] 1 errors
[lexigram-ai-observability] 1 errors
[lexigram-ai-prompt] 1 errors
[lexigram-ai-rag] 1 errors
[lexigram-ai-relay] 1 errors
[lexigram-ai-relay-gateway] 1 errors
[lexigram-ai-session] 1 errors
[lexigram-ai-skills] 1 errors
[lexigram-ai-workers] 1 errors
[lexigram-audit] 1 errors
[lexigram-auth] 1 errors
[lexigram-cache] 1 errors
[lexigram-cli] 1 errors
[lexigram-contracts] 1 errors
[lexigram-events] 1 errors
[lexigram-features] 1 errors
[lexigram-graph] 1 errors
[lexigram-graphql] 1 errors
[lexigram-http] 1 errors
[lexigram-monitor] 1 errors
[lexigram-multimedia] 1 errors
[lexigram-multimedia-beat] 1 errors
[lexigram-multimedia-image] 1 errors
[lexigram-multimedia-interpolate] 1 errors
[lexigram-multimedia-music] 1 errors
[lexigram-multimedia-tts] 1 errors
[lexigram-multimedia-upscale] 1 errors
[lexigram-multimedia-video] 1 errors
[lexigram-nosql] 1 errors
[lexigram-notification] 1 errors
[lexigram-queue] 1 errors
[lexigram-resilience] 1 errors
[lexigram-search] 1 errors
[lexigram-secrets] 1 errors
[lexigram-sql] 1 errors
[lexigram-storage] 1 errors
[lexigram-tasks] 1 errors
[lexigram-tenancy] 1 errors
[lexigram-testing] 1 errors
[lexigram-ui] 1 errors
[lexigram-vector] 1 errors
[lexigram-web] 1 errors
[lexigram-webhook] 1 errors
[lexigram-workflow] 1 errors
```

## Package Metrics

| Package | Source Files | Test Files |
|---------|--------------|------------|
| `lexigram` | 304 | 259 |
| `lexigram-admin` | 488 | 436 |
| `lexigram-ai` | 25 | 49 |
| `lexigram-ai-agents` | 57 | 39 |
| `lexigram-ai-evaluation` | 22 | 24 |
| `lexigram-ai-feedback` | 25 | 29 |
| `lexigram-ai-governance` | 65 | 46 |
| `lexigram-ai-guard` | 34 | 22 |
| `lexigram-ai-llm` | 150 | 121 |
| `lexigram-ai-mcp` | 63 | 36 |
| `lexigram-ai-memory` | 49 | 32 |
| `lexigram-ai-observability` | 27 | 30 |
| `lexigram-ai-prompt` | 46 | 32 |
| `lexigram-ai-rag` | 186 | 41 |
| `lexigram-ai-relay` | 36 | 26 |
| `lexigram-ai-relay-gateway` | 55 | 41 |
| `lexigram-ai-session` | 46 | 35 |
| `lexigram-ai-skills` | 53 | 38 |
| `lexigram-ai-workers` | 34 | 34 |
| `lexigram-audit` | 46 | 35 |
| `lexigram-auth` | 129 | 82 |
| `lexigram-cache` | 86 | 68 |
| `lexigram-cli` | 96 | 74 |
| `lexigram-contracts` | 318 | 159 |
| `lexigram-events` | 157 | 95 |
| `lexigram-features` | 35 | 23 |
| `lexigram-graph` | 25 | 32 |
| `lexigram-graphql` | 74 | 62 |
| `lexigram-http` | 31 | 26 |
| `lexigram-monitor` | 84 | 57 |
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
| `lexigram-sql` | 176 | 118 |
| `lexigram-storage` | 37 | 36 |
| `lexigram-tasks` | 82 | 61 |
| `lexigram-tenancy` | 64 | 43 |
| `lexigram-testing` | 152 | 39 |
| `lexigram-ui` | 158 | 75 |
| `lexigram-vector` | 63 | 41 |
| `lexigram-web` | 186 | 165 |
| `lexigram-webhook` | 42 | 34 |
| `lexigram-workflow` | 68 | 51 |

