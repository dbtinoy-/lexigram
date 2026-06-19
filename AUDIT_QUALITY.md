# AUDIT_QUALITY.md — Lexigram Framework Quality Snapshot

> **Source**: Live command evidence from repository quality tools, with package counts as supporting context.

---

## Summary

- Tool checks run: 2
- Passing tools: 0
- Failing tools: 2
- Packages counted: 54
- Total mypy errors: 0
- Packages with errors: 0

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `Ruff` | **FAIL** | 1 | 2022 ms | `uv run ruff check .` |
| `Mypy` | **FAIL** | 1 | 37646 ms | `uv run mypy src/ (per-package across 54 packages)` |

### Ruff

- Status: **FAIL**
- Exit code: `1`
- Duration: `2022 ms`
- Command: `uv run ruff check .`
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
  
```

### Mypy

- Status: **FAIL**
- Exit code: `1`
- Duration: `37646 ms`
- Command: `uv run mypy src/ (per-package across 54 packages)`
- Output snippet:

```text
[lexigram] 0 errors
[lexigram-admin] 0 errors
[lexigram-ai] 0 errors
[lexigram-ai-agents] 0 errors
[lexigram-ai-evaluation] 0 errors
[lexigram-ai-feedback] 0 errors
[lexigram-ai-governance] 0 errors
[lexigram-ai-guard] 0 errors
[lexigram-ai-llm] 0 errors
[lexigram-ai-mcp] 0 errors
[lexigram-ai-memory] 0 errors
[lexigram-ai-observability] 0 errors
[lexigram-ai-prompt] 0 errors
[lexigram-ai-rag] 0 errors
[lexigram-ai-relay] 0 errors
[lexigram-ai-relay-gateway] 0 errors
[lexigram-ai-session] 0 errors
[lexigram-ai-skills] 0 errors
[lexigram-ai-workers] 0 errors
[lexigram-audit] 0 errors
[lexigram-auth] 0 errors
[lexigram-cache] 0 errors
[lexigram-cli] 0 errors
[lexigram-contracts] 0 errors
[lexigram-events] 0 errors
[lexigram-features] 0 errors
[lexigram-graph] 0 errors
[lexigram-graphql] 0 errors
[lexigram-http] 0 errors
[lexigram-monitor] 0 errors
[lexigram-multimedia] 0 errors
[lexigram-multimedia-beat] 0 errors
[lexigram-multimedia-image] 0 errors
[lexigram-multimedia-interpolate] 0 errors
[lexigram-multimedia-music] 0 errors
[lexigram-multimedia-tts] 0 errors
[lexigram-multimedia-upscale] 0 errors
[lexigram-multimedia-video] 0 errors
[lexigram-nosql] 0 errors
[lexigram-notification] 0 errors
[lexigram-queue] 0 errors
[lexigram-resilience] 0 errors
[lexigram-search] 0 errors
[lexigram-secrets] 0 errors
[lexigram-sql] 0 errors
[lexigram-storage] 0 errors
[lexigram-tasks] 0 errors
[lexigram-tenancy] 0 errors
[lexigram-testing] 0 errors
[lexigram-ui] 0 errors
[lexigram-vector] 0 errors
[lexigram-web] 0 errors
[lexigram-webhook] 0 errors
[lexigram-workflow] 0 errors
```

## Package Metrics

| Package | Source Files | Test Files |
|---------|--------------|------------|
| `lexigram` | 294 | 251 |
| `lexigram-admin` | 452 | 395 |
| `lexigram-ai` | 25 | 41 |
| `lexigram-ai-agents` | 56 | 37 |
| `lexigram-ai-evaluation` | 18 | 20 |
| `lexigram-ai-feedback` | 26 | 27 |
| `lexigram-ai-governance` | 64 | 43 |
| `lexigram-ai-guard` | 34 | 20 |
| `lexigram-ai-llm` | 150 | 120 |
| `lexigram-ai-mcp` | 63 | 33 |
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
| `lexigram-contracts` | 310 | 150 |
| `lexigram-events` | 153 | 88 |
| `lexigram-features` | 35 | 23 |
| `lexigram-graph` | 25 | 31 |
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
| `lexigram-search` | 86 | 56 |
| `lexigram-secrets` | 24 | 11 |
| `lexigram-sql` | 176 | 109 |
| `lexigram-storage` | 37 | 35 |
| `lexigram-tasks` | 82 | 56 |
| `lexigram-tenancy` | 64 | 43 |
| `lexigram-testing` | 151 | 39 |
| `lexigram-ui` | 152 | 68 |
| `lexigram-vector` | 62 | 38 |
| `lexigram-web` | 188 | 160 |
| `lexigram-webhook` | 42 | 34 |
| `lexigram-workflow` | 68 | 51 |

