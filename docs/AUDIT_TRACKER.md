# Security Audit — Implementation Tracker

**Generated:** 2026-08-16
**Source:** `docs/superpowers/specs/2026-08-16-security-architecture-audit-findings.md`
**Process:** verify → spec → plan → execute → two-pass review

Status of all 15 security remediation areas across audit Rounds 1-3.
Round 3 (§6 below) added 5 more areas; specs + plans for those were
written 2026-08-16, none executed yet. Round 1-2: nothing executed except
Plugins (in progress).

---

## Status Legend

| Mark | Meaning |
|------|---------|
| `[ ]` | Not started |
| `[~]` | In progress |
| `[x]` | Done |
| `(s)` | Blocked on sign-off — see §2 |

---

## 1. Area Summary

| # | Area | Severity mix | Spec | Plan | Status |
|---|------|--------------|------|------|--------|
| 1 | **P0 session-secret** | Critical ×3 | `specs/2026-08-16-security-p0-session-secret-design.md` | `plans/2026-08-16-security-p0-session-secret.md` | Not started |
| 2 | **SQL injection** | Critical ×2, High ×2, Med ×2, Low ×2 | `specs/2026-08-16-security-sql-injection-design.md` | `plans/2026-08-16-security-sql-injection.md` | Not started |
| 3 | **Tenancy isolation** | Critical ×2, High ×2, Med ×2 | `specs/2026-08-16-security-tenancy-design.md` | `plans/2026-08-16-security-tenancy.md` | Not started (s) |
| 4 | **XSS / output rendering** | Critical ×2, High ×5, Med ×1 | `specs/2026-08-16-security-xss-render-design.md` | `plans/2026-08-16-security-xss-render.md` | Not started |
| 5 | **Auth / hashers** | Critical ×1, High ×3 | `specs/2026-08-16-security-auth-hashers-design.md` | `plans/2026-08-16-security-auth-hashers.md` | Not started (s) |
| 6 | **Web CSRF / headers** | High ×5, Med ×3 | `specs/2026-08-16-security-web-csrf-design.md` | `plans/2026-08-16-security-web-csrf.md` | Not started (s) |
| 7 | **Secrets / credentials** | Critical ×1, High ×3, Med ×2, Low ×2 | `specs/2026-08-16-security-secrets-design.md` | `plans/2026-08-16-security-secrets.md` | Not started (s) |
| 8 | **SSRF / outbound** | Critical ×2, High ×1, Med ×1 | `specs/2026-08-16-security-ssrf-design.md` | `plans/2026-08-16-security-ssrf.md` | Not started |
| 9 | **Deserialization / code-exec** | High ×1, Med ×2, Low ×2 | `specs/2026-08-16-security-deserialization-design.md` | `plans/2026-08-16-security-deserialization.md` | Not started (s) |
| 10 | **Plugins** | Low ×5 | `specs/2026-08-16-security-plugins-design.md` | `plans/2026-08-16-security-plugins.md` | In progress (`[~]` §3.10) |

**Recommended execution order (audit §0):** 1 (P0) → 2 (SQLi) → 8 (SSRF) → 4 (XSS) → 6 (Web CSRF) → 5 (Auth) → 7 (Secrets) → 3 (Tenancy) → 9 (Deserialization) → 10 (Plugins).

**Cross-extension constraint (tenancy B3):** `lexigram-sql` and `lexigram-tenancy` changes from the tenancy plan must merge together before the fail-closed raise lands.

---

## 2. Open Decisions — Pending Sign-off

Every spec §4 marks options as `RECOMMENDED — pending sign-off`. Mark the
decision block `[x]` once signed off; a plan remains `(s)` until then.

