# AUDIT_DEPENDENCIES.md — Lexigram Framework Dependency Freshness Snapshot

> **Source**: Live command evidence from `uv pip list --outdated` and workspace
> manifest scans against `dev/checks/dep_pins.py`.

---

## Summary

- Outdated packages detected: 12
- Workspace members with own pyproject.toml: 54
- Unbounded third-party pins (baseline debt): 807

## Tool Results

| Tool | Status | Exit Code | Duration | Command |
|------|--------|-----------|----------|---------|
| `uv pip list --outdated` | **PASS** | 0 | 1927 ms | `uv pip list --outdated` |
| `check_dep_pins.py` | **PASS** | 0 | 411 ms | `uv run python dev/check_dep_pins.py` |

## Outdated Packages

| Package | Installed | Latest | Type |
|---------|-----------|--------|------|
| `argon2-cffi-bindings` | 25.1.0 | 26.1.0 | wheel |
| `botocore` | 1.40.61 | 1.43.81 | wheel |
| `click` | 8.4.2 | 8.5.0 | wheel |
| `cryptography` | 50.0.0 | 50.0.1 | wheel |
| `filelock` | 3.32.3 | 3.32.4 | wheel |
| `platformdirs` | 4.11.3 | 4.11.4 | wheel |
| `pydantic-core` | 2.46.4 | 2.48.0 | wheel |
| `python-discovery` | 1.5.2 | 1.5.3 | wheel |
| `rich` | 13.9.4 | 15.0.0 | wheel |
| `ruff` | 0.16.3 | 0.16.4 | wheel |
| `types-webencodings` | 0.5.0.20260408 | 0.6.0.20260826 | wheel |
| `virtualenv` | 21.7.4 | 21.7.5 | wheel |

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

Baseline guard: `dev/checks/dep_pins.py` fails CI on unbounded third-party pins not covered by `dev/dep_pins_baseline.json`; regenerate deliberately with `--write-baseline`.
