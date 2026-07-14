# AUDIT_SECURITY.md — Lexigram Framework Security Audit

> **Source**: Live command evidence (pip-audit, ruff bandit rules), framework security rules, and the audit tracker (`docs/AUDIT_TRACKER.md`).

---

## Summary

- Verdict: **WARN** — static analysis found issues to review
- Dependency scan: clean (0 vulnerable package(s))
- SAST (ruff `S` rules): 304 finding(s) (0 unverified, 0 verified low-risk, 304 low-signal noise)
- Framework security rules: 1 finding(s)
- Tracker areas: 99 total, 99 done

## Dependency Scan

- Command: `uv run pip-audit --timeout 60`
- Exit code: `0`
- Duration: `1152 ms`
- Vulnerable packages: 0
- Summary: `No known vulnerabilities found`

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
No known vulnerabilities found
```

## Static Analysis (ruff bandit rules)

- Exit code: `1`

### Findings (unverified)

| File | Line | Rule | Message |
|------|------|------|---------|
| `(none)` | 0 | `-` | No unverified bandit findings. |

### Verified Low-Risk Families (reviewed 2026-08-19; all closed — see notes below)

- Count: 0

All previously verified low-risk findings are closed: each site is
either `# noqa`-annotated with a per-site justification or hardened
in code. See Verification Notes.


### Low-Signal Rules (S101 asserts, S105/S106 hardcoded strings)

- Count: 304