- [ ] **Tenancy O1 / plan B1** — identity-bound membership protocol: framework contracts protocol, app implements (recommended) vs framework-managed `tenant_memberships` table (deferred, separate spec).
- [ ] **Tenancy B2** — error-code deviation: spec §3.3 assigns `LEX_ERR_SQL_032`, but `032–035/036/037` are taken; plan uses `LEX_ERR_SQL_038`. Confirm the deviation.
- [ ] **Auth ODD-1** — single composed hasher; kill the DI bypass (recommended Option A).
- [ ] **Web-CSRF D1–D6** — flip-points recorded per task (flag semantics, bypass narrowing, HSTS defaults, token-lifetime wiring, boundary hygiene).
- [ ] **Secrets** — fail-closed cloud backend semantics; empty-credential boot errors; rotation eviction policy.
- [ ] **SQLi D1** — deleting free-text `WHERE` in MCP `sql_query` (recommended); **D2** — `find_by_spec`/`paginate_cursor` sort whitelist default.
- [ ] **XSS** — escape-by-default at primitive vs opt-in; sanitizer allowlist scope.
- [ ] **Deserialization D-A…D-D** — SkillLoader fail-closed sandbox (recommended) vs disable `enable_skill_sources`; pickle deletion vs restriction; `@cacheable` registry-only tagged lookup; MySQL backup `--result-file` + stdin restore (recommended) vs `--execute=source` rejection.
- [ ] **SSRF** — fail-closed contract primitive defaults; webhook default-deny posture.
- [ ] **Plugins** — integrity: HMAC skipped, acceptance documented (decided, no sign-off needed); per-page GET permission skipped, documented (decided).
- [ ] **AI-guard** — wire mid-loop guard hooks (tool observations checked before entering context at `react.py:301-308`, `function_calling.py:413-418/465-469`, `plan_execute_executor.py:215-222`); make streaming guard path fail-closed (currently wide-`except` allow); auto-wire pipeline from DI at `AgentsProvider.boot()` (`di/provider.py:289`); make `@guarded` real; decide LLM-detector fail-open posture (recommended: fail-closed on infra errors).
- [ ] **GraphQL** — wire `DepthLimitExtension`/`AliasLimitExtension`/new `ComplexityLimitExtension` into `SchemaBuilderProtocol.build()`; fail-closed production model-validator `_auto_disable_introspection_in_production` + `IntrospectionGuardExtension` (effective-flag semantics, registered first); honest `IntrospectionConfig` docstring; repo-level resolver-authz boundary (framework safety net vs documented app responsibility).
- [ ] **Media-upload** — caps (file size, duration, mime allowlist) in contracts `multimedia/security.py`; SSRF primitive consumption at 4 fetch sites with `allow_redirects=False`; ffmpeg filter-field validation at dataclass level; `client_max_size` on all 13 servers; `scale_factor` runtime validation — **Task 0 gates on SSRF D1 merge**.
- [ ] **Notification/webhook** — contracts mailer validation (subject/to/cc/headers CRLF rejection); SMTP `send()` catches `HeaderParseError`/`HeaderWriteError` (`smtp_mailer.py:120-127`); `escape_html` helper for Mailable; Slack mrkdwn escaping (gated); envelope-recipient validation.
- [ ] **Rate-limit** — middleware-enforced rule semantics via `get_rule` with default-limit fallback (not scaffolded `check_rate_limit`); chunked-body enforcement via streaming byte counter (413 mid-stream); keep `enabled=True` default but make it mean real enforcement; wire `storage_backend`/`whitelist_ips`; decorator path keeps warn-and-skip contract; GraphQL `UnifiedRateLimiter` fail-open deferred to GraphQL spec.

---

## 3. Per-Area Tasks

### 3.1 P0 session-secret (Critical) — `plans/2026-08-16-security-p0-session-secret.md`

- [ ] Task 1 — route session signing through the validated helper (`core/routing.py` → `build_session_cookie_kwargs`; new `test_routing_session_secret.py`)
- [ ] Task 2 — resolve CSRF service in `boot()`, hard-fail on missing binding (new `test_admin_boot_csrf_fail_closed.py`)
- [ ] Task 3 — consume boot-resolved CSRF service in `mount_to_app()` via `_get_csrf_service()`; update 3 `test_bundle_provider.py` tests
- [ ] Task 4 — convert remaining silent `except Exception: pass` to logged structlog warnings
- [ ] Task 5 — full verification: lint, typecheck, test suite, two-pass review

### 3.2 SQL injection — `plans/2026-08-16-security-sql-injection.md`

