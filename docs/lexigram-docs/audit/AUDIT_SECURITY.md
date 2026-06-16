# AUDIT_SECURITY.md — Lexigram Framework Security Audit

> **Source**: Live command evidence (pip-audit, ruff bandit rules), framework security rules, and the audit tracker (`docs/AUDIT_TRACKER.md`).

---

## Summary

- Verdict: **CRITICAL** — a critical framework security rule fired
- Dependency scan: failed
- SAST (ruff `S` rules): 606 finding(s) (303 high-signal)
- Framework security rules: 5 finding(s)
- Tracker areas: 84 total, 54 done

## Dependency Scan

- Command: `uv pip audit`
- Exit code: `2`
- Duration: `7 ms`
- Summary: `For more information, try '--help'.`

```text
error: unrecognized subcommand 'audit'

Usage: uv pip [OPTIONS] <COMMAND>

For more information, try '--help'.
```

## Static Analysis (ruff bandit rules)

- Exit code: `1`

### Findings

| File | Line | Rule | Message |
|------|------|------|---------|
| `lexigram-admin/src/lexigram/admin/auth/store/audit_log_sql.py` | 220 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/email_otp_sql.py` | 95 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/email_otp_sql.py` | 103 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/email_otp_sql.py` | 120 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/email_verification_sql.py` | 99 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/email_verification_sql.py` | 116 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/email_verification_sql.py` | 136 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/email_verification_sql.py` | 150 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/email_verification_sql.py` | 171 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/lockout_sql.py` | 154 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/lockout_sql.py` | 218 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/lockout_sql.py` | 260 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/login_attempt_sql.py` | 160 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/login_attempt_sql.py` | 188 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/mfa_sql.py` | 107 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/mfa_sql.py` | 139 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/mfa_sql.py` | 152 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/password_reset_token_sql.py` | 93 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/password_reset_token_sql.py` | 100 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/password_reset_token_sql.py` | 127 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/session_sql.py` | 83 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/session_sql.py` | 98 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/session_sql.py` | 188 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/session_sql.py` | 212 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/session_sql.py` | 226 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/session_sql.py` | 236 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/auth/store/session_sql.py` | 248 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/controllers/base.py` | 146 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-admin/src/lexigram/admin/controllers/base.py` | 165 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-admin/src/lexigram/admin/controllers/resource.py` | 484 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-admin/src/lexigram/admin/dashboard/route_integrator.py` | 258 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-admin/src/lexigram/admin/dashboard/route_integrator.py` | 296 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-admin/src/lexigram/admin/dashboard/route_integrator.py` | 325 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `lexigram-admin/src/lexigram/admin/dashboard/route_integrator.py` | 450 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-admin/src/lexigram/admin/data/data_source.py` | 238 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/data/data_source.py` | 251 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/data/data_source.py` | 252 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/data/data_source.py` | 295 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/data/data_source.py` | 329 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/data/data_source.py` | 345 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/engine/renderer.py` | 156 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-admin/src/lexigram/admin/events/adapter.py` | 36 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-admin/src/lexigram/admin/media/library.py` | 271 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-admin/src/lexigram/admin/rbac/roles_sql.py` | 94 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/rbac/roles_sql.py` | 102 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/rbac/roles_sql.py` | 111 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/rbac/roles_sql.py` | 124 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/rbac/roles_sql.py` | 138 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/resources/handler.py` | 121 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-admin/src/lexigram/admin/resources/handler.py` | 451 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-admin/src/lexigram/admin/services/collaborative.py` | 450 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-admin/src/lexigram/admin/services/search_service.py` | 163 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-admin/src/lexigram/admin/services/settings_service.py` | 80 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/services/settings_service.py` | 91 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/services/settings_service.py` | 105 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-admin/src/lexigram/admin/state/context.py` | 202 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-admin/src/lexigram/admin/ui/layouts/admin_layout.py` | 426 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `lexigram-admin/src/lexigram/admin/ui/layouts/standalone_layout.py` | 255 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `lexigram-ai-governance/src/lexigram/ai/governance/audit/database.py` | 138 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-ai-governance/src/lexigram/ai/governance/audit/database.py` | 164 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-ai-governance/src/lexigram/ai/governance/audit/database.py` | 181 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-ai-governance/src/lexigram/ai/governance/audit/database.py` | 189 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-ai-governance/src/lexigram/ai/governance/audit/database.py` | 197 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-ai-governance/src/lexigram/ai/governance/relay_billing/persistence.py` | 305 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-ai-llm/src/lexigram/ai/llm/audit_bridge.py` | 57 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-ai-llm/src/lexigram/ai/llm/embedding/cohere.py` | 66 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-ai-llm/src/lexigram/ai/llm/embedding/jina.py` | 68 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-ai-llm/src/lexigram/ai/llm/embedding/local.py` | 73 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-ai-llm/src/lexigram/ai/llm/embedding/openai.py` | 73 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-ai-llm/src/lexigram/ai/llm/embedding/voyage.py` | 66 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py` | 146 | `S104` | Possible binding to all interfaces |
| `lexigram-ai-mcp/src/lexigram/ai/mcp/connectors/sql.py` | 266 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-ai-mcp/src/lexigram/ai/mcp/connectors/sql.py` | 324 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-ai-mcp/src/lexigram/ai/mcp/resources/database.py` | 126 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-ai-mcp/src/lexigram/ai/mcp/resources/database.py` | 136 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-ai-prompt/src/lexigram/ai/prompt/optimization/optimizer.py` | 170 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-audit/src/lexigram/audit/admin/contributor.py` | 89 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-audit/src/lexigram/audit/store/sql.py` | 148 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-audit/src/lexigram/audit/store/sql.py` | 188 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-audit/src/lexigram/audit/store/sql.py` | 211 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-audit/src/lexigram/audit/verification/backfill.py` | 52 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-audit/src/lexigram/audit/verification/backfill.py` | 82 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-auth/src/lexigram/auth/storage/apikey_sql.py` | 63 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-auth/src/lexigram/auth/storage/apikey_sql.py` | 75 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-auth/src/lexigram/auth/storage/apikey_sql.py` | 88 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-auth/src/lexigram/auth/storage/apikey_sql.py` | 103 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-cache/src/lexigram/cache/service/core.py` | 161 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-cache/src/lexigram/cache/service/stampede.py` | 237 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-cache/src/lexigram/cache/service/stampede.py` | 269 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-cli/src/lexigram/cli/commands/db.py` | 580 | `S603` | `subprocess` call: check for execution of untrusted input |
| `lexigram-cli/src/lexigram/cli/commands/db.py` | 636 | `S603` | `subprocess` call: check for execution of untrusted input |
| `lexigram-cli/src/lexigram/cli/commands/dev.py` | 103 | `S104` | Possible binding to all interfaces |
| `lexigram-cli/src/lexigram/cli/commands/new.py` | 21 | `S701` | By default, jinja2 sets `autoescape` to `False`. Consider using `autoescape=True` or the `select_autoescape` function to mitigate XSS vulnerabilities. |
| `lexigram-cli/src/lexigram/cli/commands/run.py` | 156 | `S603` | `subprocess` call: check for execution of untrusted input |
| `lexigram-cli/src/lexigram/cli/lib/templates.py` | 13 | `S701` | By default, jinja2 sets `autoescape` to `False`. Consider using `autoescape=True` or the `select_autoescape` function to mitigate XSS vulnerabilities. |
| `lexigram-cli/src/lexigram/cli/registry/database.py` | 492 | `S603` | `subprocess` call: check for execution of untrusted input |
| `lexigram-cli/src/lexigram/cli/registry/health.py` | 317 | `S607` | Starting a process with a partial executable path |
| `lexigram-cli/src/lexigram/cli/registry/health.py` | 357 | `S607` | Starting a process with a partial executable path |
| `lexigram-cli/src/lexigram/cli/registry/presets.py` | 43 | `S104` | Possible binding to all interfaces |
| `lexigram-cli/src/lexigram/cli/registry/presets.py` | 63 | `S104` | Possible binding to all interfaces |
| `lexigram-cli/src/lexigram/cli/registry/presets.py` | 112 | `S104` | Possible binding to all interfaces |
| `lexigram-cli/src/lexigram/cli/registry/provider.py` | 381 | `S104` | Possible binding to all interfaces |
| `lexigram-cli/src/lexigram/cli/registry/provider.py` | 544 | `S603` | `subprocess` call: check for execution of untrusted input |
| `lexigram-cli/src/lexigram/cli/registry/provider.py` | 545 | `S607` | Starting a process with a partial executable path |
| `lexigram-cli/src/lexigram/cli/registry/server.py` | 284 | `S603` | `subprocess` call: check for execution of untrusted input |
| `lexigram-cli/src/lexigram/cli/registry/server.py` | 297 | `S603` | `subprocess` call: check for execution of untrusted input |
| `lexigram-cli/src/lexigram/cli/registry/task.py` | 70 | `S603` | `subprocess` call: check for execution of untrusted input |
| `lexigram-cli/src/lexigram/cli/registry/task.py` | 111 | `S603` | `subprocess` call: check for execution of untrusted input |
| `lexigram-cli/src/lexigram/cli/registry/task.py` | 149 | `S603` | `subprocess` call: check for execution of untrusted input |
| `lexigram-cli/src/lexigram/cli/registry/version.py` | 60 | `S607` | Starting a process with a partial executable path |
| `lexigram-events/src/lexigram/events/middleware/retry.py` | 81 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-events/src/lexigram/events/stores/checkpoints.py` | 24 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/checkpoints.py` | 30 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/checkpoints.py` | 48 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/checkpoints.py` | 56 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/checkpoints.py` | 72 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/checkpoints.py` | 76 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/checkpoints.py` | 88 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/checkpoints.py` | 92 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/checkpoints.py` | 104 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/checkpoints.py` | 119 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/checkpoints.py` | 125 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/checkpoints.py` | 143 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/checkpoints.py` | 149 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/database_bridge.py` | 50 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/database_bridge.py` | 77 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/database_bridge.py` | 121 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/database_bridge.py` | 154 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/database_bridge.py` | 172 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/idempotency.py` | 27 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/idempotency.py` | 33 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/idempotency.py` | 57 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/idempotency.py` | 64 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/idempotency.py` | 78 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/idempotency.py` | 88 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/outbox.py` | 120 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/outbox.py` | 126 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/outbox.py` | 263 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/outbox.py` | 290 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/outbox.py` | 304 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/outbox.py` | 333 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/postgres/event_store.py` | 148 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/postgres/event_store.py` | 262 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/postgres/event_store.py` | 267 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/postgres/event_store.py` | 336 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 65 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 76 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 91 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 99 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 110 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 123 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 134 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 146 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 151 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 155 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 162 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 170 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 178 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 188 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 196 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-events/src/lexigram/events/stores/sqlite/queries.py` | 204 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-graphql/src/lexigram/graphql/di/provider.py` | 223 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-http/src/lexigram/http/client/http_client.py` | 102 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-http/src/lexigram/http/di/provider.py` | 85 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-http/src/lexigram/http/di/provider.py` | 95 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-http/src/lexigram/http/di/provider.py` | 100 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-http/src/lexigram/http/retry/policy.py` | 36 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-monitor/src/lexigram/monitor/backends/db_exporter.py` | 103 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-monitor/src/lexigram/monitor/scheduling/scheduled_worker.py` | 131 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-multimedia-image/src/lexigram/multimedia/image/providers/comfyui.py` | 181 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-multimedia-video/src/lexigram/multimedia/video/providers/comfyui.py` | 198 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-queue/src/lexigram/queue/admin/pages/overview.py` | 34 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-search/src/lexigram/search/backends/mysql/backend.py` | 130 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/mysql/backend.py` | 195 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/mysql/backend.py` | 213 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/mysql/backend.py` | 240 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/postgres/backend.py` | 123 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/postgres/backend.py` | 199 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/postgres/backend.py` | 217 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/postgres/backend.py` | 246 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/postgres/backend.py` | 304 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/postgres/backend.py` | 326 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/sqlite/backend.py` | 68 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/sqlite/backend.py` | 96 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/sqlite/backend.py` | 143 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/sqlite/backend.py` | 221 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/sqlite/backend.py` | 240 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/sqlite/schema.py` | 46 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/sqlite/schema.py` | 53 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/sqlite/schema.py` | 60 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/sqlite/schema.py` | 85 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/sqlite/schema.py` | 94 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/sqlite/schema.py` | 106 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/sqlite/schema.py` | 119 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/sqlite/schema.py` | 134 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/sqlite/schema.py` | 144 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-search/src/lexigram/search/backends/translate.py` | 180 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/backends/sqlite.py` | 444 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-sql/src/lexigram/sql/backup/backup_manager.py` | 128 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/backup/backup_manager.py` | 170 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/backup/backup_manager.py` | 303 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/backup/backup_manager.py` | 314 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/backup/backup_manager.py` | 446 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/di/provider.py` | 130 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-sql/src/lexigram/sql/di/provider.py` | 142 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-sql/src/lexigram/sql/di/provider.py` | 154 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-sql/src/lexigram/sql/logging/loggers.py` | 88 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-sql/src/lexigram/sql/outbox/store.py` | 51 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/outbox/store.py` | 65 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/outbox/store.py` | 74 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/outbox/store.py` | 81 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/performance/batch_processor.py` | 199 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/providers/_connection_mixin.py` | 270 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-sql/src/lexigram/sql/providers/crud_operations.py` | 123 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/providers/crud_operations.py` | 158 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/providers/crud_operations.py` | 190 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/providers/schema_manager.py` | 51 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/query/_sql_build_mixin.py` | 87 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/query/_sql_build_mixin.py` | 173 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/query/_sql_build_mixin.py` | 214 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/query/_sql_build_mixin.py` | 233 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/_advanced_mixin.py` | 91 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/_advanced_mixin.py` | 149 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/_advanced_mixin.py` | 187 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/_advanced_mixin.py` | 230 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/_read_mixin.py` | 45 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/_read_mixin.py` | 103 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/_read_mixin.py` | 190 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/_read_mixin.py` | 240 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/_read_mixin.py` | 284 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/_write_mixin.py` | 153 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/_write_mixin.py` | 216 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/_write_mixin.py` | 294 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/_write_mixin.py` | 369 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/append_log.py` | 80 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/append_log.py` | 105 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/append_log.py` | 152 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/append_log.py` | 185 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/append_log.py` | 198 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/append_log.py` | 211 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/append_log.py` | 214 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/repositories/base.py` | 177 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/resilience/core.py` | 225 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `lexigram-sql/src/lexigram/sql/search/full_text.py` | 134 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/search/full_text.py` | 209 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/storage/postgres.py` | 82 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/storage/postgres.py` | 110 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/storage/postgres.py` | 125 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/storage/postgres.py` | 141 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/storage/postgres.py` | 148 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/storage/postgres.py` | 160 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/storage/postgres.py` | 166 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/locks.py` | 99 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/locks.py` | 115 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/locks.py` | 124 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/locks.py` | 152 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/locks.py` | 182 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/secrets.py` | 74 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/secrets.py` | 97 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/secrets.py` | 110 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/secrets.py` | 127 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/state.py` | 80 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/state.py` | 109 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/state.py` | 121 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/state.py` | 138 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/state.py` | 162 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/state.py` | 199 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-sql/src/lexigram/sql/stores/state.py` | 211 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-tasks/src/lexigram/tasks/backends/postgres.py` | 111 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-tasks/src/lexigram/tasks/backends/postgres.py` | 140 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-tasks/src/lexigram/tasks/backends/postgres.py` | 179 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-tasks/src/lexigram/tasks/backends/postgres.py` | 198 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-tasks/src/lexigram/tasks/backends/postgres.py` | 229 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-tasks/src/lexigram/tasks/backends/postgres.py` | 240 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-tasks/src/lexigram/tasks/backends/postgres.py` | 275 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-tasks/src/lexigram/tasks/backends/postgres.py` | 292 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-tasks/src/lexigram/tasks/backends/postgres.py` | 307 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-tasks/src/lexigram/tasks/di/provider.py` | 385 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-tasks/src/lexigram/tasks/di/provider.py` | 490 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-tasks/src/lexigram/tasks/scheduled_worker.py` | 155 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-tenancy/src/lexigram/tenancy/integration/sql_bridge.py` | 71 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-tenancy/src/lexigram/tenancy/integration/sql_bridge.py` | 81 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-tenancy/src/lexigram/tenancy/migration/saga.py` | 265 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-testing/src/lexigram/testing/lib/admin_helpers.py` | 197 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-testing/src/lexigram/testing/lib/admin_helpers.py` | 204 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-ui/src/lexigram/ui/layouts/html_document.py` | 66 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `lexigram-vector/src/lexigram/vector/backends/pgvector/collection.py` | 42 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-vector/src/lexigram/vector/backends/pgvector/collection.py` | 91 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-vector/src/lexigram/vector/backends/pgvector/collection.py` | 101 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-vector/src/lexigram/vector/backends/pgvector/collection.py` | 124 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-vector/src/lexigram/vector/backends/pgvector/collection.py` | 157 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-web/src/lexigram/web/constants.py` | 21 | `S104` | Possible binding to all interfaces |
| `lexigram-web/src/lexigram/web/errors/html_error_renderer.py` | 182 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-web/src/lexigram/web/routing/health.py` | 77 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-web/src/lexigram/web/routing/health.py` | 83 | `S110` | `try`-`except`-`pass` detected, consider logging the exception |
| `lexigram-webhook/src/lexigram/webhook/store/sql.py` | 171 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-webhook/src/lexigram/webhook/store/sql.py` | 338 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-workflow/src/lexigram/workflow/checkpoint/store_database.py` | 86 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-workflow/src/lexigram/workflow/checkpoint/store_database.py` | 111 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-workflow/src/lexigram/workflow/checkpoint/store_database.py` | 147 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-workflow/src/lexigram/workflow/state/persistence.py` | 99 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram-workflow/src/lexigram/workflow/state/persistence.py` | 124 | `S608` | Possible SQL injection vector through string-based query construction |
| `lexigram/src/lexigram/middleware/builtins/resilience.py` | 70 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |

### Low-Signal Rules (S101 asserts, S105/S106 hardcoded strings)

- Count: 303

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
| `lexigram-ai-workers/src/lexigram/ai/workers/dlq/worker.py` | 489 | `S101` | Use of `assert` detected |
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

## Framework Security Rules

| File | Line | Rule ID | Severity | Message |
|------|------|---------|----------|---------|
| `lexigram-auth/src/lexigram/auth/authn/_jwt_lifecycle.py` | 214 | `sec-jwt-verification-disabled` | `critical` | lexigram-auth/src/lexigram/auth/authn/_jwt_lifecycle.py disables JWT signature verification via options. |
| `lexigram-auth/src/lexigram/auth/authn/_jwt_lifecycle.py` | 404 | `sec-jwt-verification-disabled` | `critical` | lexigram-auth/src/lexigram/auth/authn/_jwt_lifecycle.py disables JWT signature verification via options. |
| `lexigram-auth/src/lexigram/auth/authn/_jwt_lifecycle.py` | 480 | `sec-jwt-verification-disabled` | `critical` | lexigram-auth/src/lexigram/auth/authn/_jwt_lifecycle.py disables JWT signature verification via options. |
| `lexigram-auth/src/lexigram/auth/authn/blacklist.py` | 94 | `sec-jwt-verification-disabled` | `critical` | lexigram-auth/src/lexigram/auth/authn/blacklist.py disables JWT signature verification via options. |
| `lexigram-auth/src/lexigram/auth/authn/blacklist.py` | 201 | `sec-jwt-verification-disabled` | `critical` | lexigram-auth/src/lexigram/auth/authn/blacklist.py disables JWT signature verification via options. |

## Audit Tracker Status

- Total areas: 84
- Done: 54
- Open: 30
- Open severity mix: High ×4, Low ×4, Med ×5

## Verified-Clean Surfaces

- `lexigram-testing`'s fakes — reviewed and confirmed clean; no findings.
- `lexigram-ai-evaluation` — confirmed no LLM-as-judge or prompt-injection surface exists in this package (a plausible-sounding risk that turned out not to apply here).
- `lexigram-queue`'s Kafka/SQS/Azure Service Bus/GCP Pub/Sub backends — all implement proper `max_in_flight`-based backpressure with per-message task isolation (contrast §72/§73, which are specific to the in-memory default and Redis backend).
- `lexigram-workflow`'s dynamic-code-execution and checkpoint-deserialization surfaces — reviewed, clean (contrast §79, which is a narrower SQL-interpolation issue in one query method, not a deserialization/eval risk).
- Fernet encryption usage and JSON-only serialization — confirmed consistent and correct across all 9 packages swept this round.

## Open Risk Table

| # | Area | Severity mix |
|---|------|--------------|
| 40 | **Meilisearch/Typesense filter-expression injection** (`lexigram-search/backends/filters.py`) | High ×1 |
| 50 | **`lexigram-ai-governance` Redis persistence silently fails open, disabling budget/RPM enforcement** | High ×1 |
| 51 | **`lexigram-ai-governance` → `lexigram-tasks` cross-extension import** | Low ×1 |
| 52 | **`lexigram-ai-observability` trace spans carry unredacted tool/agent/retriever payloads** | Med ×1 |
| 53 | **`lexigram-ai-workers` document-ingestion accepts unvalidated file paths (traversal / arbitrary read)** | High ×1 |
| 54 | **`lexigram-ai-prompt` `max_variable_length` config flag is defined but never enforced** | Low ×1 |
| 55 | **`lexigram-features` empty `user_attributes` rule fails open (enabled=True for everyone)** | Low/Med ×1 |
| 56 | **`lexigram-monitor` `/health`+`/metrics` unauthenticated, and health checks may leak raw exception strings** | Med ×2 |
| 57 | **`lexigram-monitor` still hard-depends on `lexigram-tasks` at the packaging level** | Low ×1 |
| 58 | **`lexigram-resilience` `throttle()` decorator is structurally dead — every call raises** | Med ×1 |
| 59 | **`lexigram-resilience` idempotency fails open on store outage, and two `unwrap()`-without-guard sites can defeat even that fallback** | Med-High ×1 |
| 60 | **`lexigram-resilience` database idempotency store's "dialect-aware" placeholder is hardcoded to `?`, breaking Postgres — deeper than reported (naive `.replace()` also can't produce sequential `$1,$2,...` for multi-param queries)** | Low ×1 |
| 61 | lexigram-ai | High |
| 62 | lexigram-ai-evaluation | Medium |
| 63 | lexigram-ai-feedback | Medium |
| 64 | lexigram-ai-feedback | High |
| 65 | lexigram-ai-feedback | Medium |
| 66 | lexigram-audit | Critical |
| 67 | lexigram-audit | High |
| 68 | lexigram-audit | Medium |
| 69 | lexigram-events | Critical |
| 70 | lexigram-events | High |
| 71 | lexigram-events | Medium |
| 72 | lexigram-queue | High |
| 73 | lexigram-queue | High |
| 74 | lexigram-queue | High |
| 75 | lexigram-queue | Low |
| 76 | lexigram-tasks | High |
| 77 | lexigram-tasks | Medium |
| 79 | lexigram-workflow | Medium |