| File | Line | Rule | Message |
|------|------|------|---------|
| `lexigram-admin/src/lexigram/admin/auth/types.py` | 24 | `S105` | Possible hardcoded password assigned to: "PASSWORD_CHANGED" |
| `lexigram-admin/src/lexigram/admin/auth/types.py` | 25 | `S105` | Possible hardcoded password assigned to: "PASSWORD_RESET_REQUESTED" |
| `lexigram-admin/src/lexigram/admin/auth/types.py` | 28 | `S105` | Possible hardcoded password assigned to: "SETUP_TOKEN_USED" |
| `lexigram-admin/src/lexigram/admin/auth/types.py` | 68 | `S105` | Possible hardcoded password assigned to: "COMMON_PASSWORD" |
| `lexigram-admin/src/lexigram/admin/exceptions.py` | 14 | `S105` | Possible hardcoded password assigned to: "AUTH_INVALID_TOKEN" |
| `lexigram-admin/src/lexigram/admin/middleware/input_sanitizer.py` | 118 | `S101` | Use of `assert` detected |
| `lexigram-admin/src/lexigram/admin/middleware/security_headers.py` | 65 | `S101` | Use of `assert` detected |
| `lexigram-admin/src/lexigram/admin/services/notifications/models.py` | 19 | `S105` | Possible hardcoded password assigned to: "PASSWORD_RESET" |
| `lexigram-admin/src/lexigram/admin/services/notifications/models.py` | 22 | `S105` | Possible hardcoded password assigned to: "PASSWORD_CHANGED" |
| `lexigram-ai-governance/src/lexigram/ai/governance/relay_billing/pricing.py` | 232 | `S101` | Use of `assert` detected |
| `lexigram-ai-governance/src/lexigram/ai/governance/relay_billing/pricing.py` | 238 | `S101` | Use of `assert` detected |
| `lexigram-ai-guard/src/lexigram/ai/guard/pipeline/result.py` | 20 | `S105` | Possible hardcoded password assigned to: "PASS" |
| `lexigram-ai-llm/src/lexigram/ai/llm/metrics/collector.py` | 26 | `S105` | Possible hardcoded password assigned to: "TOKEN_USAGE" |
| `lexigram-ai-llm/src/lexigram/ai/llm/selection/core.py` | 54 | `S105` | Possible hardcoded password assigned to: "TOKEN_COUNT" |
| `lexigram-ai-llm/src/lexigram/ai/llm/thinking/normalizer.py` | 43 | `S105` | Possible hardcoded password assigned to: "end_token" |
| `lexigram-ai-prompt/src/lexigram/ai/prompt/optimization/few_shot.py` | 104 | `S101` | Use of `assert` detected |
| `lexigram-ai-rag/src/lexigram/ai/rag/chunking/types.py` | 52 | `S105` | Possible hardcoded password assigned to: "TOKEN" |
| `lexigram-ai-rag/src/lexigram/ai/rag/context_compression/types.py` | 15 | `S105` | Possible hardcoded password assigned to: "TOKEN_LIMIT" |
| `lexigram-ai-rag/src/lexigram/ai/rag/evaluation/types.py` | 39 | `S105` | Possible hardcoded password assigned to: "TOKEN_USAGE" |
| `lexigram-ai-rag/src/lexigram/ai/rag/multimodal/loaders/audio.py` | 318 | `S101` | Use of `assert` detected |
| `lexigram-ai-rag/src/lexigram/ai/rag/routing/strategies/llm.py` | 161 | `S101` | Use of `assert` detected |
| `lexigram-ai-relay/src/lexigram/ai/relay/mappers/claude.py` | 779 | `S101` | Use of `assert` detected |
| `lexigram-ai-relay/src/lexigram/ai/relay/mappers/gemini.py` | 797 | `S101` | Use of `assert` detected |
| `lexigram-ai-session/src/lexigram/ai/session/branching/branch_manager.py` | 93 | `S101` | Use of `assert` detected |
| `lexigram-ai-workers/src/lexigram/ai/workers/dlq/worker.py` | 491 | `S101` | Use of `assert` detected |
| `lexigram-audit/src/lexigram/audit/verification/verifier.py` | 123 | `S101` | Use of `assert` detected |
| `lexigram-auth/src/lexigram/auth/authn/_jwt_lifecycle.py` | 523 | `S106` | Possible hardcoded password assigned to argument: "token_type" |
| `lexigram-auth/src/lexigram/auth/authn/security.py` | 233 | `S105` | Possible hardcoded password assigned to: "DUMMY_PASSWORD_HASH" |
| `lexigram-auth/src/lexigram/auth/constants.py` | 23 | `S105` | Possible hardcoded password assigned to: "DEFAULT_TOKEN_ALGORITHM" |
| `lexigram-auth/src/lexigram/auth/constants.py` | 24 | `S105` | Possible hardcoded password assigned to: "DEFAULT_TOKEN_TYPE" |
| `lexigram-auth/src/lexigram/auth/mfa/totp_vectors.py` | 43 | `S106` | Possible hardcoded password assigned to argument: "secret" |
| `lexigram-auth/src/lexigram/auth/mfa/totp_vectors.py` | 52 | `S106` | Possible hardcoded password assigned to argument: "secret" |
| `lexigram-auth/src/lexigram/auth/mfa/totp_vectors.py` | 61 | `S106` | Possible hardcoded password assigned to argument: "secret" |
| `lexigram-auth/src/lexigram/auth/mfa/totp_vectors.py` | 70 | `S106` | Possible hardcoded password assigned to argument: "secret" |
| `lexigram-auth/src/lexigram/auth/mfa/totp_vectors.py` | 79 | `S106` | Possible hardcoded password assigned to argument: "secret" |
| `lexigram-auth/src/lexigram/auth/mfa/totp_vectors.py` | 88 | `S106` | Possible hardcoded password assigned to argument: "secret" |
| `lexigram-auth/src/lexigram/auth/mfa/totp_vectors.py` | 97 | `S106` | Possible hardcoded password assigned to argument: "secret" |
| `lexigram-auth/src/lexigram/auth/mfa/totp_vectors.py` | 106 | `S106` | Possible hardcoded password assigned to argument: "secret" |
| `lexigram-auth/src/lexigram/auth/module.py` | 100 | `S106` | Possible hardcoded password assigned to argument: "secret_key" |
| `lexigram-auth/src/lexigram/auth/module.py` | 102 | `S106` | Possible hardcoded password assigned to argument: "secret_key" |
| `lexigram-auth/src/lexigram/auth/types.py` | 24 | `S105` | Possible hardcoded password assigned to: "TOKEN_EXPIRED" |
| `lexigram-auth/src/lexigram/auth/types.py` | 25 | `S105` | Possible hardcoded password assigned to: "TOKEN_INVALID" |
| `lexigram-cache/src/lexigram/cache/constants.py` | 176 | `S105` | Possible hardcoded password assigned to: "ERROR_MSG_INSECURE_PASSWORD" |
| `lexigram-cli/src/lexigram/cli/commands/gen.py` | 70 | `S101` | Use of `assert` detected |
| `lexigram-cli/src/lexigram/cli/registry/health.py` | 27 | `S105` | Possible hardcoded password assigned to: "PASS" |
| `lexigram-multimedia-beat/src/lexigram/multimedia/beat/di/provider.py` | 92 | `S101` | Use of `assert` detected |
| `lexigram-multimedia-image/src/lexigram/multimedia/image/config.py` | 16 | `S105` | Possible hardcoded password assigned to: "openai_api_key_secret_name" |
| `lexigram-multimedia-image/src/lexigram/multimedia/image/config.py` | 19 | `S105` | Possible hardcoded password assigned to: "stability_api_key_secret_name" |
| `lexigram-multimedia-image/src/lexigram/multimedia/image/di/provider.py` | 139 | `S101` | Use of `assert` detected |
| `lexigram-multimedia-interpolate/src/lexigram/multimedia/interpolate/di/provider.py` | 85 | `S101` | Use of `assert` detected |
| `lexigram-multimedia-music/src/lexigram/multimedia/music/di/provider.py` | 118 | `S101` | Use of `assert` detected |
| `lexigram-multimedia-tts/src/lexigram/multimedia/tts/config.py` | 19 | `S105` | Possible hardcoded password assigned to: "elevenlabs_api_key_secret_name" |
| `lexigram-multimedia-tts/src/lexigram/multimedia/tts/config.py` | 20 | `S105` | Possible hardcoded password assigned to: "openai_api_key_secret_name" |
| `lexigram-multimedia-upscale/src/lexigram/multimedia/upscale/di/provider.py` | 94 | `S101` | Use of `assert` detected |
| `lexigram-multimedia-video/src/lexigram/multimedia/video/config.py` | 30 | `S105` | Possible hardcoded password assigned to: "runway_api_key_secret_name" |
| `lexigram-multimedia-video/src/lexigram/multimedia/video/config.py` | 31 | `S105` | Possible hardcoded password assigned to: "openai_api_key_secret_name" |
| `lexigram-multimedia-video/src/lexigram/multimedia/video/di/provider.py` | 206 | `S101` | Use of `assert` detected |
| `lexigram-multimedia-video/src/lexigram/multimedia/video/processing/argv.py` | 415 | `S101` | Use of `assert` detected |
| `lexigram-multimedia-video/src/lexigram/multimedia/video/processing/argv.py` | 461 | `S101` | Use of `assert` detected |
| `lexigram-multimedia-video/src/lexigram/multimedia/video/processing/ffmpeg.py` | 352 | `S101` | Use of `assert` detected |
| `lexigram-multimedia-video/src/lexigram/multimedia/video/processing/ffmpeg.py` | 353 | `S101` | Use of `assert` detected |
| `lexigram-resilience/src/lexigram/resilience/idempotency/store.py` | 216 | `S101` | Use of `assert` detected |
| `lexigram-resilience/src/lexigram/resilience/pipeline/executor.py` | 123 | `S101` | Use of `assert` detected |
| `lexigram-resilience/src/lexigram/resilience/pipeline/executor.py` | 136 | `S101` | Use of `assert` detected |
| `lexigram-resilience/src/lexigram/resilience/pipeline/executor.py` | 149 | `S101` | Use of `assert` detected |
| `lexigram-storage/src/lexigram/storage/kv/local.py` | 63 | `S101` | Use of `assert` detected |
| `lexigram-tasks/src/lexigram/tasks/backends/rabbitmq.py` | 131 | `S101` | Use of `assert` detected |
| `lexigram-tasks/src/lexigram/tasks/backends/rabbitmq.py` | 132 | `S101` | Use of `assert` detected |
| `lexigram-tasks/src/lexigram/tasks/backends/rabbitmq.py` | 172 | `S101` | Use of `assert` detected |
| `lexigram-tasks/src/lexigram/tasks/backends/rabbitmq.py` | 230 | `S101` | Use of `assert` detected |
| `lexigram-tasks/src/lexigram/tasks/backends/rabbitmq.py` | 245 | `S101` | Use of `assert` detected |
| `lexigram-tasks/src/lexigram/tasks/backends/redis.py` | 126 | `S101` | Use of `assert` detected |
| `lexigram-tasks/src/lexigram/tasks/concurrency/compute.py` | 492 | `S101` | Use of `assert` detected |
| `lexigram-tasks/src/lexigram/tasks/di/provider.py` | 236 | `S101` | Use of `assert` detected |
| `lexigram-tasks/src/lexigram/tasks/progress/tracker.py` | 230 | `S101` | Use of `assert` detected |
| `lexigram-tasks/src/lexigram/tasks/scheduling/cron.py` | 83 | `S101` | Use of `assert` detected |
| `lexigram-tasks/src/lexigram/tasks/scheduling/cron.py` | 101 | `S101` | Use of `assert` detected |
| `lexigram-tasks/src/lexigram/tasks/scheduling/cron.py` | 118 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/ai/client.py` | 144 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/ai/client.py` | 149 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/ai/client.py` | 154 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/auth/bed.py` | 45 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/auth/bed.py` | 50 | `S106` | Possible hardcoded password assigned to argument: "secret_key" |
| `lexigram-testing/src/lexigram/testing/clients/auth/bed.py` | 53 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/auth/fixtures.py` | 81 | `S106` | Possible hardcoded password assigned to argument: "password" |
| `lexigram-testing/src/lexigram/testing/clients/auth/fixtures.py` | 93 | `S106` | Possible hardcoded password assigned to argument: "password" |
| `lexigram-testing/src/lexigram/testing/clients/auth/fixtures.py` | 105 | `S106` | Possible hardcoded password assigned to argument: "password" |
| `lexigram-testing/src/lexigram/testing/clients/auth/fixtures.py` | 117 | `S106` | Possible hardcoded password assigned to argument: "password" |
| `lexigram-testing/src/lexigram/testing/clients/auth/fixtures.py` | 130 | `S106` | Possible hardcoded password assigned to argument: "password" |
| `lexigram-testing/src/lexigram/testing/clients/auth/fixtures.py` | 288 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/auth/fixtures.py` | 310 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/auth/fixtures.py` | 332 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/auth/fixtures.py` | 458 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/auth/types.py` | 102 | `S105` | Possible hardcoded password assigned to: "token_type" |
| `lexigram-testing/src/lexigram/testing/clients/auth/types.py` | 129 | `S106` | Possible hardcoded password assigned to argument: "token_type" |
| `lexigram-testing/src/lexigram/testing/clients/cache/bed.py` | 49 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/cache/bed.py` | 58 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/cache/bed.py` | 63 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/cache/bed.py` | 91 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/cache/client_core.py` | 209 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/cache/client_core.py` | 240 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/cache/client_core.py` | 242 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/cache/client_core.py` | 245 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/events/components/test_bed.py` | 49 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/storage/fixtures.py` | 38 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/storage/fixtures.py` | 48 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/tasks/client.py` | 65 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/tasks/client.py` | 66 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/tasks/client.py` | 94 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/tasks/client.py` | 125 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/ui/core.py` | 76 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/ui/core.py` | 81 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/ui/core.py` | 89 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/ui/core.py` | 94 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/ui/core.py` | 101 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/web/client.py` | 54 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/web/client.py` | 84 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/web/client.py` | 97 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/clients/web/client.py` | 111 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/audit.py` | 70 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/audit.py` | 71 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/audit.py` | 85 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/audit.py` | 87 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/audit.py` | 100 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/audit.py` | 112 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/audit.py` | 121 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/audit.py` | 155 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/audit.py` | 156 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/audit.py` | 168 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/audit.py` | 181 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/audit.py` | 190 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/audit.py` | 191 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/blob_store.py` | 52 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/blob_store.py` | 63 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/blob_store.py` | 69 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/blob_store.py` | 81 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/blob_store.py` | 95 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/blob_store.py` | 96 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/blob_store.py` | 108 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/blob_store.py` | 109 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/blob_store.py` | 120 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/blob_store.py` | 121 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/cache.py` | 52 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/cache.py` | 59 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/cache.py` | 66 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/cache.py` | 74 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/cache.py` | 75 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/cache.py` | 82 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/cache.py` | 91 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/cache.py` | 92 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/cache.py` | 100 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/cache.py` | 109 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/cache.py` | 118 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/cache.py` | 131 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/database.py` | 50 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/database.py` | 51 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/database.py` | 63 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/database.py` | 72 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/database.py` | 100 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/database.py` | 102 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/database.py` | 126 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/distributed_lock.py` | 36 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/distributed_lock.py` | 45 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/distributed_lock.py` | 52 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/distributed_lock.py` | 61 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/distributed_lock.py` | 70 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/distributed_lock.py` | 80 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/distributed_lock.py` | 88 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/distributed_lock.py` | 89 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/distributed_lock.py` | 97 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/distributed_lock.py` | 105 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/distributed_lock.py` | 112 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/event_bus.py` | 69 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/event_bus.py` | 70 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/event_bus.py` | 87 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/event_bus.py` | 107 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/event_bus.py` | 108 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/event_bus.py` | 126 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/flags.py` | 72 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/flags.py` | 83 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/flags.py` | 93 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/flags.py` | 100 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/flags.py` | 108 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/flags.py` | 120 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/flags.py` | 125 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/middleware.py` | 77 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/middleware.py` | 96 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/middleware.py` | 133 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/middleware.py` | 138 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/notification.py` | 65 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/notification.py` | 73 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/notification.py` | 75 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/notification.py` | 76 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/notification.py` | 89 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/notification.py` | 98 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/notification.py` | 108 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/notification.py` | 115 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/notification.py` | 116 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/queue_backend.py` | 41 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/queue_backend.py` | 42 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/queue_backend.py` | 51 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/queue_backend.py` | 58 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/queue_backend.py` | 66 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/queue_backend.py` | 75 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/queue_backend.py` | 78 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/queue_backend.py` | 86 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/queue_backend.py` | 89 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/repository.py` | 68 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/repository.py` | 69 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/search.py` | 125 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/search.py` | 138 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/search.py` | 139 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 73 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 79 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 86 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 93 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 106 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 114 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 115 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 116 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 125 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 134 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 143 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 150 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 158 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 159 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 164 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 170 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/secrets.py` | 171 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 87 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 97 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 98 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 107 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 121 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 145 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 150 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 151 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 162 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 167 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 187 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 190 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 192 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 206 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/task_queue.py` | 207 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/vector_store.py` | 98 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/vector_store.py` | 99 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/vector_store.py` | 106 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/vector_store.py` | 116 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/vector_store.py` | 127 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/vector_store.py` | 133 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/vector_store.py` | 145 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/vector_store.py` | 147 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/vector_store.py` | 162 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/vector_store.py` | 163 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/vector_store.py` | 178 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/vector_store.py` | 179 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/vector_store.py` | 195 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 111 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 112 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 113 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 120 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 133 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 135 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 147 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 148 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 155 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 177 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 178 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 192 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 243 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 244 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 245 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 256 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 263 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 264 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 285 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 293 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 307 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 323 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 324 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 338 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 345 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/compliance/webhook.py` | 346 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/lib/admin_helpers.py` | 142 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/lib/admin_helpers.py` | 157 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/lib/admin_helpers.py` | 170 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/lib/admin_helpers.py` | 179 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/lib/assertions.py` | 30 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/lib/assertions.py` | 72 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/lib/assertions.py` | 74 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/testkit/assertions.py` | 40 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/testkit/assertions.py` | 56 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/testkit/assertions.py` | 74 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/testkit/assertions.py` | 95 | `S101` | Use of `assert` detected |
| `lexigram-testing/src/lexigram/testing/websocket/client.py` | 98 | `S101` | Use of `assert` detected |
| `lexigram-web/src/lexigram/web/security/csrf/middleware.py` | 43 | `S105` | Possible hardcoded password assigned to: "_TOKEN_ISSUER" |
| `lexigram-web/src/lexigram/web/security/csrf/middleware.py` | 147 | `S101` | Use of `assert` detected |
| `lexigram-workflow/src/lexigram/workflow/bulk/operation.py` | 179 | `S101` | Use of `assert` detected |
| `lexigram-workflow/src/lexigram/workflow/execution/runner.py` | 102 | `S101` | Use of `assert` detected |
| `lexigram-workflow/src/lexigram/workflow/state/machine.py` | 152 | `S101` | Use of `assert` detected |
| `lexigram/src/lexigram/concurrency/executors/dispatcher.py` | 175 | `S101` | Use of `assert` detected |
| `lexigram/src/lexigram/concurrency/executors/dispatcher.py` | 182 | `S101` | Use of `assert` detected |
| `lexigram/src/lexigram/middleware/builtins/validation.py` | 41 | `S101` | Use of `assert` detected |
| `lexigram/src/lexigram/saga/base.py` | 225 | `S101` | Use of `assert` detected |

### Verification Notes

All 305 verified low-risk findings were closed on 2026-08-19 by deep re-verification of every site:

- **S608** (SQL injection, 221 sites): every site re-verified individually. Nine genuine issues fixed: `index_many` index sanitization on the Postgres/MySQL backends, identifier validation at construction for `PostgresFTSQuery`/`MySQLFTSQuery` (table and columns), `Column()` quoting for `batch_processor` record keys, and a collection-name allowlist in `BaseVectorCollection` (prevents quoted-identifier breakout in pgvector SQL). All remaining sites are `# noqa: S608`-annotated with per-site justification: config-only identifiers, allowlisted sanitizers (`_sanitize_index_name`, `_quote_identifier`, `_FIELD_NAME_RE`, `_safe_filter_key`), fixed condition strings, or parameterized values.
- **S110** (except-pass, 41 sites): intentional non-fatal fallbacks; every site annotated with its justification.
- **S311** (pseudo-random, 16 sites): retry/TTL jitter, backoff, sampling, and mock vectors — no security context; annotated.
- **S603** (subprocess, 10 sites): nine operator CLI tooling sites annotated (argv lists, no shell); one genuine fix — `lexigram-cli` MCP self-invocation switched from `sys.argv[0]` to `sys.executable -m lexigram.cli.runtime.main` (argv[0] independence).
- **S607/S104/S704/S701** (17 sites): static PATH tools invoked by the operator, `0.0.0.0` dev-server config defaults, trusted framework HTML composition, and trusted CLI scaffold templates — all annotated with per-site justification.