- [ ] Task 1 (P0) — SQLConnector structured filters: replace free-text `WHERE` + deny-list (`_has_dangerous_sql` removed); `test_mcp_sql_connector_safety.py`
- [ ] Task 2 (P0) — postgres `faceted_search` facet guard (never build quoted literals)
- [ ] Task 3 (P0) — `AsyncQueryBuilder` identifier wrap through `Column()`/`Table()` at set-time; **plan checkpoint**
- [ ] Task 4 (P1) — Cypher compiler identifier guard (`lexigram-graph`)
- [ ] Task 5 (P1) — repository sort whitelist verification + regression coverage
- [ ] Task 6 (P2) — callback-filter removal verification (already delisted — grep gate + note)
- [ ] Task 7 (P2) — specification `Field*` identifier wrap; document `where_raw`/`order_by_raw` escape hatches
- [ ] Task 8 (Low) — AdminSession repository `_TABLE` → `Table()`

### 3.3 Tenancy isolation — `plans/2026-08-16-security-tenancy.md` (s)

- [ ] Task 1 (F2) — implement `set_tenant_from_scope`/`reset_tenant` on `DbContext` (bridge wiring)
- [ ] Task 2 (F2/F3) — enforcement core: `TenantScopingError`, fail-closed filter, construction guard, `with_tenant_scope` — **must merge with Task 1 together** (B3)
- [ ] Task 3 (F4) — fail-closed `create()`: backfill-or-reject with `TenantScopingError`
- [ ] Task 4 (F1) — identity-bound tenant resolution: contracts protocol, `resolve_with_source`, `authorize()` — **blocked on O1 sign-off** (B1)
- [ ] Task 5 (F5) — ContextVar token capture/reset in `TenantContextMiddleware`; update (not delete) resolver mocks in `test_middleware.py` (B4)
- [ ] Task 6 — full verification

### 3.4 XSS / output rendering — `plans/2026-08-16-security-xss-render.md`

- [ ] Task 1 (F1) — escape-by-default at the `el()` primitive (`lexigram-ui`)
- [ ] Task 2 (F2) — close delete-confirm path + dashboard widgets (`lexigram-admin`); extend existing `test_content_renderer.py`
- [ ] Task 3 (F3/F5/F7) — allowlist sanitizer wired into rich text render path
- [ ] Task 4 (F6) — replace hand-rolled toast f-string with escaping renderer
- [ ] Task 5 (F4/F8) — move trusted-HTML boundary to the renderer (`admin_shell.html` autoescape)
- [ ] Task 6 — full verification

### 3.5 Auth / hashers — `plans/2026-08-16-security-auth-hashers.md` (s)

- [ ] Task 1 (F2) — config-driven cost factors; make the `rounds` knob real (`PasswordConfig` cost field)
- [ ] Task 2 (F1) — real `needs_rehash()` + cost-upgrade on login (`security.py:163-165` → wired via `services.py:326/350`)
- [ ] Task 3 (F3) — single composed hasher; kill the DI bypass — **implements ODD-1, recommended Option A** (s); update `test_auth.py:49-59`, `test_setup_controller.py:348-352`
- [ ] Task 4 (F4) — delete the admin SHA-256 fallback (`admin/lib/password.py:27-28`); fail closed on setup path
- [ ] Task 5 — full verification

### 3.6 Web CSRF / headers — `plans/2026-08-16-security-web-csrf.md` (s)

- [ ] Task 1 (F-W1) — one CSRF flag, fail-closed validation (`lexigram-web` `SecurityConfig.enable_csrf` dead-flag fix)
- [ ] Task 2 (F-W2/3/4) — HMAC-sign the wired middleware; narrow default bypasses
- [ ] Task 3 (F-W6/7) — HSTS production-on, one headers implementation, host validation
- [ ] Task 4 (F-W5) — admin token-lifetime wiring (`csrf_token_lifetime`, additive)
- [ ] Task 5 (F-W8) — web↔admin CSRF boundary hygiene
- [ ] Task 6 — full verification

### 3.7 Secrets / credentials — `plans/2026-08-16-security-secrets.md` (s)

