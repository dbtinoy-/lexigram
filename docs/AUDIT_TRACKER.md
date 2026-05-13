# Security Audit — Implementation Tracker

**Generated:** 2026-08-16
**Source:** `docs/superpowers/specs/2026-08-16-security-architecture-audit-findings.md`
**Process:** verify → spec → plan → execute → two-pass review

Status of all 15 spec+plan security remediation areas across audit Rounds
1-3, plus 21 further areas from Rounds 4-7 (20 with design specs written
2026-08-16; Round 4 #20 Non-SQL has none; no plans or execution yet). Round 3 (§6 below)
added 5 more areas; specs + plans for those were written 2026-08-16, none
executed yet. Round 4 (§7 below) added 5 more areas; design specs written for
four of five (all but #20 Non-SQL). Round 5 (§8 below) and Round 6 (§9 below)
added 5 areas each; design specs written for all ten. Round 7 (§10 below)
added 6 more areas from a focused lexigram-admin pass (2026-08-16); design
specs for all six written 2026-08-16, none executed yet. Round 8 (§11
below) added 6 more areas from a second focused lexigram-admin pass plus
the lexigram-search filter backends (2026-08-16); findings + design specs
for all six written 2026-08-16, none executed yet. Round 9 (§12 below)
added 5 more areas from the first extension-package pass (AI subsystem,
HTTP-facing, media/data/IO packages; 2026-08-16); design specs for all
five written 2026-08-16; the pass also re-verified 8 prior spec'd areas
and confirmed them still open (no new specs — they trace to §3 plans).
Round 1-2 execution (2026-08-16): P0 session-secret
(§3.1), SQL injection (§3.2), XSS (§3.4), and SSRF (§3.8) executed and
verified complete; Plugins Tasks 1-6 executed, Task 7 blocked on `uv lock`
(§3.10); Web CSRF (§3.6) partially executed (`75568cd`) with deviations
recorded in its plan; the remaining areas are not started.

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
| 1 | **P0 session-secret** | Critical ×3 | `specs/2026-08-16-security-p0-session-secret-design.md` | `plans/2026-08-16-security-p0-session-secret.md` | Done |
| 2 | **SQL injection** | Critical ×2, High ×2, Med ×2, Low ×2 | `specs/2026-08-16-security-sql-injection-design.md` | `plans/2026-08-16-security-sql-injection.md` | Done |
| 3 | **Tenancy isolation** | Critical ×2, High ×2, Med ×2 | `specs/2026-08-16-security-tenancy-design.md` | `plans/2026-08-16-security-tenancy.md` | Not started (s) |
| 4 | **XSS / output rendering** | Critical ×2, High ×5, Med ×1 | `specs/2026-08-16-security-xss-render-design.md` | `plans/2026-08-16-security-xss-render.md` | Done |
| 5 | **Auth / hashers** | Critical ×1, High ×3 | `specs/2026-08-16-security-auth-hashers-design.md` | `plans/2026-08-16-security-auth-hashers.md` | Not started (s) |
| 6 | **Web CSRF / headers** | High ×5, Med ×3 | `specs/2026-08-16-security-web-csrf-design.md` | `plans/2026-08-16-security-web-csrf.md` | In progress (partial — §3.6) |
| 7 | **Secrets / credentials** | Critical ×1, High ×3, Med ×2, Low ×2 | `specs/2026-08-16-security-secrets-design.md` | `plans/2026-08-16-security-secrets.md` | Not started (s) |
| 8 | **SSRF / outbound** | Critical ×2, High ×1, Med ×1 | `specs/2026-08-16-security-ssrf-design.md` | `plans/2026-08-16-security-ssrf.md` | Done |
| 9 | **Deserialization / code-exec** | High ×1, Med ×2, Low ×2 | `specs/2026-08-16-security-deserialization-design.md` | `plans/2026-08-16-security-deserialization.md` | Not started (s) |
| 10 | **Plugins** | Low ×5 | `specs/2026-08-16-security-plugins-design.md` | `plans/2026-08-16-security-plugins.md` | In progress (`[~]` §3.10 — Task 7 blocked) |

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

### 3.1 P0 session-secret (Critical) — `plans/2026-08-16-security-p0-session-secret.md` `[x]`

- [x] Task 1 — route session signing through the validated helper (`core/routing.py` → `build_session_cookie_kwargs`; new `test_routing_session_secret.py`)
- [x] Task 2 — resolve CSRF service in `boot()`, hard-fail on missing binding (new `test_admin_boot_csrf_fail_closed.py`)
- [x] Task 3 — consume boot-resolved CSRF service in `mount_to_app()` via `_get_csrf_service()`; update 3 `test_bundle_provider.py` tests
- [x] Task 4 — convert remaining silent `except Exception: pass` to logged structlog warnings
- [x] Task 5 — full verification: lint, typecheck, test suite, two-pass review

### 3.2 SQL injection — `plans/2026-08-16-security-sql-injection.md` `[x]`

- [x] Task 1 (P0) — SQLConnector structured filters: replace free-text `WHERE` + deny-list (`_has_dangerous_sql` removed); `test_mcp_sql_connector_safety.py`
- [x] Task 2 (P0) — postgres `faceted_search` facet guard (never build quoted literals)
- [x] Task 3 (P0) — `AsyncQueryBuilder` identifier wrap through `Column()`/`Table()` at set-time; **plan checkpoint**
- [x] Task 4 (P1) — Cypher compiler identifier guard (`lexigram-graph`)
- [x] Task 5 (P1) — repository sort whitelist verification + regression coverage
- [x] Task 6 (P2) — callback-filter removal verification (already delisted — grep gate + note)
- [x] Task 7 (P2) — specification `Field*` identifier wrap; document `where_raw`/`order_by_raw` escape hatches
- [x] Task 8 (Low) — AdminSession repository `_TABLE` → `Table()`

### 3.3 Tenancy isolation — `plans/2026-08-16-security-tenancy.md` (s)

- [ ] Task 1 (F2) — implement `set_tenant_from_scope`/`reset_tenant` on `DbContext` (bridge wiring)
- [ ] Task 2 (F2/F3) — enforcement core: `TenantScopingError`, fail-closed filter, construction guard, `with_tenant_scope` — **must merge with Task 1 together** (B3)
- [ ] Task 3 (F4) — fail-closed `create()`: backfill-or-reject with `TenantScopingError`
- [ ] Task 4 (F1) — identity-bound tenant resolution: contracts protocol, `resolve_with_source`, `authorize()` — **blocked on O1 sign-off** (B1)
- [ ] Task 5 (F5) — ContextVar token capture/reset in `TenantContextMiddleware`; update (not delete) resolver mocks in `test_middleware.py` (B4)
- [ ] Task 6 — full verification

### 3.4 XSS / output rendering — `plans/2026-08-16-security-xss-render.md` `[x]`

- [x] Task 1 (F1) — escape-by-default at the `el()` primitive (`lexigram-ui`)
- [x] Task 2 (F2) — close delete-confirm path + dashboard widgets (`lexigram-admin`); extend existing `test_content_renderer.py`
- [x] Task 3 (F3/F5/F7) — allowlist sanitizer wired into rich text render path
- [x] Task 4 (F6) — replace hand-rolled toast f-string with escaping renderer
- [x] Task 5 (F4/F8) — move trusted-HTML boundary to the renderer (`admin_shell.html` autoescape)
- [x] Task 6 — full verification

### 3.5 Auth / hashers — `plans/2026-08-16-security-auth-hashers.md` (s)

- [ ] Task 1 (F2) — config-driven cost factors; make the `rounds` knob real (`PasswordConfig` cost field)
- [ ] Task 2 (F1) — real `needs_rehash()` + cost-upgrade on login (`security.py:163-165` → wired via `services.py:326/350`)
- [ ] Task 3 (F3) — single composed hasher; kill the DI bypass — **implements ODD-1, recommended Option A** (s); update `test_auth.py:49-59`, `test_setup_controller.py:348-352`
- [ ] Task 4 (F4) — delete the admin SHA-256 fallback (`admin/lib/password.py:27-28`); fail closed on setup path
- [ ] Task 5 — full verification

### 3.6 Web CSRF / headers — `plans/2026-08-16-security-web-csrf.md` `[~]`

Partially executed 2026-08-16 (`75568cd`): production hard-fail when CSRF disabled + `/api/` dropped from default exclusion + cookie-aware excluded-path validation + duplicate `SecurityHeadersMiddleware` deleted. **Deviations from plan:** `enable_csrf` gated in `_add_csrf` instead of authoritative-sync (D-1 alt); bypass narrowing via cookie-awareness instead of removing `hx-request`/content-type/auth-scheme defaults. Details in the plan's Execution Status table.

- [ ] Task 1 (F-W1) — one CSRF flag, fail-closed validation (partial: `enable_csrf` gate shipped; authoritative-sync + prod `secret_key` raise pending)
- [ ] Task 2 (F-W2/3/4) — HMAC-sign the wired middleware; narrow default bypasses (partial: `/api/` default exclusion removed, cookie-aware exclusions; HMAC signing + bypass removal pending)
- [ ] Task 3 (F-W6/7) — HSTS production-on, one headers implementation, host validation (partial: duplicate `SecurityHeadersMiddleware` deleted; HSTS + host validation pending)
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

### 3.8 SSRF / outbound — `plans/2026-08-16-security-ssrf.md` `[x]`

 - [x] Task 1 (D1) — contracts SSRF primitive (stdlib-only, DNS-aware, fail-closed)
 - [x] Task 2 (D2) — core + admin sanitizers delegate to the single primitive (collapse duplication)
 - [x] Task 3 (D3) — webhook: default-deny registration + delivery, `allow_private_urls` opt-out
 - [x] Task 4 (D5) — RAG `WebScraperLoader`: validate seed, redirects, followed links
 - [x] Task 5 (D4) — MCP `web_fetch`: validate + own the redirect trail
 - [x] Task 6 (D6) — storage: local driver stops lying; admin falls back to `get_url`
 - [x] Task 7 — full verification (incl. boundaries)

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

- [x] Task 1 (D1) — contracts mailer validation: CRLF rejection on subject/to/cc/headers + envelope recipients (new `test_mailer_validation.py`)
- [x] Task 2 (D2) — `SMTPMailer.send()` catches `HeaderParseError`/`HeaderWriteError` → Result error (new `test_smtp_header_injection.py`)
- [x] Task 3 (D3) — `escape_html` helper for Mailable html_body (extend `test_mailable.py`)
- [x] Task 4 (D4) — Slack mrkdwn escaping (gated; extend `test_slack.py`)
- [x] Task 5 — full verification (zero `lexigram-webhook` edits; webhook SSRF owned by SSRF plan Task 3)

### 3.15 Rate-limiting / DoS — `plans/2026-08-16-security-rate-limit.md` (s)

- [x] Task 1 (CRIT) — middleware actually enforces rules: resolve rule via `get_rule` with default-limit fallback; keep `enabled=True` but make it mean enforcement
- [x] Task 2 (CRIT) — honest config: `RateLimitConfig` docstring; wire dead fields `whitelist_ips`/`storage_backend` (or documented decision)
- [x] Task 3 (MED) — chunked-body enforcement: streaming byte counter over `receive` (413 mid-stream) in `body_limit.py`
- [x] Task 4 (LOW) — concurrency-bound decision: bulkhead evaluation in `lexigram-queue` backends
- [x] Task 5 — full verification

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

## 5. Execution Split (2026-08-16)

Two parallel waves over the executable (non-`(s)`) areas, per §1 execution order:

**Wave A — coordinator (me):** P0 session-secret (§3.1), SSRF (§3.8) —
kept in-coordinator because both are design-sensitive: P0 is Critical×3 on
the boot path; SSRF D1 is the contracts primitive that gates Media Task 0.

**Wave B — parallel agents:** SQL injection (§3.2), XSS / output
rendering (§3.4) — well-specified plans with independent file sets.

**Parked:** Plugins Task 7 (uv lock conflict on `lexigram-multimedia-music`
↔ `pillow`), and all `(s)` areas (3, 5, 7, 9, 11–15) pending §2 sign-off.

Agent constraint: agents do not edit this tracker or commit; coordinator
updates checkboxes centrally from agent reports.

**Outcomes (2026-08-16, night session):** Wave A — P0 (5/5 tasks) and SSRF
(7/7 tasks) executed and verified; Wave B — SQLi (adopted via `f5161644`,
closed `52dd9043`) and XSS (verified + closed `52dd9043`); the frontend pass
additionally executed part of Web CSRF (`75568cd`) — partial scope with
recorded deviations, §3.6; Plugins Task 7 remains parked (uv lock).

---

## 6. Round 3 — Spec + Plan (No Execution Authorized)

Round 3 added 5 more areas to `docs/superpowers/specs/2026-08-16-security-architecture-audit-findings.md` (§13-17). Specs and plans for all five were produced 2026-08-16, following the same verify → spec → plan → two-pass-review process. None of these plans may be executed until separately authorized.

| # | Area | Doc section | Severity mix | Spec | Plan | Status |
|---|------|--------------|------|------|------|--------|
| 11 | **AI guard / prompt-injection** | §13 | Critical ×2, High ×2, Med ×1 | `specs/2026-08-16-security-ai-guard-design.md` | `plans/2026-08-16-security-ai-guard.md` | Not started (s) |
| 12 | **GraphQL security** | §14 | Critical ×2, High ×1, Med ×1 | `specs/2026-08-16-security-graphql-design.md` | `plans/2026-08-16-security-graphql.md` | Not started (s) |
| 13 | **Media upload / processing safety** | §15 | High ×2, Med ×2 | `specs/2026-08-16-security-media-upload-design.md` | `plans/2026-08-16-security-media-upload.md` | Not started (s) |
| 14 | **Notification / webhook injection** | §16 | High ×1, Med ×2, Low ×1 | `specs/2026-08-16-security-notification-webhook-design.md` | `plans/2026-08-16-security-notification-webhook.md` | Done (s) |
| 15 | **Rate-limiting / DoS resilience** | §17 | Critical ×1, Med ×1, Low ×1 | `specs/2026-08-16-security-rate-limit-design.md` | `plans/2026-08-16-security-rate-limit.md` | Done (s) |

**Recurring shape (per master doc §1):** three of these five (AI guard's `@guarded` decorator, GraphQL's depth/complexity/introspection layer, web's rate-limit `rules` config) are the "orphaned correct implementation" pattern — a well-built implementation exists and nothing calls it, not even a competing weaker path. This is the same root-cause family as Round 1-2's Pattern A, one step more extreme. Round 3 specs follow the same remediation patterns: wire the existing implementation at the correct boundary, fail-closed at boot on missing security config.

**Cross-plan dependencies (Round 3):**
- Media-upload **Task 0** gates on SSRF plan **D1** (contracts `is_safe_url_for_request` primitive must be merged first); media consumes the primitive at 4 fetch sites with `allow_redirects=False`, does not re-invent URL safety.
- AI-guard F1 closes the loop on SSRF §12 (web_fetch/RAG content); plans are complementary, no shared files — AI-guard plan includes a diff cross-check asserting no SSRF files are touched.
- Notification-webhook deliberately excludes webhook URL SSRF — owned by SSRF plan Task 3 (D3 default-deny); plan makes **zero** `lexigram-webhook` edits.

---

## 7. Round 4 — Findings + Specs (No Plans/Execution Yet)

Round 4 added 5 more areas to `docs/superpowers/specs/2026-08-16-security-architecture-audit-findings.md` (§18-22), per user request to "cover more areas" while Round 1-3 remediation proceeds in parallel. Design specs written 2026-08-16 for four of the five — **#20 Non-SQL query injection has no spec yet** — and no plan or code change written for any of these.

| # | Area | Doc section | Severity mix |
|---|------|--------------|------|
| 16 | **AI memory / session data isolation** | §18 | Critical ×1, High ×2 |
| 17 | **Logging & observability data leakage** | §19 | Critical ×1 |
| 18 | **AI relay / worker / MCP trust boundary** | §20 | High ×1, Med ×1 |
| 19 | **Outbound HTTP client & resilience hardening** | §21 | High ×1, Med ×1 |
| 20 | **Non-SQL query injection** (`lexigram-nosql`/`lexigram-graph`/`lexigram-vector`) | §22 | High ×1 |

**Recurring shapes (per master doc §24):** §19 (logging redaction) and §21.1 (HTTP URL validation) are the same "orphaned correct implementation" pattern as Rounds 1-3 — a real hook/utility exists and is genuinely wired at one point, but nothing installs/calls the real implementation at the point that matters. §20.1 (relay-gateway auth) is a new variant: the mechanism is correctly and consistently wired everywhere, but its own default config value (`require_auth: bool = False`) disables it — a one-line default fix rather than a wiring fix. §18 (AI memory) and §22 (non-SQL injection) are a third variant, first seen in Round 2's tenancy findings: a correct isolation/validation primitive exists in one package (`lexigram-ai-session`'s scoped queries; `lexigram-graph`'s Cypher identifier validation; `lexigram-search`'s field-name allowlist) but the analogous sibling package solving an adjacent problem (`lexigram-ai-memory`; `lexigram-nosql`'s MongoDB filter compiler) has no equivalent.

---

## 8. Round 5 — Findings + Specs (No Plans/Execution Yet)

Round 5 added 5 more areas to `docs/superpowers/specs/2026-08-16-security-architecture-audit-findings.md` (§23-27), per user request to "continue with round 5 more areas." Design specs written 2026-08-16 for all five — no plan or code change written for any of these yet.

| # | Area | Doc section | Severity mix |
|---|------|--------------|------|
| 21 | **RBAC super-admin role configurability** | §23 | High ×1, Med ×1 |
| 22 | **Password reset / email verification token lifecycle consistency** | §24 | Med ×1, Low ×1 |
| 23 | **CORS & cross-origin configuration** | §25 | Med ×1 |
| 24 | **MFA / TOTP second-factor handling** | §26 | High ×1, Med ×1 |
| 25 | **User impersonation feature** | §27 | Med ×1 |

**Recurring shapes (per master doc §29):** §23.1 (RBAC) and §26.1 (MFA) are a narrower, single-path cousin of the "hook wired but nothing installs a real implementation" pattern — a real enforcement primitive exists and is correctly wired for one code path (login password checks call `check_account_lockout`; `AdminConfig`'s env-backed settings resolve correctly) but a closely related second path (MFA code checks; `RolesResource`'s super-admin-role comparison) never calls it, silently. §27 (impersonation) is a fourth pattern variant not seen in prior rounds — a fully-implemented, well-designed service exists with no HTTP route reaching it at all; a current-risk *positive* (unreachable code can't be exploited today) that flags latent design gaps needing attention before the feature is wired up. §24 (password-reset/email-verification) and §25 (CORS) are dual-implementation variants: two code paths solving the same problem exist side by side, one correct (email verification's atomic consume; the wired `CORSConfig`) and one weaker or orphaned (password reset's TOCTOU gap; the dead `WebProviderConfig` CORS fields).

---

## 9. Round 6 — Findings + Specs (No Plans/Execution Yet)

Round 6 added 5 more areas to `docs/superpowers/specs/2026-08-16-security-architecture-audit-findings.md` (§28-32), per user request to "continue with the next round for more areas." Design specs written 2026-08-16 for all five — no plan or code change written for any of these yet.

| # | Area | Doc section | Severity mix |
|---|------|--------------|------|
| 26 | **First-run setup wizard race/takeover** | §28 | High ×1 |
| 27 | **Admin session/authorization middleware boot-time fail-open** | §29 | Med ×1 |
| 28 | **CSV export formula/DDE injection** | §30 | Med ×1 |
| 29 | **Connection pool health/management endpoint authorization** | §31 | Med ×1 |
| 30 | **Post-login/post-verification open redirect** | §32 | Med ×1 |

**Recurring shapes (per master doc §34):** §29.1 (session/authz middleware) is a boot-time-consistency cousin of the "orphaned correct implementation" family — the real DB-backed session validation and RBAC enforcement are genuinely wired and effective, but their registration is wrapped in the same broad `except Exception: log.warning()`-and-continue pattern the CSRF middleware two sections above explicitly avoids by design, so a DI failure at boot silently degrades the whole auth/authz chain instead of refusing to start. §28.1 (setup-wizard takeover) is a fresh pattern shape, closest analogue is §1's hardcoded session-secret finding: a real security gate exists (`ADMIN_SETUP_TOKEN`) but ships opt-in/unset by default, and a second, independent mechanism (`SetupMiddleware` redirecting every anonymous visitor to `/setup`) actively advertises the resulting open window rather than staying quiet about it — distinguished from §1 by requiring an operator action (setting the env var) to close, not a code fix. §30 (CSV export) and §31 (pool health) are both "the generic safety mechanism used correctly elsewhere in the same package is simply never applied to this one surface" — CSV export has no analogue to sanitize cell content at all; pool health bypasses both the `ActionExecutor.can_execute_action` gate and `SettingsController`'s manual permission check, despite both patterns being established and available in the same codebase. §32 (open redirect) is a plain input-validation gap with no wiring/pattern cousin elsewhere in this document — the single `next_url` parameter is simply never validated at any of its five call sites.

---

## 10. Round 7 — Findings + Specs (No Plans/Execution Yet)

Round 7 added 6 more areas from a focused `lexigram-admin` security pass
(2026-08-16). All six were verified against live code and confirmed absent
from every existing spec/plan (repo-wide doc grep: no `data_source.py`,
`tabular.py`, `controllers/search.py`, or `_BYPASS_SUFFIXES` matches anywhere
in `docs/superpowers/`). Designs written 2026-08-16 — no plan or code
change executed yet. Master-doc section numbers §33-§38 are reserved for
these areas once merged into the findings document.

| # | Area | Severity mix | Spec |
|---|------|--------------|------|
| 31 | **Generic-repository SQL identifier injection** (`admin/data/data_source.py`) | Critical ×1, High ×1 | `specs/2026-08-16-security-admin-sql-identifiers-design.md` |
| 32 | **Auth-guard path-suffix bypass** (`admin/middleware/auth_guard.py`) | High ×1 | `specs/2026-08-16-security-auth-guard-bypass-design.md` |
| 33 | **Alpine JS-expression injection via record ids** (`admin/ui/organisms/table/views/tabular.py`) | High ×1, Med ×1 | `specs/2026-08-16-security-alpine-js-expression-design.md` |
| 34 | **Search partial unescaped record fields** (`admin/controllers/search.py`) | Med ×1 | `specs/2026-08-16-security-search-partial-escaping-design.md` |
| 35 | **Legacy session fallback without TTL / revocation** (`admin/middleware/auth.py`) | Med ×1 | `specs/2026-08-16-security-session-fallback-ttl-design.md` |
| 36 | **Admin login `roles` unbound local** (`admin/auth/services/auth_service.py`) | High ×1 (availability) | `specs/2026-08-16-security-admin-login-roles-unbound-design.md` |

**§33 — SQL identifier injection in the generic resource repository (Critical/High).**
`data/data_source.py` parameterizes values but never identifiers: `find_many` interpolates
raw filter field names into `WHERE` (`:257`); `create` interpolates raw dict keys into the
INSERT column list and the bare `table_name` (`:296`); `update` interpolates raw set-clause
fields and the bare `id_field` in `WHERE` (`:324`,`:331`). `_quote_identifier` — the correct
primitive, already used by `find_one`/`delete` (`:236-238`,`:342-344`) — is skipped by all
three. Reachability: `ResourceController.create()` (`controllers/resource.py:326-`) takes
field names straight from POST form data (`data = dict(form_data)`; `validate_create` is a
pass-through by default) into `data_source.create()`, so an attacker-controlled form field
name lands in the column list (Critical). `update` is the same shape (`:396-430`).
`find_many` filters are caller-supplied; the view layer whitelists via
`build_specification()` (`controllers/base.py:263-289`, praised as a correct closed-whitelist
in the master doc) but the data layer itself has no guard for direct callers (High). The
SQLi plan (§3.2) covers the connector, postgres `faceted_search`, `AsyncQueryBuilder`,
Cypher compiler, repository sort, `Field*` wrap, and admin `AdminSession._TABLE` — this
live resource path is not covered.

**§34 — Auth-guard path-suffix bypass (High).**
`middleware/auth_guard.py:143-145` classifies public paths with `path == suffix or
path.endswith(suffix)` over `_BYPASS_SUFFIXES` (`/login`, `/logout`, `/register`, `/setup`,
`/health`, `/password-reset`, `/verify-email`, plus slash-suffixed twins). Any protected URL
whose path ends in one of those suffixes — `/admin/users/login/`, `/admin/resources/register`,
`/admin/plugins/health` — is served with no session check. Resource names under
`/admin/{resource}/…` are config/contributor-driven, so a resource legitimately named
`login`, `health`, or `register` silently turns an admin page public. Fix is exact
segment-boundary matching; the `_BYPASS_PREFIXES`/`_BYPASS_TOKEN_PREFIXES` handling is
unaffected.

**§35 — Alpine JS-expression injection via record ids (High/Med).**
`ui/organisms/table/views/tabular.py` interpolates record-derived values into JS-string
contexts inside Alpine attributes with no JS escaping: `:304`/`:319` (`group_name` in
`:class`/`@click`), `:376` (`rid` in `@click`), `:415`/`:421-422` (`rid` in `:class`/
`:aria-expanded`/`@click`), `:522-527` (`rid`, `group_key`, `row_height` in row `:class`/
`x-show`, and `style`), `:543-549` (detail `x-show`), plus `detail_url` built from `rid`
(`:540`). The XSS plan's escape-by-default at `el()` (Task 1, done) does **not** neutralize
these: HTML attribute escaping turns `'` into `&#x27;`, but the browser decodes entities
before Alpine evaluates the attribute as JS, so a `'` inside a record id (emails, usernames,
labels, arbitrary string ids) still breaks out of the single-quoted JS string — stored XSS
in the authenticated admin table view. Escaping for the JS-string context (backslash-escape
`\`, `'`, newlines) is required on top of `el()`'s HTML escaping.

**§36 — Search partial unescaped record fields (Med).**
`controllers/search.py:165-185` builds the site-search HTMX partial with raw f-strings:
`r.title` and `r.subtitle` into text spans, `r.url` into `href`/`hx-get`, `resource_label`
into a header span — no escaping anywhere in the builder. Record fields are admin-entered,
so this is a stored-XSS surface (returns to the same admin session on every search hit).
The executed XSS plan covered delete-confirm, dashboard widgets, rich text, toasts, and the
shell boundary — this partial was not in scope.

**§37 — Legacy session fallback without TTL / revocation (Med).**
`middleware/auth.py:183-193`: when no `session_id` is present (no `SessionService` bound, or
a session predating it), any `admin_user_id` in the signed cookie is accepted after only an
`is_active` re-fetch — no expiry, no revocation, no idle timeout. The session-service path
(`:153-181`) enforces all three. This is the residual surface that survives the P0
session-secret fix: a validly signed cookie never expires. Remove the fallback where
`SessionService` is bound, or stamp/check an in-session expiry marker where it must remain.

**§38 — Admin login `roles` unbound local (High, availability).**
`auth/services/auth_service.py:332` returns `roles=roles` on the plain success path, but
`roles` is assigned only inside the early-return email-verification (`:220`) and MFA
(`:244`,`:267`) branches; the main path defines only `session_roles` (`:290`). Any login
that falls through (user without TOTP enrolled — the default setup-created account — or
`mfa_service` unbound) raises `UnboundLocalError` → HTTP 500, bricking the standard login
flow. Suspicious that the suite is green (likely all fixtures use TOTP-enrolled users,
which exit early) — **verify-first**: add a plain-login-path unit test reproducing the
failure before fixing (`roles` → `session_roles`).

**Recurring shapes:** §33 and §35 are new variants of the "correct primitive exists but a
live sibling path never calls it" family — here the primitive (`_quote_identifier`;
`el()` escape-by-default) sits in the same file/package as the unguarded path, used by half
the methods. §32 is a plain path-matching validation gap, closest analogue Round 6 §32's
open-redirect (input-validation gap, five call sites). §36 is a residual raw-f-string
surface outside the executed XSS plan's inventory. §37 is the dual-implementation variant
from Round 5 §24/§25: TTL enforcement exists and is correct on the session-service path;
the fallback silently skips it. §38 is a plain runtime availability bug with no security
cousin — included because it bricks the default login flow.

---

## 11. Round 8 — Findings + Specs (No Plans/Execution Yet)

Round 8 added 6 more areas from a second focused `lexigram-admin` pass
(2026-08-16), sweeping the previously unaudited relations, export-service,
settings-config, and command-palette surfaces plus the `lexigram-search`
filter backends. Master-doc section numbers §39-§44 are reserved for these
areas once merged into the findings document. Findings verified against
live code; designs written 2026-08-16 — no plan or code change executed
yet.

| # | Area | Severity mix | Spec |
|---|------|--------------|------|
| 37 | **Relation panel raw-field rendering (stored + reflected XSS)** (`admin/relations/manager_ext.py`, `belongs_to_many.py`, `routes.py`) | High ×1, Med ×1 | `specs/2026-08-16-security-relations-panel-xss-design.md` |
| 38 | **Relation endpoint authorization / parent-IDOR** (`admin/relations/routes.py`, `manager_ext.py` predicates) | Med ×1 | `specs/2026-08-16-security-relations-routes-authz-design.md` |
| 39 | **Excel export backend formula injection** (`admin/services/export/adapters/excel.py`) | Med ×1 | `specs/2026-08-16-security-export-excel-formula-design.md` |
| 40 | **Meilisearch/Typesense filter-expression injection** (`lexigram-search/backends/filters.py`) | High ×1 | `specs/2026-08-16-security-search-filter-injection-design.md` |
| 41 | **Settings config-read GETs bypass the edit-permission gate** (`admin/controllers/settings.py`, `widgets.py`) | Med ×1 | `specs/2026-08-16-security-settings-config-read-gate-design.md` |
| 42 | **Command palette cross-resource search without per-resource rights** (`admin/controllers/command_palette.py`) | Med ×1 | `specs/2026-08-16-security-command-palette-permissions-design.md` |

**§39 — Relation panel renders record fields raw (High/Med, stored + reflected XSS).**
`relations/manager_ext.py` builds the inline-edit relation table with raw f-strings:
`f"<td>{value}</td>"` (`:91`), `f"<td>{item}</td>"` (`:93`), `item_id` into
`edit_url`/`delete_url` href attributes (`:97-103`), `parent_id`/`rel_name` into the
create URL (`:111-112`). `relations/belongs_to_many.py` is the same: `label` into a
raw `<td>` (`:235`), `item_id` into `data-related-id` *and* the JSON payload of
`hx-vals='{{"related_id": "{item_id}"}}'` (`:230-232`), pivot `value` into
`<input value="{value}">` (`:292`). Reachability is a routine admin flow —
`GET /admin/{resource}/{parent}/relations/{rel}` is the exact `hx-get` target of
Round 7 §35's expandable-detail view (`tabular.py:563`). Record fields are
admin/end-user-writable, so any field value carrying `"`/`<` breaks out of the
attribute or injects markup into the admin's session (stored XSS). A second,
reflected site: `relations/routes.py:48` echoes the URL `record_id` raw into
`HTMLResponse(f"<div>Edit form for {record_id}</div>")` when the record is missing.
The executed XSS plan's `el()` escape-by-default does not apply — these builders
never route through `el()`.

**§40 — Relation endpoints enforce no per-request permission (Med).**
`relations/routes.py:23-93` registers six routes per resource relation (list,
create form, create, edit form, update, delete) with zero permission checks:
`parent_id` comes straight from the path and is passed to `manager_class(parent_id=...)`
(`:97-100`) with no parent-resource existence check (IDOR read of any parent's
related records); the manager's own `can_create`/`can_edit`/`can_delete`/
`can_detach` predicates (`manager_ext.py:53-75`, defaulting to `Ok(None)` = allow)
are **never invoked by any HTTP handler** (verified: no call sites). The only
gate left is `AdminAuthorizationMiddleware`, whose default authorizer admits every
authenticated user. Live mutators (toggle/sync/pivot) are not mounted; the live
gap is data exposure plus missing granular RBAC once they are.

**§41 — Excel export backend writes raw cell values (Med, un-fixed XLSX sibling of §30).**
`services/export/adapters/excel.py:64-67` writes `cell.value = value` straight into
openpyxl cells with no formula/DDE handling. Round 6 §30 covers `CsvExportBackend`
(`services/export/adapters/csv.py`) and its spec (`2026-08-16-security-csv-export-injection-design.md`)
remediates only that backend; `ExcelExportBackend` — the same export pipeline
(`services/export/service.py` `IExportBackend`), same generic data source, same
`ExportAction`/`ExportBulkAction` reachability — ships the identical class of
injection unguarded: a cell value `=HYPERLINK(...)` (or `+`/`-`/`@`-prefixed) in an
exported field evaluates as a live formula in Excel/Sheets/LibreOffice.

**§42 — Meilisearch/Typesense filter-expression injection (High).**
`lexigram-search/src/lexigram/search/backends/filters.py`: `_meili_value` (`:172-178`)
wraps strings as `f'"{value}"'` with zero escaping, and `_typesense_value` (`:262-266`)
is bare `str(value)` with no quoting at all; **field names are interpolated raw**
(`f"{key} = ..."`, `f"{key} != ..."`, etc., `:207-234`, `:293-317`). Every filter
slot (eq/ne/contains/comparisons/in/nin) flows through them, and
`render_filters`/`render_typesense` (`:666`, `:322`) are the only renderers for the
`MeiliSearchBackend` (`meilisearch/backend.py:215`) and `TypesenseBackend`
(`typesense/backend.py:115`). `QueryRule` values reach them unvalidated via
`filterset/block_translator.py:110-134` (only `_validate_field` regex on the field
name). A caller-supplied value containing `"`/`(`/`&&` etc. breaks out of the
filter literal and rewrites the filter expression — filter-bypass (e.g. scoped
queries narrowed to a tenant/owner), data disclosure, or DoS. Admin's own
`SearchService` does not construct these backends today; host apps wiring
`lexigram-search` to Meilisearch/Typesense are the live users — same
"data layer has no guard for direct callers" shape as Round 7 §33.

**§43 — Settings config-read GETs bypass the edit-permission gate (Med).**
`controllers/settings.py:168-205` (`spec_view`, GET `/admin/settings/{namespace}`)
renders the full config form **including current stored values** for any
authenticated user; the `required_permissions` check exists only in `save_spec`
(`:216-221`). Sidebar filtering is navigation-only. Same shape, second call site:
`controllers/widgets.py:346-387` (`GET /admin/core/widgets/{name}/config`) renders
the widget config schema plus **stored config params** (which may include API keys
or tokens) with no `_user_has_edit_permission` check, while every mutating widget
route requires `admin.settings.edit` (`:389-394` etc.). Confidentiality of stored
configuration values; the manual-check-bypass family of Round 6 §31.

**§44 — Command palette search returns cross-resource record data (Med).**
`controllers/command_palette.py:46-72` (`GET /admin/command-palette?q=...`) calls
`SearchService.search(query)` with no user or permission context and returns
`{label, href, subtitle}` for matches from *every* searchable resource — including
records the caller has no `can_view` right on (default authorizer admits all
authenticated users). JSON surface of the same root cause as Round 7 §36's search
partial; the `/admin/search` HTML surface and this JSON endpoint share the missing
per-resource filter.

**Recurring shapes:** §39 is the residual raw-f-string rendering surface right next
to Round 7 §35 — same `/relations/{rel}` detail flow, different layer: the relation
managers build HTML strings directly and never route through the `el()` primitive
the XSS plan fixed. §40 is the "correct permission predicate exists but no HTTP
handler invokes it" family — `RelationManager.can_*` mirrors Round 5 §26.1's MFA
predicate and Round 4's orphaned-correct-implementation shape. §41 is the
dual-implementation variant from Round 7 §37/Round 5 §24-25: §30's remediation lands
on `csv.py`; the `excel.py` sibling ships the same class unguarded. §42 is a new
filter-expression sibling of the identifier-injection family (Round 7 §33): the
construction-time guard is absent at a framework search layer, values *and* field
names interpolated raw. §43 is the manual-check-bypass family of Round 6 §31 (POST
gated, sibling GET not). §44 is the authorization-context gap shared with Round 7
§36 (search without per-resource `can_view`) on a new JSON surface.

---

## 12. Round 9 — Findings + Specs (No Plans/Execution Yet)

Round 9 (2026-08-16) swept the extension packages outside `lexigram-admin`
for the first time — AI subsystem (`lexigram-ai-*`, `lexigram-vector`),
HTTP-facing (`lexigram-http/web/webhook/graphql/auth/tenancy`), and
media/data/IO/background (`lexigram-multimedia*`, `lexigram-notification`,
`lexigram-queue/tasks/events/workflow`, `lexigram-storage`, `lexigram-secrets`
etc.) — via three parallel exploration agents, with every finding below
personally re-verified against live code. Five areas are genuinely new
(§45-49, design specs written 2026-08-16); the remainder of the pass
re-verified eight previously spec'd remediation areas and confirmed they
are **still open** (no new specs — they trace to the existing Round 1-3
plans listed in §3). No plans or execution written for any Round 9 item.

| # | Area | Severity mix | Spec |
|---|------|--------------|------|
| 45 | **`lexigram-vector` pgvector metadata-field injection** | High ×1 | `specs/2026-08-16-security-vector-sql-field-injection-design.md` |
| 46 | **`lexigram-storage` KV local namespace traversal** (arbitrary `rmtree`) | Med ×1 | `specs/2026-08-16-security-storage-kv-namespace-traversal-design.md` |
| 47 | **`lexigram-ai-mcp` server: no initialize-handshake/authz enforcement** | Med ×1 | `specs/2026-08-16-security-mcp-server-initialize-authz-design.md` |
| 48 | **`lexigram-ai-agents` tool-visibility check fails open** | Med ×1 | `specs/2026-08-16-security-agents-tool-visibility-failopen-design.md` |
| 49 | **`lexigram-auth` OAuth2 email binding without `email_verified`** | Med ×1 | `specs/2026-08-16-security-oauth2-email-verified-binding-design.md` |

**§45 — pgvector metadata-filter field interpolation (High).**
`lexigram-vector/src/lexigram/vector/backends/pgvector/filters.py:62-66,84` builds
`f"metadata->>'{field}'"`, `f"metadata ? '{field}'"`, and
`f"(metadata->>'{field}')::numeric {op} {param}"` with the **field name
interpolated raw** (values are parameterized). Field names arrive from
caller-supplied metadata-filter dicts via
`adapters/vector_store.py:161` (`MetadataCondition(field=k, ...)` where `k`
is the dict key) with no allowlist — an attacker-controlled key breaks out
of the JSONB path expression into SQL. Sibling of the Round 8 §42 filter-
expression family; the repo's SQL-identifier remediation
(Column()/Table() wrap, and `lexigram-graph`/`lexigram-search` allowlists)
was never applied to this `lexigram-vector` backend. (This closes the
"no spec yet" gap for Round 4 #20's `lexigram-vector` leg.)

**§46 — KV local backend namespace path traversal → arbitrary `rmtree` (Med).**
`lexigram-storage/src/lexigram/storage/kv/local.py:48-52` sanitizes the key
(`[A-Za-z0-9._-]` filter) but joins the **namespace verbatim**:
`self.base_path / ns / f"{safe_key}{ext}"`; `list_keys` (`:146-147`) and
`clear` (`:162-167`, `shutil.rmtree(ns_path)`) use the same unsanitized
`ns`. `ns="../../x"` escapes the base dir — arbitrary directory read and,
via `clear()`, arbitrary directory deletion on the host. Namespace values
derive from caller-supplied tenant/channel/style ids.

**§47 — MCP server dispatches calls before `initialize` and with no authz (Med).**
`lexigram-ai-mcp/.../server/core.py:75` sets `self._initialized = False`,
`:250` sets it `True` on initialize — but `handle_message` (`:111-160`)
never checks it, so `tools/call`, `resources/read`, `prompts/get`,
`sampling/createMessage` are all serviced for any client that skipped the
MCP handshake (and for any client at all when no auth is wired). MCP spec
requires `-32002` rejection pre-initialize; the flag is write-only.

**§48 — Agent tool-visibility check fails open (Med).**
`lexigram-ai-agents/.../tools/registry.py:282-288`:
`except (RuntimeError, TypeError, ValueError, AttributeError, OSError):
return True` — if the module-graph visibility lookup fails, the tool is
treated as visible. Same manual-check fail-open family as Round 3 §29 /
Round 8 §43: the check exists and is correct on its happy path; every
failure mode silently grants access.

**§49 — OAuth2 binds accounts by unverified email (Med, conditional).**
`lexigram-auth/.../authn/oauth2.py:460-465` `_find_or_create_oauth_user`
looks up / binds by the raw `email` claim with no `email_verified` check.
With a provider (or IdP configuration) that returns unverified emails,
an attacker registering the victim's address at a lenient IdP inherits the
existing account. Google flow mitigates (`google_oauth.py:112-114,131-133`);
severity depends on provider config.

**Verification status — prior spec'd areas confirmed STILL OPEN (2026-08-16):**

| Area (tracker §) | Spec exists | Re-verified evidence | Status |
|---|---|---|---|
| GraphQL limits/introspection (§3.12) | `graphql-design.md` | `di/provider.py:379-389` wires only `RateLimitExtension`; `core/execution.py:358-359` "Would need depth analyzer"; `schema/builder.py:217-218` passes extensions only if added; `IntrospectionConfig` (`config.py:119-137`) consumed nowhere; plus new detail: `core/execution.py:280-300` wraps arbitrary resolver exceptions with `safe=True`/`str(original)`, bypassing `mask_errors` | Open |
| Media upload SSRF + ffmpeg (§3.13) | `media-upload-design.md` | All four fetch sites unguarded (`media_io.py:36-40`, `_asset_io.py:13-17`, `librosa.py:37-41`, `f5_tts_server.py:44-48`); `file://` passthrough at `media_io.py:28-32`; `argv.py:160-163` `drawtext` f-string with raw `font_size`/`color`; 13 servers bind `0.0.0.0` | Open |
| Password reset lifecycle (§5 #22 / `password-reset-lifecycle-design.md`) | exists | Sharpened: `request_reset` (`password_reset.py:76-80`) generates the token but **never persists it** (`update_user(user)` without setting `password_reset_token`) → reset is broken out of the box; `_find_user_by_token` (`:114-130`) scans `list_users(0, 1000)` with plaintext `==` comparison; `confirm_reset` never calls `invalidate_token` | Open |
| Rate limiting (§3.15) | `rate-limit-design.md` | Sharpened: exact-path throttle match `request.url.path in ["/auth/login", "/auth/register"]` (`middleware/auth.py:196`; `throttle.py:23-31`) — `/auth/login/` bypasses throttling entirely | Open |
| AI memory isolation (§4 #16) | `ai-memory-design.md` | `backends/database.py:20-28` `_SELECT_ALL`/`_RECENT` have no owner/session/tenant scoping; `retrieve()` (`:86-117`) loads the whole table and filters in Python | Open |
| AI guard wiring + fail-open (§3.11) | `ai-guard-design.md` | `streaming.py:250-252, 280-282` `except Exception → return True` (input+output); `@guarded` still `return await func(...)` (`decorators.py:46-53`); `AgentsProvider.boot()` (`di/provider.py:289`) still constructs `AgentSafetyInfra` with no guard pipeline | Open |
| Secrets fail-closed backends (§3.7 Task 5) | `secrets-design.md` | `backends/vault.py:54-55, 86-87, 107-108, 122-123` bare `except Exception → return None`/`pass`; GCP/AWS identical | Open |
| Skill sandbox / deserialization (§3.9 F1) | `deserialization-design.md` | `skill_loader.py:139-148` `exec(compiled, local_ns)` with `"os": os` in the namespace; `_get_env` (`:121-129`) passes **full** `os.environ` to subprocesses; `_is_safe_path` checks only `".."` in the resolved path string | Open |

**Verified-clean surfaces (negatives):** webhook HMAC timing-safe compare +
SSRF scheme allowlist landed (`webhook/verification/hmac.py:29-31`,
`url_safety.py`); web CSRF landed with the HTMX carve-out (§3.6 partial is
accurate); CORS wired; session cookies are opaque UUIDs with HttpOnly/Secure/
SameSite; queue/tasks/events/workflow serialize JSON-only (registry-based
dispatch, no pickle/yaml/eval); outbound notification vendors hit fixed
endpoints; storage object backends normalize paths; RAG/MCP URL loaders
consume the SSRF primitive; AI-session store is correctly user-scoped.

**Recurring shapes (§45-49):** §45 is the identifier-injection family from
Round 7 §33 + Round 8 §42 arriving at a third framework data backend
(remediation exists in-package-family: `Column()`/`Table()` wrap,
allowlists — never applied here). §46 is the local-storage twin of the
"sanitize one input, forget the sibling" pattern (key sanitized, namespace
not). §47 is the "state flag set but never read" shape — the permission-
predicate-exists family of Round 5 §26.1 inverted: the gate is a boolean
that nothing consults. §48 is the manual-check fail-open family of Round 3
§29 / Round 8 §43 (correct happy path, every error path grants). §49 is a
conditional account-binding gap whose severity is provider-config-dependent —
the Round 5 §24 token-lifecycle family's email-verification cousin.

---

## 13. Commands (from AGENTS.md)

```bash
uv run ruff check . && uv run ruff format --check .   # lint
uv run mypy lexigram/src/                             # typecheck core
uv run pytest --tb=short --cov-fail-under=80          # aggregate suite
uv run pytest <pkg>/tests/                            # scoped
```

Constraints: no worktrees, no branches unless asked; commit only when
explicitly asked; every changed line must trace to an audit finding.