## Framework Security Rules

| File | Line | Rule ID | Severity | Message |
|------|------|---------|----------|---------|
| `lexigram-auth/src/lexigram/auth/authn/_jwt_lifecycle.py` | 214 | `sec-jwt-verification-disabled` | `important` | lexigram-auth/src/lexigram/auth/authn/_jwt_lifecycle.py disables JWT signature verification via options (explicit dev-only opt-in gate). |

## Audit Tracker Status

- Total areas: 99
- Done: 99
- Open: 0

## Verified-Clean Surfaces

- `lexigram-testing`'s fakes — reviewed and confirmed clean; no findings.
- `lexigram-ai-evaluation` — confirmed no LLM-as-judge or prompt-injection surface exists in this package (a plausible-sounding risk that turned out not to apply here).
- `lexigram-queue`'s Kafka/SQS/Azure Service Bus/GCP Pub/Sub backends — all implement proper `max_in_flight`-based backpressure with per-message task isolation (contrast §72/§73, which are specific to the in-memory default and Redis backend).
- `lexigram-workflow`'s dynamic-code-execution and checkpoint-deserialization surfaces — reviewed, clean (contrast §79, which is a narrower SQL-interpolation issue in one query method, not a deserialization/eval risk).
- Fernet encryption usage and JSON-only serialization — confirmed consistent and correct across all 9 packages swept this round.
- Dependency hygiene (2026-08-18): `python-jose`/`ecdsa` removed from the tree (CVE-2024-23342 Minerva timing attack, no upstream fix; pip-audit clean after removal). Only runtime call site was the diagnostic `get_unverified_header()` in `lexigram-admin/.../guards.py` — replaced with a stdlib base64url header decode; auth test token minting switched to `pyjwt` (already a dependency).

## Open Risk Table

| # | Area | Severity mix |
|---|------|--------------|
| - | (none) | - |