- [ ] Task 1 (F1) — `SecretsConfig` env derivation + production validator + replace `FakeRotatableSecretStore` default
- [ ] Task 2 (F3) — `AuthenticationProvider` strict-env raise; delete dev-secret literal; widen HS validator
- [ ] Task 3 (F2) — `SecretStr` for `JWTConfig.secret_key` / `AdminAuthConfig.session_secret`
- [ ] Task 4 (F4) — mask embedding `api_key` fields (`repr=False`)
- [ ] Task 5 (F5) — fail-closed cloud backend semantics + empty-credential boot error
- [ ] Task 6 (F6) — `DotenvSecretBackend` permission discipline (chmod 0600)
- [ ] Task 7 (F7) — `SecretValue.__format__` masking
- [ ] Task 8 (F8) — `RotationDecorator` grace-buffer eviction
- [ ] Task 9 — full verification

### 3.8 SSRF / outbound — `plans/2026-08-16-security-ssrf.md`

- [ ] Task 1 (D1) — contracts SSRF primitive (stdlib-only, DNS-aware, fail-closed)
- [ ] Task 2 (D2) — core + admin sanitizers delegate to the single primitive (collapse duplication)
- [ ] Task 3 (D3) — webhook: default-deny registration + delivery, `allow_private_urls` opt-out
- [ ] Task 4 (D5) — RAG `WebScraperLoader`: validate seed, redirects, followed links
- [ ] Task 5 (D4) — MCP `web_fetch`: validate + own the redirect trail
- [ ] Task 6 (D6) — storage: local driver stops lying; admin falls back to `get_url`
- [ ] Task 7 — full verification (incl. boundaries)

### 3.9 Deserialization / code-exec — `plans/2026-08-16-security-deserialization.md` (s)

- [ ] Task 1 (F1) — `SkillLoader`: real fail-closed sandbox + wired `allowed_script_types` (`lexigram-ai-skills`) — **blocked on D-A sign-off** (s)
- [ ] Task 2 (F2) — delete or restrict the three pickle deserializers (`lexigram-cache`, `lexigram-search`, `lexigram-cli`) — **D-B** (s)
- [ ] Task 3 (F3) — `@cacheable` type-tag gadget: registered type registry, deny-by-default — **D-C** (s)
- [ ] Task 4 (F4) — CLI MySQL backup/restore: drop `shell=True`, fix redirection — **D-D** (s)
- [ ] Task 5 (F5) — delete the dormant shell-string runner (`scripts/audit/base.py:243`)
- [ ] Task 6 — full verification

### 3.10 Plugins — `plans/2026-08-16-security-plugins.md` `[~]`

- [x] Task 1 (L1) — engine delegates discovery/instantiation to the shared primitive (collapse duplicate `discover_providers()`); moved into core as `lexigram.plugins` (the `lexigram-plugins` distribution was folded into `lexigram`)
- [x] Task 2 (L2) — wire `validate_plan()` into the boot engine (advisory `requires`/`conflicts`)
- [x] Task 3 (L4) — validate the state-file schema `version` on load (preserve `.corrupt` pattern); new `test_state_hardening.py`
- [x] Task 4 (L3) — document the accepted no-tamper-evidence posture (no code change; HMAC skipped by decision) — `lexigram/docs/plugins.md` "File integrity"
- [x] Task 5 (L5) — document the accepted per-page-GET posture (no code change; acceptance `Sec-2026-08-16-L5` comment on `plugins.py:index()`) — `lexigram/docs/plugins.md` "Per-page GET (admin)"
- [x] Task 6 — distribution plumbing: `lexigram-plugins` removed from both `pyproject.toml` files; `PluginsModule` entry points + core `__init__` exports; `lexigram-plugins/` directory deleted; docstring/example-yaml/README/CHANGELOG updated
- [ ] Task 7 — full verification: lint, typecheck, test suite, boot smoke (blocked on `uv lock` resolution of a pre-existing `lexigram-multimedia-music[ace-step-server]` ↔ `pillow` conflict on non-3.13 Python ranges; re-lock scoped to the .venv interpreter)

