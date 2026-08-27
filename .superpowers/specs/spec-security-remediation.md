# Spec: Security Remediation Program

**Status:** approved · **Date:** 2026-08-22
**Source:** full-repo security audit (5 domains, all findings verified by reading code)
**Plans:** `2026-08-22-security-criticals-plan.md` · `2026-08-22-outbound-safety-plan.md` ·
`2026-08-22-secrets-logging-plan.md` · `2026-08-22-medium-hardening-plan.md`

## Decisions (defaults taken; override before execution)

| Decision | Choice |
|---|---|
| Scope | All phases planned; Phase 1 lands first |
| CSRF fail-closed | Yes — breaking for any consumer relying on missing session tokens; admin-only surface |
| Tenant scoping | Enforced only when multitenancy enabled; single-tenant deployments unaffected (`enforce_scoping` flag) |
| JWT `aud` | Mint at creation immediately; verification stays config-gated (no outstanding-token invalidation) |
| Dependencies (#7) | Visibility-only this round (audit coverage), version bumps are separate effort |
| Commits | One commit per finding with its regression tests |

## Findings inventory (all verified)

### Critical / High
1. **CSRF guard fails open** when session lacks `csrf_token`; plain `!=` compare bypassing `AdminCsrfService.validate_token()` — `admin/auth/guards.py:437-440,461`
2. **Mass-assignment**: controller default `validate_create/update` return raw form dicts into INSERT/UPDATE; bulk import maps verbatim; memory adapter does arbitrary `setattr` — `controllers/resource/mutation.py:37-133`, `services/import_/service.py:224,416`, `data/adapters/memory_adapter.py:118-122`. Note: `Resource.before_validate` already coerces+validates but is never called by the defaults, and `_coerce_form_data` passes unknown keys through.
3. **Tenant identity client-controlled** (`X-Tenant-Id` header / `admin_tenant` cookie trusted verbatim) + repository data source has zero tenant scoping — `admin/multitenancy/adapter.py:181-194`, `data/adapters/repository/data_source.py:28-70`
4. **SSRF via auto-followed redirects**: `_assert_url_safe()` validates initial URL only; aiohttp session follows redirects unvalidated — `http/client/http_client.py:260-287`, `pool/connection_pool.py:79-87`
5. **Log redaction exact-key match** misses compound keys (`auth_token`, `dsn`, `apiKey`, `secret_key`…) — `logging/redaction.py:78`
6. **Sentry without `before_send` scrubber** — `monitor/error_tracking.py:82-87`
7. **CI pip-audit blind to override-pinned ML stack** — `ci.yml:241-244`; multimedia extras pins

### Medium
8. Stored SSRF: gateway channel `upstream_base_url` accepted from admin form unvalidated and persisted — `relay-gateway/admin/actions.py:148-187`
9. DNS-rebinding TOCTOU in `url_safety` primitive (resolve-at-check vs connect-time) — `contracts/security/url_safety.py:52-115`
10. JWT: `aud` never minted; `verify_aud=False` without configured audience; type-less token gains refresh rights — `auth/authn/_jwt_creation.py:72-85`, `_jwt_lifecycle.py:243-279`
11. Open redirect via `Referer` in tenancy switch; tenancy switch cookie lacks `Secure` — `admin/controllers/tenancy.py:78-85`
12. Staging skips insecure-secret validator; pairs with lax/non-Secure cookies — `admin/config.py:365-372`, `_cookie_config.py:26-30`
13. Identifier interpolation: pgvector `DROP TABLE IF EXISTS "{name}"` (`vector/backends/pgvector/backend.py:89-109`), savepoint names into SQL (`sql/providers/transaction_manager.py:117-135`, `unit_of_work/simple.py:535-564`), `CREATE DATABASE "{db}"` (`postgres_provider.py:78`)
14. `SecretStr` gaps: notification drivers (`auth_token`, FCM `server_key`, APNs PEM, VAPID private key, SMTP password), web CSRF `secret_key`, admin `setup_token`, monitor DSN

### Low
15. Codegen name path traversal/content injection — `codegen/base.py:132-136,47-67` + web/cli generators sinks
16. ai-llm client has no SSRF gate (config-sourced URLs today)
17. uploads pipeline containment opt-in (`base_dir=None`)
18. Slack notifier unpinned host + follows redirects
19. Plain Jinja env for prompt rendering (SSTI if templates become user-editable)

## Verified clean (no work)

SQL parameterization with fail-closed `Table()`/`Column()` identifiers; no pickle/yaml.load/shell=True in src; open-redirect `next` handling solid with tests; no tracked secret files; AI provider keys already `SecretStr`; Sentry PII off; rich-text sanitized via nh3.

## Phase map

| Phase | Plan | Findings |
|---|---|---|
| 1 Criticals | security-criticals-plan | 1, 2, 3 |
| 2 Outbound safety | outbound-safety-plan | 4, 8, 9 |
| 3 Secrets/logging | secrets-logging-plan | 5, 6, 14 |
| 4 Medium hardening | medium-hardening-plan | 10, 11, 12, 13, 15 (+16-19 backlog) |
| 5 Deps visibility | inside master spec §Phase 5 | 7 |

## Global constraints (apply to every plan)

- Narrow test runs per AGENTS.md §3.4: file-scoped, `-m "not integration" --no-cov`.
- Gates before each commit: `uv run ruff check <paths>` + `uv run ruff format --check <paths>`; mypy on touched src dirs where the package is typed.
- Emoji pathspec commits (`git add -f` new files first); never sweep other lanes' dirt.
- Every fix ships its adversarial regression test in the same commit.
- No compat shims; update in-repo consumers to real homes.
