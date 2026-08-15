# AUDIT_DEPENDENCIES.md — Lexigram Framework Dependency Freshness Snapshot

> **Source**: Live command evidence from `uv pip list --outdated` and workspace
> manifest scans against `scripts/check_dep_pins.py`.

---

## Summary

- Outdated packages detected: 11
- Workspace members with own pyproject.toml: 55
- Unbounded third-party pins (baseline debt): 807

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `uv pip list --outdated` | **PASS** | 0 | 1216 ms | `uv pip list --outdated` |
| `check_dep_pins.py` | **PASS** | 0 | 300 ms | `uv run python scripts/check_dep_pins.py` |

## Outdated Packages

| Package | Installed | Latest | Type |
|---------|-----------|--------|------|
| `botocore` | 1.40.61 | 1.43.75 | wheel |
| `grimp` | 3.13 | 3.15 | wheel |
| `import-linter` | 2.6 | 2.13 | wheel |
| `jiter` | 0.14.0 | 0.16.0 | wheel |
| `lexigram-contracts` | 0.1.3007 | 0.1.3010 | wheel /home/admin/Documents/AI/applications/lexigram-dev/lexigram-contracts |
| `openai` | 2.54.0 | 3.3.1 | wheel |
| `pydantic-core` | 2.46.4 | 2.48.0 | wheel |
| `pyee` | 13.0.1 | 14.0.0 | wheel |
| `rich` | 13.9.4 | 15.0.0 | wheel |
| `tqdm` | 4.67.1 | 4.70.0 | wheel |
| `uvicorn` | 0.52.3 | 0.52.4 | wheel |

## Direct Dependency Manifest

| Member | Own pyproject | Unbounded third-party pins |
|--------|---------------|----------------------------|
| `lexigram` | yes | 15 |
| `lexigram-admin` | yes | 35 |
| `lexigram-ai` | yes | 80 |
| `lexigram-ai-agents` | yes | 8 |
| `lexigram-ai-evaluation` | yes | 0 |
| `lexigram-ai-feedback` | yes | 7 |
| `lexigram-ai-governance` | yes | 8 |
| `lexigram-ai-guard` | yes | 8 |
| `lexigram-ai-llm` | yes | 33 |
| `lexigram-ai-mcp` | yes | 8 |
| `lexigram-ai-memory` | yes | 8 |
| `lexigram-ai-observability` | yes | 7 |
| `lexigram-ai-prompt` | yes | 8 |
| `lexigram-ai-rag` | yes | 21 |
| `lexigram-ai-relay` | yes | 7 |
| `lexigram-ai-relay-gateway` | yes | 9 |
| `lexigram-ai-session` | yes | 7 |
| `lexigram-ai-skills` | yes | 8 |
| `lexigram-ai-workers` | yes | 7 |
| `lexigram-all` | yes | 0 |
| `lexigram-audit` | yes | 8 |
| `lexigram-auth` | yes | 29 |
| `lexigram-cache` | yes | 25 |
| `lexigram-cli` | yes | 19 |
| `lexigram-contracts` | yes | 7 |
| `lexigram-events` | yes | 30 |
| `lexigram-features` | yes | 8 |
| `lexigram-graph` | yes | 7 |
| `lexigram-graphql` | yes | 20 |
| `lexigram-http` | yes | 9 |
| `lexigram-monitor` | yes | 24 |
| `lexigram-multimedia` | yes | 6 |
| `lexigram-multimedia-beat` | yes | 13 |
| `lexigram-multimedia-image` | yes | 8 |
| `lexigram-multimedia-interpolate` | yes | 8 |
| `lexigram-multimedia-music` | yes | 8 |
| `lexigram-multimedia-tts` | yes | 8 |
| `lexigram-multimedia-upscale` | yes | 8 |
| `lexigram-multimedia-video` | yes | 8 |
| `lexigram-nosql` | yes | 11 |
| `lexigram-notification` | yes | 20 |
| `lexigram-queue` | yes | 4 |
| `lexigram-resilience` | yes | 6 |
| `lexigram-search` | yes | 33 |
| `lexigram-secrets` | yes | 13 |
| `lexigram-sql` | yes | 25 |
| `lexigram-storage` | yes | 22 |
| `lexigram-tasks` | yes | 26 |
| `lexigram-tenancy` | yes | 8 |
| `lexigram-testing` | yes | 25 |
| `lexigram-ui` | yes | 15 |
| `lexigram-vector` | yes | 15 |
| `lexigram-web` | yes | 37 |
| `lexigram-webhook` | yes | 2 |
| `lexigram-workflow` | yes | 8 |

Baseline guard: `scripts/check_dep_pins.py` fails CI on unbounded third-party pins not covered by `scripts/dep_pins_baseline.json`; regenerate deliberately with `--write-baseline`.