### 3.11 AI guard / prompt-injection — `plans/2026-08-16-security-ai-guard.md` (s)

- [ ] Task 1 (F2) — auto-wire `GuardPipeline` from DI in `AgentsProvider.boot()`; export `GuardPipelineProtocol` from GuardModule; executor reads `agent.guard_pipeline` (currently dead-ends at constructor `safety` only, `executor.py:140`)
- [ ] Task 2 (F1) — mid-loop guard hooks: check tool observations before entering context (`react.py:301-308`, `function_calling.py:413-418/465-469`, `plan_execute_executor.py:215-222`)
- [ ] Task 3 (F3) — make `@guarded` real: resolve the pipeline from the container, invoke check_input/check_output (currently `return await func(...)` only, `decorators.py:46-53`); replace the mock-only "decorator" tests
- [ ] Task 4 (F4) — LLM-detector error posture: fail-closed on infrastructure errors, keep fail-open only for detection-verdict errors (`llm_injection.py:172-197`)
- [ ] Task 5 (F1) — streaming path fail-closed: `streaming.py:250-252, 280-282` catch broad `Exception` → allow; make it escalate
- [ ] Task 6 — full verification (incl. diff cross-check vs SSRF plan)

### 3.12 GraphQL security — `plans/2026-08-16-security-graphql.md` (s)

- [ ] Task 1 — failing through-executor security tests (prove depth/alias/complexity gating is dead; complexity analyzer orphan)
- [ ] Task 2 — wire `DepthLimitExtension`/`AliasLimitExtension`/new `ComplexityLimitExtension` in `SchemaBuilderProtocol.build()`; complete `SchemaValidator` with complexity
- [ ] Task 3 — failing tests: introspection stays ON for default production config today
- [ ] Task 4 — fail-closed: production model-validator `_auto_disable_introspection_in_production` + `IntrospectionGuardExtension` (effective-flag semantics, registered first) + honest `IntrospectionConfig` docstring
- [ ] Task 5 — ruff/mypy/full suite/end-to-end gate proof + two-pass review

### 3.13 Media upload / processing safety — `plans/2026-08-16-security-media-upload.md` (s)

- [ ] Task 0 — **gate: SSRF D1 contracts primitive merged** (`lexigram.contracts.security.url_safety.is_safe_url_for_request`, DNS-aware, fail-closed)
- [ ] Task 1 (F1) — consume the contracts primitive at all 4 fetch sites with `allow_redirects=False`: `_asset_io.py:13-17`, `librosa.py:37-41`, `media_io.py:34-43`, `f5_tts_server.py:44-51`
- [ ] Task 2 (F2) — caps (size, duration, mime allowlist) in contracts `multimedia/security.py`; pre-decode guards at `librosa.py:59`, `madmom_server.py:34-41`
- [ ] Task 3 (F3) — ffmpeg filter-field validation at dataclass level (`argv.py` color/font_size/codec/resolution/bitrate; reachable via `video/tasks.py:147-244`)
- [ ] Task 4 (F4) — `client_max_size` on all 13 servers; runtime `scale_factor` validation (`hat_server.py:42-43`, `real_esrgan_server.py:41-42`)
- [ ] Task 5 — full verification

### 3.14 Notification / webhook injection — `plans/2026-08-16-security-notification-webhook.md` (s)

- [ ] Task 1 (D1) — contracts mailer validation: CRLF rejection on subject/to/cc/headers + envelope recipients (new `test_mailer_validation.py`)
- [ ] Task 2 (D2) — `SMTPMailer.send()` catches `HeaderParseError`/`HeaderWriteError` → Result error (new `test_smtp_header_injection.py`)
- [ ] Task 3 (D3) — `escape_html` helper for Mailable html_body (extend `test_mailable.py`)
- [ ] Task 4 (D4) — Slack mrkdwn escaping (gated; extend `test_slack.py`)
- [ ] Task 5 — full verification (zero `lexigram-webhook` edits; webhook SSRF owned by SSRF plan Task 3)

### 3.15 Rate-limiting / DoS — `plans/2026-08-16-security-rate-limit.md` (s)

