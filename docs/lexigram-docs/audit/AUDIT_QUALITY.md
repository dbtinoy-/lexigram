# AUDIT_QUALITY.md — Lexigram Framework Quality Snapshot

> **Source**: Live command evidence from repository quality tools, with package counts as supporting context.

---

## Summary

- Tool checks run: 2
- Passing tools: 1
- Failing tools: 1
- Packages counted: 54
- Total mypy errors: 188
- Packages with errors: 32

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **PASS** | 0 | 242 ms | `uv run ruff check .` |
| `Mypy` | **FAIL** | 1 | 72569 ms | `uv run mypy src/ (per-package across 54 packages)` |

### Ruff

- Status: **PASS**
- Exit code: `0`
- Duration: `242 ms`
- Command: `uv run ruff check .`
- Output snippet:

```text
All checks passed!
```

### Mypy

- Status: **FAIL**
- Exit code: `1`
- Duration: `72569 ms`
- Command: `uv run mypy src/ (per-package across 54 packages)`
- Output snippet:

```text
[lexigram-admin] 11 errors
[lexigram-ai-agents] 19 errors
[lexigram-ai-governance] 4 errors
[lexigram-ai-rag] 1 errors
[lexigram-audit] 3 errors
[lexigram-auth] 3 errors
[lexigram-cache] 2 errors
[lexigram-cli] 5 errors
[lexigram-events] 12 errors
[lexigram-graph] 19 errors
[lexigram-graphql] 3 errors
[lexigram-monitor] 4 errors
[lexigram-multimedia] 1 errors
[lexigram-multimedia-beat] 1 errors
[lexigram-multimedia-image] 1 errors
[lexigram-multimedia-interpolate] 1 errors
[lexigram-multimedia-music] 1 errors
[lexigram-multimedia-tts] 1 errors
[lexigram-multimedia-upscale] 1 errors
[lexigram-multimedia-video] 1 errors
[lexigram-notification] 1 errors
[lexigram-queue] 7 errors
[lexigram-secrets] 26 errors
[lexigram-sql] 4 errors
[lexigram-tasks] 5 errors
[lexigram-tenancy] 24 errors
[lexigram-testing] 2 errors
[lexigram-ui] 13 errors
[lexigram-vector] 6 errors
[lexigram-web] 3 errors
[lexigram-webhook] 2 errors
[lexigram-workflow] 1 errors
```

### Mypy Error Breakdown

#### By Error Code

| Code | Count | Description |
|------|-------|-------------|
| `arg-type` | 64 | Argument type mismatch |
| `unused-ignore` | 49 | Unused type: ignore comment |
| `attr-defined` | 17 | Attribute not defined on type |
| `assignment` | 13 | Type checking error |
| `override` | 10 | Method override type mismatch |
| `return-value` | 7 | Type checking error |
| `str` | 5 | Type checking error |
| `name-defined` | 5 | Type checking error |
| `var-annotated` | 4 | Variable missing type annotation |
| `misc` | 4 | Miscellaneous type checking error |
| `int` | 4 | Type checking error |
| `import-not-found` | 4 | Type checking error |
| `annotation-unchecked` | 2 | Type checking error |
| `import-untyped` | 2 | Type checking error |
| `dict-item` | 2 | Type checking error |

#### By Package (Top 10)

| Package | Errors |
|---------|--------|
| `lexigram-secrets` | 26 |
| `lexigram-tenancy` | 24 |
| `lexigram-ai-agents` | 19 |
| `lexigram-graph` | 19 |
| `lexigram-ui` | 13 |
| `lexigram-events` | 12 |
| `lexigram-admin` | 11 |
| `lexigram-queue` | 7 |
| `lexigram-vector` | 6 |
| `lexigram-cli` | 5 |

## Package Metrics

| Package | Source Files | Test Files |
|---------|--------------|------------|
| `lexigram` | 286 | 245 |
| `lexigram-admin` | 462 | 327 |
| `lexigram-ai` | 24 | 40 |
| `lexigram-ai-agents` | 56 | 37 |
| `lexigram-ai-evaluation` | 18 | 20 |
| `lexigram-ai-feedback` | 26 | 26 |
| `lexigram-ai-governance` | 50 | 37 |
| `lexigram-ai-guard` | 34 | 19 |
| `lexigram-ai-llm` | 149 | 119 |
| `lexigram-ai-mcp` | 63 | 32 |
| `lexigram-ai-memory` | 49 | 28 |
| `lexigram-ai-observability` | 27 | 27 |
| `lexigram-ai-prompt` | 46 | 31 |
| `lexigram-ai-rag` | 188 | 40 |
| `lexigram-ai-relay` | 25 | 22 |
| `lexigram-ai-relay-gateway` | 35 | 22 |
| `lexigram-ai-session` | 43 | 33 |
| `lexigram-ai-skills` | 53 | 36 |
| `lexigram-ai-workers` | 34 | 33 |
| `lexigram-audit` | 46 | 31 |
| `lexigram-auth` | 128 | 70 |
| `lexigram-cache` | 87 | 55 |
| `lexigram-cli` | 96 | 72 |
| `lexigram-contracts` | 302 | 141 |
| `lexigram-events` | 154 | 83 |
| `lexigram-features` | 35 | 23 |
| `lexigram-graph` | 25 | 30 |
| `lexigram-graphql` | 74 | 59 |
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
| `lexigram-nosql` | 42 | 36 |
| `lexigram-notification` | 47 | 28 |
| `lexigram-queue` | 47 | 30 |
| `lexigram-resilience` | 53 | 31 |
| `lexigram-search` | 81 | 53 |
| `lexigram-secrets` | 24 | 11 |
| `lexigram-sql` | 179 | 103 |
| `lexigram-storage` | 37 | 35 |
| `lexigram-tasks` | 83 | 51 |
| `lexigram-tenancy` | 64 | 42 |
| `lexigram-testing` | 151 | 39 |
| `lexigram-ui` | 113 | 55 |
| `lexigram-vector` | 62 | 37 |
| `lexigram-web` | 189 | 151 |
| `lexigram-webhook` | 39 | 33 |
| `lexigram-workflow` | 68 | 51 |