- [ ] Task 1 (CRIT) — middleware actually enforces rules: resolve rule via `get_rule` with default-limit fallback; keep `enabled=True` but make it mean enforcement
- [ ] Task 2 (CRIT) — honest config: `RateLimitConfig` docstring; wire dead fields `whitelist_ips`/`storage_backend` (or documented decision)
- [ ] Task 3 (MED) — chunked-body enforcement: streaming byte counter over `receive` (413 mid-stream) in `body_limit.py`
- [ ] Task 4 (LOW) — concurrency-bound decision: bulkhead evaluation in `lexigram-queue` backends
- [ ] Task 5 — full verification

---

## 4. Audit-Correction Register

Agents re-verified every finding against live code; corrections below must
not regress. Full details in each spec §2.

| Area | Correction |
|------|------------|
| Auth | F1 `needs_rehash()` hardcoded `return False` (dead); F4 consumer is the admin setup/initial-provisioning path, and the fallback also bricks admin login silently; tests `test_auth.py:49-59`, `test_setup_controller.py:348-352` assert the weak behaviors and must be **updated**; `rounds` can't work because `hash`/`verify` are staticmethods |
| Secrets | Default store is worse than audited — a **test fake** (`FakeRotatableSecretStore`); only 4 of 5 Vault methods collapse (audit overcounted), GCP has the identical pattern (audit named only Vault); Vault/AWS do have bugfix tests (audit's "no tests" overbroad — accurate for GCP/Azure); JWT manager's production literal check exists but only for exact `LEX_ENV == "production"` — staging hole stands |
| Tenancy | `auth_claims` never populated by any framework auth middleware — JWT resolver never resolves, header path is the effective default; `TenantScope` (claimed by `RowLevelIsolationStrategy` docstring) doesn't exist anywhere |
| Web-CSRF | Audit F6 reversed: CSRF is actually **on by default** (dead flag lies in opposition); HSTS is opt-in (audit corrected); F-W3/F-W5/F-W8 are new details the audit missed |
| XSS | F5 premise corrected (sanitizer exists but not in render path); F7 host-side widget content renderer is a new surface (audit §3 findings 7-8 were verified clean) |
| Architecture | `lexigram.result` already converges on contracts (F1b is a one-line import fix); audit missed `lexigram-ai-llm` call sites + `lexigram-search` calls a nonexistent `ambient_hashing.digest` API (latent `AttributeError`); live importlinter failure is `*.admin.pages.* → lexigram.ui` (not `lexigram.admin → lexigram.ui`); six DB drivers consume the retry shim, not four |
| SQLi | F3/F4 callers corrected to current live callers; F6 admin `SqlQueryBuilder` confirmed dead |
| Deserialization | Pickle defaults re-settled as Medium (not as severe as headline); all claims re-grepped to real file:line refs; no fabricated CVEs |
| AI-guard | Output-check line ref corrected (`executor.py:375-408`, not `:312-332`); audit's "Positive" fail-closed guard integration is only true of `run()` — **streaming path fails open** (`streaming.py:250-252, 280-282` catch broad `Exception`, return allow); even explicit `.with_guard_pipeline(...)` dead-ends — executor never reads `agent.guard_pipeline`; GuardModule exports no `GuardPipelineProtocol`; "default" pipeline requires mounting `GuardModule` (not part of standard module set) |
| Media upload | F1 spans **4 fetch sites not 2** (audit missed `video/processing/media_io.py:34-43` and `tts/servers/f5_tts_server.py:44-51`); F2 decode-bomb has a twin server-side (`madmom_server.py:34-41`); `file://` passthroughs exist at `media_io.py:28-32` / `f5_tts_server.py:37-38`; all servers bind `0.0.0.0`; F4 "none of six" → **none of 13 servers** set `client_max_size`, and aiohttp implicit default is ~1 MiB (defect is the implicit mis-sized cap, not literal unboundedness); ffmpeg filter-string reachability confirmed at framework level (`video/tasks.py:147-244`); `probe_duration`/`probe_fps` run ffprobe with no timeout |
| Notification | SMTP header injection **re-rated High → Medium**: compat32 `__setitem__` accepts CRLF, but `as_string()` raises `email.errors.HeaderParseError` (verified on 3.11/3.12/3.13) — "silently BCCs attacker" does not occur; real defect is the uncaught `HeaderParseError` leaking from the executor thread (Result-contract violation, admin `EmailSender` crash risk) + zero boundary validation + unvalidated envelope recipients; CRLF-bearing header **names** raise `HeaderWriteError` (same leak); `reply_to` ignored by SMTP + SendGrid backends |
| Rate-limit | "Nothing calls per-route enforcement" accurate only for REST middleware — 3 live `check_rate_limit` callers exist elsewhere (GraphQL `UnifiedRateLimiter` opt-in + fail-open → deferred to separate spec, debug routes, WebSocket limiter); two more dead config fields beyond `rules`: `whitelist_ips` and `storage_backend` (never read in `src/`); `body_limit.py:34-37` docstring references a TODO that doesn't exist |

---

## 6. Round 3 — Spec + Plan (No Execution Authorized)

Round 3 added 5 more areas to `docs/superpowers/specs/2026-08-16-security-architecture-audit-findings.md` (§13-17). Specs and plans for all five were produced 2026-08-16, following the same verify → spec → plan → two-pass-review process. None of these plans may be executed until separately authorized.

| # | Area | Doc section | Severity mix | Spec | Plan | Status |
|---|------|--------------|------|------|------|--------|
| 11 | **AI guard / prompt-injection** | §13 | Critical ×2, High ×2, Med ×1 | `specs/2026-08-16-security-ai-guard-design.md` | `plans/2026-08-16-security-ai-guard.md` | Not started (s) |
| 12 | **GraphQL security** | §14 | Critical ×2, High ×1, Med ×1 | `specs/2026-08-16-security-graphql-design.md` | `plans/2026-08-16-security-graphql.md` | Not started (s) |
| 13 | **Media upload / processing safety** | §15 | High ×2, Med ×2 | `specs/2026-08-16-security-media-upload-design.md` | `plans/2026-08-16-security-media-upload.md` | Not started (s) |
| 14 | **Notification / webhook injection** | §16 | High ×1, Med ×2, Low ×1 | `specs/2026-08-16-security-notification-webhook-design.md` | `plans/2026-08-16-security-notification-webhook.md` | Not started (s) |
| 15 | **Rate-limiting / DoS resilience** | §17 | Critical ×1, Med ×1, Low ×1 | `specs/2026-08-16-security-rate-limit-design.md` | `plans/2026-08-16-security-rate-limit.md` | Not started (s) |

**Recurring shape (per master doc §1):** three of these five (AI guard's `@guarded` decorator, GraphQL's depth/complexity/introspection layer, web's rate-limit `rules` config) are the "orphaned correct implementation" pattern — a well-built implementation exists and nothing calls it, not even a competing weaker path. This is the same root-cause family as Round 1-2's Pattern A, one step more extreme. Round 3 specs follow the same remediation patterns: wire the existing implementation at the correct boundary, fail-closed at boot on missing security config.

**Cross-plan dependencies (Round 3):**
- Media-upload **Task 0** gates on SSRF plan **D1** (contracts `is_safe_url_for_request` primitive must be merged first); media consumes the primitive at 4 fetch sites with `allow_redirects=False`, does not re-invent URL safety.
- AI-guard F1 closes the loop on SSRF §12 (web_fetch/RAG content); plans are complementary, no shared files — AI-guard plan includes a diff cross-check asserting no SSRF files are touched.
- Notification-webhook deliberately excludes webhook URL SSRF — owned by SSRF plan Task 3 (D3 default-deny); plan makes **zero** `lexigram-webhook` edits.

---

## 7. Commands (from AGENTS.md)

```bash
uv run ruff check . && uv run ruff format --check .   # lint
uv run mypy lexigram/src/                             # typecheck core
uv run pytest --tb=short --cov-fail-under=80          # aggregate suite
uv run pytest <pkg>/tests/                            # scoped
```

Constraints: no worktrees, no branches unless asked; commit only when
explicitly asked; every changed line must trace to an audit finding.