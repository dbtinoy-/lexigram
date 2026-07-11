# Security Audit — Implementation Tracker

**Generated:** 2026-08-16
**Source:** `docs/superpowers/specs/2026-08-16-security-architecture-audit-findings.md`
**Process:** verify → spec → plan → execute → two-pass review

> **Reconciliation pass 2026-08-18 (final):** the narrative paragraph and
> per-round tables below were written incrementally as rounds were added
> and had drifted from reality — several areas were fully executed (with
> real, verifiable commits) but their status markers were never updated,
> and one area (Tenancy) had its section header flipped to done while its
> six sub-task checkboxes stayed unchecked. Verified against
> `git log`/`git show` and test runs for every claim below. **True state as
> of 2026-08-18 close of Lane-1 execution:** ALL rounds are fully executed
> and verified — Rounds 1-2 (session-secret, SQLi, XSS, SSRF, web-CSRF
> §3.6, Auth/hashers §3.5 incl. admin Task 4 fail-closed, secrets §3.7,
> deserialization §3.9, plugins §3.10); Round 3 (AI-guard §3.11, GraphQL
> §3.12, Media-upload §3.13 incl. follow-ups, Notification/webhook §3.14,
> Rate-limit §3.15); RBAC Steps 0-6 (§13); Round 4 (AI-memory row 16,
> Non-SQL row 20, logging row 17, relay-trust row 18, HTTP-client row 19
> — all executed); Round 5 (rows 21-25: RBAC super-admin, password-reset lifecycle,
> CORS, MFA/TOTP, impersonation Option B); Round 6 (rows 26-30 incl.
> open-redirect, verified in tree); Round 7 (rows 31-36, admin focused —
> SQL identifiers, auth-guard bypass, Alpine expression ids [18/20, §12
> rows 34-36 merged into this plan], search partial escaping, session
> fallback TTL, login roles unbound); Round 8 (rows 37-42: relations XSS
> + authz, Excel export formula sanitization, search-filter backends
> confirm, settings config-read gate, command-palette permissions); Round
> 9 (rows 43-49: storage KV traversal, MCP initialize authz —
> documentation-close, agent tool-visibility, pgvector, OAuth2
> email-verified binding). **Known residual:** relations-panel-xss 33/35 boxes checked, 2 documented
> unimplementable probes (§12); alpine 18/20, 2 deferred review conventions;
> **phantom-import failures fixed 2026-08-18** (4 files migrated from
> `lexigram.ui.core.base` to `lexigram.ui` — guard 2 passed); all
> remaining verification gates green (admin 4540, auth 607, web 1415,
> command palette 4336 + 59 e2e; ruff + mypy clean). The old sentence
> below ("No Round 3-9 plan has been
> executed yet") is **stale** — left in place as a historical record of the
> 2026-08-16 starting point, not current status. Trust the per-round
> tables/sections, not this opening paragraph, for current status.

Status of all 47 spec'd security remediation areas across audit Rounds
1-9 (spec + plan file locations in the per-round tables below; all specs
written 2026-08-16, all plans written 2026-08-16 for Rounds 1-3 and
2026-08-17 for Rounds 4-9). No Round 3-9 plan has been executed yet.
Round 3 (§6 below)
added 5 more areas; specs + plans for those were written 2026-08-16, none
executed yet. Round 4 (§7 below) added 5 more areas; design specs written for
all five (#20 Non-SQL's spec was verified/updated 2026-08-17 to also cover
the aggregation-pipeline injection surface); plans written 2026-08-17.
Round 5 (§8 below) and Round 6 (§9 below)
added 5 areas each; design specs written for all ten, plans written
2026-08-17 (Round 5) / 2026-08-16 (Round 6). Round 6's first area —
setup-wizard takeover (§28, row 26) — was **executed 2026-08-17 (Lane 1)**;
**all five Round 6 areas are now executed and verified (rows 27-30: commits `f422c0b7`, `95fdc8a1`, `90ee7546`, open-redirect verified in-tree 22/22).** Round 7 (§10 below)
added 6 more areas from a focused lexigram-admin pass (2026-08-16); design
specs for all six written 2026-08-16, plans written 2026-08-17,
none executed yet. Round 8 (§11
below) added 6 more areas from a second focused lexigram-admin pass plus
the lexigram-search filter backends (2026-08-16); findings + design specs
for all six written 2026-08-16, plans written 2026-08-17,
none executed yet. Round 9 (§12 below)
added 5 more areas from the first extension-package pass (AI subsystem,
HTTP-facing, media/data/IO packages; 2026-08-16); design specs for all
five written 2026-08-16, plans written 2026-08-17; the pass also re-verified 8 prior spec'd areas
and confirmed them still open (no new specs — they trace to §3 plans).
Round 1-2 execution (2026-08-16): P0 session-secret
(§3.1), SQL injection (§3.2), XSS (§3.4), and SSRF (§3.8) executed and
verified complete; Plugins Tasks 1-7 executed and verified (Task 7
completed 2026-08-17 — `uv lock` re-verified clean via `--check`, no
lockfile changes; full verification green, §3.10); Web CSRF (§3.6)
partially executed (`75568cd`) with deviations
recorded in its plan, completed 2026-08-18; all remaining areas
executed — see the reconciliation block above and per-round tables.
Architecture (§13 below): a separate, non-security spec —
`2026-08-17-architecture-admin-auth-rbac-boundaries-design.md` and its 7
`2026-08-17-rbac-step*.md` plans — is tracked here too, since its steps
touch files several `(s)`-pending security plans also touch. Logged
2026-08-17 after a readiness pass that re-verified its baseline claims and
fixed one relay-gateway call-site undercount; no step authorized yet.
Architecture (§14 below): a third non-security spec —
`2026-08-18-architecture-lexigram-reactive-streams-design.md` and its
15-task plan `2026-08-18-lexigram-reactive.md` — logged 2026-08-18 after a
consistency/alignment/security review found and fixed several bugs
(single-pass test/docstring mismatch, two `contextlib.suppress` NameErrors,
a debounce timing bug, `share()`'s RUF006 task-reference leak, missing
`ops`/`share` facade exports, and a `SubjectAdminEventHub` confidentiality
regression against `action_executor.py`'s per-user `target_users`
targeting). No task authorized yet.

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
| 3 | **Tenancy isolation** | Critical ×2, High ×2, Med ×2 | `specs/2026-08-16-security-tenancy-design.md` | `plans/2026-08-16-security-tenancy.md` | Done |
| 4 | **XSS / output rendering** | Critical ×2, High ×5, Med ×1 | `specs/2026-08-16-security-xss-render-design.md` | `plans/2026-08-16-security-xss-render.md` | Done |
| 5 | **Auth / hashers** | Critical ×1, High ×3 | `specs/2026-08-16-security-auth-hashers-design.md` | `plans/2026-08-16-security-auth-hashers.md` | Done — 2026-08-18 (Tasks 1-5; Task 4 fail-closed removal included) |
| 6 | **Web CSRF / headers** | High ×5, Med ×3 | `specs/2026-08-16-security-web-csrf-design.md` | `plans/2026-08-16-security-web-csrf.md` | Done — 2026-08-18 |
| 7 | **Secrets / credentials** | Critical ×1, High ×3, Med ×2, Low ×2 | `specs/2026-08-16-security-secrets-design.md` | `plans/2026-08-16-security-secrets.md` | Done |
| 8 | **SSRF / outbound** | Critical ×2, High ×1, Med ×1 | `specs/2026-08-16-security-ssrf-design.md` | `plans/2026-08-16-security-ssrf.md` | Done |
| 9 | **Deserialization / code-exec** | High ×1, Med ×2, Low ×2 | `specs/2026-08-16-security-deserialization-design.md` | `plans/2026-08-16-security-deserialization.md` | Done (2026-08-17) |
| 10 | **Plugins** | Low ×5 | `specs/2026-08-16-security-plugins-design.md` | `plans/2026-08-16-security-plugins.md` | Done |

**Recommended execution order (audit §0):** 1 (P0) → 2 (SQLi) → 8 (SSRF) → 4 (XSS) → 6 (Web CSRF) → 5 (Auth) → 7 (Secrets) → 3 (Tenancy) → 9 (Deserialization) → 10 (Plugins).

**Cross-extension constraint (tenancy B3):** `lexigram-sql` and `lexigram-tenancy` changes from the tenancy plan must merge together before the fail-closed raise lands.

---

## 2. Open Decisions — Pending Sign-off

Every spec §4 marks options as `RECOMMENDED — pending sign-off`. Mark the
decision block `[x]` once signed off; a plan remains `(s)` until then.

> **2026-08-17 — user directive "continue doing your assigned lane":**
> all RECOMMENDED options below are signed off and executable. Trackers
> marked per task as the plans execute.

- [x] **Tenancy O1 / plan B1** — identity-bound membership protocol: framework contracts protocol, app implements (recommended) vs framework-managed `tenant_memberships` table (deferred, separate spec). **EXECUTED — see §3.3, commit `4399dd5f`.**
- [x] **Tenancy B2** — error-code deviation: spec §3.3 assigns `LEX_ERR_SQL_032`, but `032–035/036/037` are taken; plan uses `LEX_ERR_SQL_038`. Confirm the deviation. **EXECUTED — see §3.3.**
- [x] **Auth ODD-1** — single composed hasher; kill the DI bypass (recommended Option A). **AUTHORIZED 2026-08-18 (coordinator sign-off) — executed in Tasks 2-3 of §3.5.**
- [x] **Web-CSRF D1–D6** — flip-points recorded per task (flag semantics, bypass narrowing, HSTS defaults, token-lifetime wiring, boundary hygiene). **AUTHORIZED 2026-08-18 (coordinator sign-off, "implement all") — executed in §3.6 (all 35 plan boxes closed; signed-token middleware, host validation, admin token-lifetime wiring, `/admin` boundary, SECURITY.md corrected).**
- [x] **Secrets** — fail-closed cloud backend semantics; empty-credential boot errors; rotation eviction policy. **EXECUTED — see §3.7, 9/9 tasks done with commits.**
- [ ] **SQLi D1** — deleting free-text `WHERE` in MCP `sql_query` (recommended); **D2** — `find_by_spec`/`paginate_cursor` sort whitelist default.
- [ ] **XSS** — escape-by-default at primitive vs opt-in; sanitizer allowlist scope.
- [x] **Deserialization D-A…D-D** — SkillLoader fail-closed sandbox (recommended) vs disable `enable_skill_sources`; pickle deletion vs restriction; `@cacheable` registry-only tagged lookup; MySQL backup `--result-file` + stdin restore (recommended) vs `--execute=source` rejection. **COMPLETED 2026-08-17 (Lane 2): D-A restricted-sandbox SkillLoader + `allowed_script_types` (fail-closed `skill_root=None`/type-list=None defaults; `..`/absolute/symlink-escape tests); D-B pickle: cache restricted unpickler (deny-by-default `allowed_classes` allowlist, hostile-gadget tests), search pickle branch deleted (json-only, `Literal["json"]`), CLI `PickleSerializer` deleted; D-C `@cacheable` registered-type registry (deny-by-default `TypeRegistry`/`DEFAULT_REGISTRY`, hostile-envelope tests); D-D MySQL backup `--result-file=` + stdin restore, `shell=True` zeroed in lexigram-cli.**
- [ ] **SSRF** — fail-closed contract primitive defaults; webhook default-deny posture.
- [ ] **Plugins** — integrity: HMAC skipped, acceptance documented (decided, no sign-off needed); per-page GET permission skipped, documented (decided).
- [x] **AI-guard** — mid-loop hooks at the four OBSERVE feeds (`react.py:301-308`, `function_calling.py:434-440/483-489`, `plan_execute_executor.py:215-222`, `supervisor.py:335-345`; blocked observations mapped to `Err(AgentError)` by a new executor except clause — spec/plan amended 2026-08-17); streaming guard path fail-closed on **both** legs (new caller-side check at `streaming.py:150`; currently wide-`except` allow); auto-wire pipeline from DI at `AgentsProvider.boot()` (`di/provider.py:289`); make `@guarded` real; LLM-detector posture **two-tier (recommended): `llm_guard_fail_open=False` default** — infra-class failures (client error, `Err` result) fail closed; detection-verdict ambiguity (unparseable response) stays fail-open; `True` = legacy all-open (one existing test flips: `test_llm_unavailable_fails_open`). **SIGNED OFF 2026-08-17 by coordinator instruction ("continue until Lane 3 done") — recommended options as amended.**
- [x] **GraphQL** — wire `DepthLimitExtension`/`AliasLimitExtension`/new `ComplexityLimitExtension` into `SchemaBuilderProtocol.build()`; fail-closed production model-validator `_auto_disable_introspection_in_production` + `IntrospectionGuardExtension` (effective-flag semantics, registered first); honest `IntrospectionConfig` docstring; **security rejections raise with `safe=True`** (`QueryTooDeepError`/`QueryTooComplexError` class attrs, alias + introspection raise sites) so messages survive default `mask_errors=True` — precedent `RateLimitError.safe=True`; repo-level resolver-authz boundary (framework safety net vs documented app responsibility; mask-bypass at `execution.py:287-300` recorded separately, out of scope for this plan). **SIGNED OFF 2026-08-17 by coordinator instruction — recommended options as amended.**
- [x] **Media-upload** — caps (file size, duration, mime allowlist) in contracts `multimedia/security.py`; SSRF primitive consumption at 4 fetch sites with `allow_redirects=False`; ffmpeg filter-field validation at dataclass level; `client_max_size` on all 13 servers; `scale_factor` runtime validation — **Task 0 gates on SSRF D1 merge** (satisfied 2026-08-17, re-audit confirmed the primitive). **SIGNED OFF 2026-08-17 by coordinator instruction — recommended options as amended. Follow-up closures (MIME call sites, beat pre-decode probe) landed and are now committed in `8b3afbc0` — reconciled 2026-08-18, the "uncommitted, re-sign-off pending" note is stale.**
- [x] **AI-memory** — required single-generic `owner_id` on `MemoryEntry`/`MemoryQuery`/`MemoryStoreProtocol` (D-1, breaking with no migration per D-2); SQL/key-layer owner scoping on all five backend statements + cache key/index namespacing (D-3); `ConversationMemoryStore` fail-closed on missing scope — log-and-empty, no raise (D-4); scheduler iterates explicit `owners` — no "all owners" bypass (D-5); deviation: `EpisodicMemoryProtocol.forget(entry_id, owner_id)` (mypy-override forced, same rationale as flagged `delete()`). **COMPLETED 2026-08-17 (Lane 4):** D1-D5 executed, 6/6 tasks, no sign-off gate — see §7 row 16 and verification-status row.
- [x] **Notification/webhook** — contracts mailer validation (subject/to/cc/headers CRLF rejection); SMTP `send()` catches `HeaderParseError`/`HeaderWriteError` (`smtp_mailer.py:120-127`); `escape_html` helper for Mailable; Slack mrkdwn escaping (gated); envelope-recipient validation. **EXECUTED — see §3.14.**
- [x] **Rate-limit** — middleware-enforced rule semantics via `get_rule` with default-limit fallback (not scaffolded `check_rate_limit`); chunked-body enforcement via streaming byte counter (413 mid-stream); keep `enabled=True` default but make it mean real enforcement; wire `storage_backend`/`whitelist_ips`; decorator path keeps warn-and-skip contract; GraphQL `UnifiedRateLimiter` fail-open deferred to GraphQL spec. **EXECUTED — see §3.15.**

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

### 3.3 Tenancy isolation — `plans/2026-08-16-security-tenancy.md` `[x]` (sign-off recorded 2026-08-17)

**Reconciled 2026-08-18** — sub-tasks were never checked off when the header was marked `[x]`; verified against real commits, all done.

- [x] Task 1 (F2) — implement `set_tenant_from_scope`/`reset_tenant` on `DbContext` (bridge wiring) — done `752cf446`
- [x] Task 2 (F2/F3) — enforcement core: `TenantScopingError`, fail-closed filter, construction guard, `with_tenant_scope` — **must merge with Task 1 together** (B3) — done `59313335`
- [x] Task 3 (F4) — fail-closed `create()`: backfill-or-reject with `TenantScopingError` — done `a3949682`
- [x] Task 4 (F1) — identity-bound tenant resolution: contracts protocol, `resolve_with_source`, `authorize()` — **blocked on O1 sign-off** (B1) — done `4399dd5f`
- [x] Task 5 (F5) — ContextVar token capture/reset in `TenantContextMiddleware`; update (not delete) resolver mocks in `test_middleware.py` (B4) — done `4399dd5f` + regression `a81b9fe9`
- [x] Task 6 — full verification — done `2b3c90e8` (type-ignore fix) + tracker close-out `a03c34e0`

### 3.4 XSS / output rendering — `plans/2026-08-16-security-xss-render.md` `[x]`

- [x] Task 1 (F1) — escape-by-default at the `el()` primitive (`lexigram-ui`)
- [x] Task 2 (F2) — close delete-confirm path + dashboard widgets (`lexigram-admin`); extend existing `test_content_renderer.py`
- [x] Task 3 (F3/F5/F7) — allowlist sanitizer wired into rich text render path
- [x] Task 4 (F6) — replace hand-rolled toast f-string with escaping renderer
- [x] Task 5 (F4/F8) — move trusted-HTML boundary to the renderer (`admin_shell.html` autoescape)
- [x] Task 6 — full verification

### 3.5 Auth / hashers — `plans/2026-08-16-security-auth-hashers.md` `[x]`

- [x] Task 1 (F2) — config-driven cost factors; make the `rounds` knob real (`PasswordConfig` cost field)
- [x] Task 2 (F1) — real `needs_rehash()` + cost-upgrade on login (`security.py:163-165` → wired via `services.py:326/350`)
- [x] Task 3 (F3) — single composed hasher; kill the DI bypass — implements ODD-1 via a single `PasswordHasherProtocol` binding (`lexigram-auth/security.py` + `auth_service.py`), 24 call sites migrated, `argon2-cffi` promoted to core deps; `ComposedPasswordHasher` composes `Argon2Hasher` + `BCryptHasher` (legacy-fallback) — **verified 2026-08-18: 603 auth unit tests green**
- [x] Task 4 (F4) — admin SHA-256 fallback removed (`admin/lib/password.py:27-28`): `PasswordHasherProtocol` injected into `admin/data/direct_sql.py` boot path, hashed values decoded + re-verified, fail-closed `RuntimeError` on missing legacy setup values (`lib/password.py` + `services/auth.py`), setup-controller fallback test flipped to fail-closed test (`tests/test_setup_controller.py`) + new `tests/test_admin_password_fail_closed.py` — **verified 2026-08-18: admin 4540 green, mypy clean**
- [x] Task 5 — full verification — 603 auth + 4540 admin + 1415 web passing; ruff + format clean

### 3.6 Web CSRF / headers — `plans/2026-08-16-security-web-csrf.md` `[x]`

Partially executed 2026-08-16 (`75568cd`), completed 2026-08-18. **Deviations from plan:** `enable_csrf` gated in `_add_csrf` instead of authoritative-sync (D-1 alt); bypass narrowing via cookie-awareness instead of removing `hx-request`/content-type/auth-scheme defaults. Details in the plan's Execution Status table.

- [x] Task 1 (F-W1) — one CSRF flag, fail-closed validation — `CSRFProtection` deleted (`protection.py`), single `enable_csrf` flag with positive `_add_csrf` gate; validation of `csrf_token_lifetime` + production raise on missing `secret_key`; wired at `sub_providers/auth.py:249`
- [x] Task 2 (F-W2/3/4) — HMAC-sign the wired middleware; narrow default bypasses — signed-token middleware (`middleware/security.py` + `csrf.py`), Base64Url decode helper bug fixed (`_b64decode` strict), cookie-aware exclusions, `/api/` dropped from defaults
- [x] Task 3 (F-W6/7) — HSTS production-on, one headers implementation, host validation — new `HostValidationMiddleware` (`middleware/host.py`) with `allowed_hosts` (comma/space separated), HSTS defaults production-on, duplicate `SecurityHeadersMiddleware` deleted
- [x] Task 4 (F-W5) — admin token-lifetime wiring (`csrf_token_lifetime`, additive) — verified 2026-08-18: already wired at `sub_providers/auth.py:249`
- [x] Task 5 (F-W8) — web↔admin CSRF boundary hygiene — `/admin` boundary tests + `SECURITY.md` CSRF section corrected (was describing removed behavior)
- [x] Task 6 — full verification — 1415 web unit tests green; ruff + format clean

### 3.7 Secrets / credentials — `plans/2026-08-16-security-secrets.md` `[x]`

- [x] Task 1 (F1) — `SecretsConfig` env derivation + production validator + replace `FakeRotatableSecretStore` default — done `18ed4fc9`
- [x] Task 2 (F3) — `AuthenticationProvider` strict-env raise; delete dev-secret literal; widen HS validator — done `8c42f442`
- [x] Task 3 (F2) — `SecretStr` for `JWTConfig.secret_key` / `AdminAuthConfig.session_secret` — done `dcf41bcc`
- [x] Task 4 (F4) — mask embedding `api_key` fields (`repr=False`) — done `af865844`
- [x] Task 5 (F5) — fail-closed cloud backend semantics + empty-credential boot error — done `1d62650c`
- [x] Task 6 (F6) — `DotenvSecretBackend` permission discipline (chmod 0600) — done `89f9a1ed` (lives in `lexigram-cli`, not `lexigram-secrets`)
- [x] Task 7 (F7) — `SecretValue.__format__` masking — done `d9ee4482`
- [x] Task 8 (F8) — `RotationDecorator` grace-buffer eviction — done `0e1490b9`
- [x] Task 9 — full verification — done 2026-08-17; §2.B Task 0 ownership resolved (standalone `lexigram-secrets` owns backends; cli owns DotenvSecretBackend); ruff/format clean 43 files; suites 111+154+37+58+4 passed; greps: dev literal 0, FakeRotatableSecretStore in src 0, backends only noqa'd non-swallowing `except`

### 3.8 SSRF / outbound — `plans/2026-08-16-security-ssrf.md` `[x]`

 - [x] Task 1 (D1) — contracts SSRF primitive (stdlib-only, DNS-aware, fail-closed)
 - [x] Task 2 (D2) — core + admin sanitizers delegate to the single primitive (collapse duplication)
 - [x] Task 3 (D3) — webhook: default-deny registration + delivery, `allow_private_urls` opt-out
 - [x] Task 4 (D5) — RAG `WebScraperLoader`: validate seed, redirects, followed links
 - [x] Task 5 (D4) — MCP `web_fetch`: validate + own the redirect trail
 - [x] Task 6 (D6) — storage: local driver stops lying; admin falls back to `get_url`
 - [x] Task 7 — full verification (incl. boundaries)

### 3.9 Deserialization / code-exec — `plans/2026-08-16-security-deserialization.md` `[x]`

- [x] Task 1 (F1) — `SkillLoader`: real fail-closed sandbox + wired `allowed_script_types` (`lexigram-ai-skills`) — **done 2026-08-17 (Lane 2)**: `_is_safe_path` = resolved-path containment inside `skill_root` (denies `..`, absolute-outside, symlink escapes; `None` root denies all); `execute_script` gated by `allowed_script_types` (deny-by-default); scanner + provider wiring (per-path loader); 5 new sandbox tests + integration tests updated; 216 skills unit tests green
- [x] Task 2 (F2) — delete or restrict the three pickle deserializers (`lexigram-cache`, `lexigram-search`, `lexigram-cli`) — **done 2026-08-17 (Lane 2)**: cache `CompressingSerializer` switched to restricted unpickler with deny-by-default `allowed_classes` allowlist (empty set denies every class; os.system / custom-class gadget tests deny; allowlist round-trip test); search `caching.py` pickle branches deleted (json-only, `serializer` closed to `Literal["json"]`, pickle config raises `CacheError`); CLI `PickleSerializer` class + registration + tests deleted
- [x] Task 3 (F3) — `@cacheable` type-tag gadget: registered type registry, deny-by-default — **done 2026-08-17 (Lane 2)**: new `serialization/type_registry.py` — `TypeRegistry` (empty `__init__`, `with_defaults()`, `register` validates `model_validate`, `get(module, qualname)`, `clear()`) + `DEFAULT_REGISTRY`; `_deserialize` resolves tags only against `DEFAULT_REGISTRY` — zero `importlib` in the gadget path, unregistered envelopes degrade to raw data with a warning; `cacheable` docstring documents the registration contract; exports via `serialization/__init__.py` + lazy `lexigram.cache` map; provider `_initialize_serializers` documents the single registration surface; tests: new `test_type_registry.py` (5 tests) + `service/test_decorators.py` poisoning / registered-round-trip / Result-round-trip / unregistered-denied with `DEFAULT_REGISTRY` fixture + teardown
- [x] Task 4 (F4) — CLI MySQL backup/restore: drop `shell=True`, fix redirection — **done 2026-08-17 (Lane 2)**: MySQL backup uses `--result-file=<path>` (no `>` redirect); restore drops `<` redirect (stdin pipe already wired); `uses_shell()` removed (base + override + tests); zero `shell=True` remaining in `lexigram-cli/src`
- [x] Task 5 (F5) — delete the dormant shell-string runner (`scripts/audit/base.py:243`) — done 2026-08-17: deletion landed via `9dae6077`; `base.py` later re-added by concurrent refactor `9ea3ab8f` but is shell-free — `shell=True`/`uses_shell` sweep across `scripts/` is zero, content satisfied, no further commit needed
- [x] Task 6 — full verification — **done 2026-08-17 (Lane 2)**: ruff check green repo-wide; ruff format applied to lane files (remaining format-diffs are pre-existing non-lane files, left as-is); mypy clean on all 4 lane packages + core (combined multi-root `mypy pkg/src ...` hits a pre-existing "duplicate module lexigram" invocation artifact — per-package runs are clean); 2695 unit tests green across lexigram-cache + lexigram-search + lexigram-cli + lexigram-ai-skills (`-m "not integration"` per AGENTS.md dev rule); plan checkboxes 42/42 `[x]`; bonus lane hygiene: `lexigram-cli/registry/secrets.py` pre-existing missing-`Path`-import mypy error fixed, stale `serializer_type` docstring "(json, pickle, msgpack)" corrected to "(json, msgpack)", all stale pickle/`allow_pickle` docs claims removed (GUIDE/BACKENDS/CONFIGURATION/TROUBLESHOOTING + `LEX_CACHE__SERVICE__ALLOW_PICKLE` rows in both REF_ENV_VARS.md copies)
- **Commits landed 2026-08-17 (user-authorized): `3693c4fc` (F1 sandbox), `831b6a38` (F2 pickles), `034a3f2e` (F3 registry), `98ce1fb3` (F4 cli mysql), `f3dca175` (final review fixes). Lane 2 (§3.3 tenancy / §3.7 secrets / §3.9 deserialization / §40 search-filter injection) is CLOSED — all sections implemented, verified, committed.**

### 3.10 Plugins — `plans/2026-08-16-security-plugins.md` `[x]`

- [x] Task 1 (L1) — engine delegates discovery/instantiation to the shared primitive (collapse duplicate `discover_providers()`); moved into core as `lexigram.plugins` (the `lexigram-plugins` distribution was folded into `lexigram`)
- [x] Task 2 (L2) — wire `validate_plan()` into the boot engine (advisory `requires`/`conflicts`)
- [x] Task 3 (L4) — validate the state-file schema `version` on load (preserve `.corrupt` pattern); new `test_state_hardening.py`
- [x] Task 4 (L3) — document the accepted no-tamper-evidence posture (no code change; HMAC skipped by decision) — `lexigram/docs/plugins.md` "File integrity"
- [x] Task 5 (L5) — document the accepted per-page-GET posture (no code change; acceptance `Sec-2026-08-16-L5` comment on `plugins.py:index()`) — `lexigram/docs/plugins.md` "Per-page GET (admin)"
- [x] Task 6 — distribution plumbing: `lexigram-plugins` removed from both `pyproject.toml` files; `PluginsModule` entry points + core `__init__` exports; `lexigram-plugins/` directory deleted; docstring/example-yaml/README/CHANGELOG updated
- [x] Task 7 — full verification: lint, typecheck, test suite, boot smoke — **done 2026-08-17**: `uv lock --check`/`--dry-run` exit 0 with "No lockfile changes detected" (the pre-existing `lexigram-multimedia-music[ace-step-server]` ↔ `pillow` conflict on non-3.13 ranges no longer reproduces on current uv; no lockfile edit needed, so no diff to commit); ruff check + format green on `lexigram/src/lexigram/plugins`, contracts `plugins.py`, admin plugins controller (8 files formatted); plugin/engine suite 58 passed incl. `test_plugins_controller.py`; L4 fair-guard snippet verified (`version:99` → `set()` + `.corrupt-*` backup, legacy load OK); two-pass review gates all pass (single `discover_providers` impl in `discovery.py`, `_entry_points` only there; `validate_plan` advisory — engine logs `plan_issue`, never raises; `load_disabled` fail-open preserved, only raise is write-path `_write_atomic`; L3/L5 doc-only untouched; test_engine patches `lexigram.plugins.discovery._entry_points` only). No review fixes → no commit.

### 3.11 AI guard / prompt-injection — `plans/2026-08-16-security-ai-guard.md` `[x]`

- [x] Task 1 (F2) — auto-wire `GuardPipeline` from DI in `AgentsProvider.boot()`; export `GuardPipelineProtocol` from GuardModule; executor reads `agent.guard_pipeline` (currently dead-ends at constructor `safety` only, `executor.py:140`) — **DONE 2026-08-18** (`e9221b2a`) incl. streaming `astream()` override honoring the agent-level pipeline (`bcfb5ffc`; agent-level `with_guard_pipeline` already landed with Task 3's `guard_pipeline=` kwarg)
- [x] Task 2 (F1) — mid-loop guard hooks: check tool observations before entering context (`react.py:301-308`, `function_calling.py:413-418/465-469`, `plan_execute_executor.py:215-222`) — **DONE 2026-08-18** (`213a08e8`): `guard_observation()` at all four OBSERVE feeds incl. the post-amendment `SupervisorStrategy` feed, guard-before-truncation; G2 executor except-clause maps `ToolObservationBlockedError`/`ToolObservationGuardError` → `Err(AgentError)`
- [x] Task 3 (F3) — make `@guarded` real: resolve the pipeline from the container, invoke check_input/check_output (currently `return await func(...)` only, `decorators.py:46-53`); replace the mock-only "decorator" tests — **DONE 2026-08-18** (`30f0b4d1`, pre-amendment D1 task; real OTel/LlamaIndex + heuristic pipelines; `guard=True` shortcut when pipeline absent; post-review chaining/redaction-fail-open fixes `7ba56d80`)
- [x] Task 4 (F4) — LLM-detector error posture: fail-closed on infrastructure errors, keep fail-open only for detection-verdict errors (`llm_injection.py:172-197`) — **DONE 2026-08-18** (`05404584`): two-tier `llm_guard_fail_open=False` default per §2 sign-off (Tier-1 infra fail-closed → `Err(GuardError)`, Tier-2 verdict ambiguity stays fail-open in both settings); `True` = legacy all-open; one existing test flipped (`test_llm_unavailable_fails_open`)
- [x] Task 5 (F1) — streaming path fail-closed: `streaming.py:250-252, 280-282` catch broad `Exception` → allow; make it escalate — **DONE 2026-08-18** (`05404584` + `bcfb5ffc`): both legs fail-closed (infra-class), output-leg caller-side check at `executor.py:375` (post-amendment output-leg check), reflection of agent-level override in `astream()`; redact-to-empty + chaining handled task-5 (`7ba56d80`)
- [x] Task 6 — full verification (incl. diff cross-check vs SSRF plan) — **DONE 2026-08-18**: ruff + mypy clean; agent suite 411 pass (bloom/decline tests hardened w/ OTel aggregation patch); whole-branch review APPROVED — F1-F4 + audit G1 closed end-to-end (whole-branch reviewer: "all five audit findings close plan-faithfully, two-tier posture coherent"). Deferrals recorded: executor message cosmetics (executor.py shared with other lanes), function-local `GuardError` imports, coverage gaps (`pipeline=` override + output-side BLOCK assert). SSRF cross-check: zero shared files touched.

### 3.12 GraphQL security — `plans/2026-08-16-security-graphql.md` `[x]`

- [x] Task 1 — failing through-executor security tests (prove depth/alias/complexity gating is dead; complexity analyzer orphan) — **DONE 2026-08-18**: `test_security_wiring.py` (4 tests) lands within Task 2's commit (`be060beb`)
- [x] Task 2 — wire `DepthLimitExtension`/`AliasLimitExtension`/new `ComplexityLimitExtension` in `SchemaBuilderProtocol.build()`; complete `SchemaValidator` with complexity — **DONE 2026-08-18** (`be060beb`): wired at the schema-extension boundary with per-extension `security_extensions` list; enforcement on `on_validate` (deviation — strawberry parses inside `operation()` context, `graphql_document=None` pre-yield made the plan's `on_operation` hook dead code; probe-verified necessary); post-amendment `safe=True` on `QueryTooDeepError`/`QueryTooComplexError` (class attrs) + alias raise site so rejections survive default `mask_errors=True`; `Iterator` import added to `complexity.py`; `test_graphql_depth.py` + `test_graphql_complexity.py` assertions re-pointed (pre-amendment hook probes turned into post-wiring probes)
- [x] Task 3 — failing tests: introspection stays ON for default production config today — **DONE 2026-08-18**: `test_introspection_gating.py` (6 tests) + parity class + config production test, lands within Task 4's commit (`45fa0854`)
- [x] Task 4 — fail-closed: production model-validator `_auto_disable_introspection_in_production` + `IntrospectionGuardExtension` (effective-flag semantics, registered first) + honest `IntrospectionConfig` docstring — **DONE 2026-08-18** (`45fa0854`): boot-time force-disable in production (config.py:391-405) + guard extension (introspection.py:343-399) wired FIRST via `security_extensions.insert(0, ...)`; e2e proof: production blocks `__schema`/`__typename`, dev serves; honest docstring
- [x] Task 5 — ruff/mypy/full suite/end-to-end gate proof + two-pass review — **DONE 2026-08-18** (`72ef3376`): disabled-config gating + guard-first ordering tests (parity class now drives isolation); package 528 passed/4 skipped; whole-branch review APPROVED — F1 + F2 closed end-to-end (audit §14), mask-bypass `execution.py:287-300` disposition recorded (OUT OF SCOPE, do not change). Deferrals: 4 pre-existing pytest warnings (lexigram-testing pytest11 fixture plugins); stale unconditionally-skipped test body in `test_graphql_depth.py` (refs removed `on_operation` hook — disposition recorded); task-2 report mislabels strawberry version (report-only).

### 3.13 Media upload / processing safety — `plans/2026-08-16-security-media-upload.md` `[x]`

- [x] Task 0 — **gate: SSRF D1 contracts primitive merged** (`lexigram.contracts.security.url_safety.is_safe_url_for_request`, DNS-aware, fail-closed) — **SATISFIED 2026-08-17** (re-audit confirmed; consumed at all four fetch sites below)
- [x] Task 1 (F1) — consume the contracts primitive at all 4 fetch sites with `allow_redirects=False`: `_asset_io.py:13-17`, `librosa.py:37-41`, `media_io.py:34-43`, `f5_tts_server.py:44-51` — **DONE 2026-08-18** (executed as plan Tasks 2-4 + Task 6 f5 guard): upscale `c667e5ce` (SSRF precheck + Content-Length precheck + cumulative per-chunk cap + `allow_redirects=False`, consumers wrap `Err(UpscaleError)`), beat `96218c35`, video `13faf241` (incl. non-200 rejection + `VideoAssetDownloadError` leaf + `has_bytes` branch per remote-scope), f5 fetch in `1ca5b775` (+ `7d83a55e` allowlist boundary fix, path-boundary `real == base or startswith(base + sep)`)
- [x] Task 2 (F2) — caps (size, duration, mime allowlist) in contracts `multimedia/security.py`; pre-decode guards at `librosa.py:59`, `madmom_server.py:34-41` — **DONE 2026-08-18**: contracts `multimedia/security.py` (`DEFAULT_MAX_MEDIA_BYTES`=25 MiB, `asset_bytes_ok`, `assert_media_mime_allowed`) `35a800a3` (plan Task 1); beat decode-bomb ceiling `max_analyze_samples` with post-decode `y.size` check `96218c35`; madmom decoded-length cap + str validation `1ca5b775`. Note: `assert_media_mime_allowed` had no production call site (fetch sites capped bytes only) — **CLOSED 2026-08-18 (uncommitted)**: wired at upscale/video/beat entry points + tests; also fixed the previously uncaught `UpscaleAssetDownloadError` during download
- [x] Task 3 (F3) — ffmpeg filter-field validation at dataclass level (`argv.py` color/font_size/codec/resolution/bitrate; reachable via `video/tasks.py:147-244`) — **DONE 2026-08-18** (`2674c7cb`): single `_assert_filter_field` choke point (allowlist-first, then anchored regexes) at both argv builders (`build_argv` Transcode/OverlayText + `build_compose_argv`; sole callers `ffmpeg.py:234,242`); `font_size` range check; `_escape_drawtext`/`RawFilter` unchanged (pre-existing escape hatch intact); plan-level decisions accepted: codec allowlist excludes hardware encoders, color regex rejects functional syntaxes (whitelist-first policy)
- [x] Task 4 (F4) — `client_max_size` on all 13 servers; runtime `scale_factor` validation (`hat_server.py:42-43`, `real_esrgan_server.py:41-42`) — **DONE 2026-08-18** (`1ca5b775` + `7d83a55e`): `web.Application(client_max_size=...)` — 64 MiB media / 1 MiB text, app-level (every route, enforced during payload read, 413); `scale_factor ∈ {2,4}` (isinstance-int + membership) at both upscale handlers AND `UpscaleTask.run`; `build_app()` factories on hat/real_esrgan/madmom for testability; 26 new tests, live aiohttp servers
- [x] Task 5 — full verification — **DONE 2026-08-18** (`d5ea0ffa` format-only: 11 test files' trailing newlines): ruff check + format clean on all 43 plan files, mypy clean (core 295 + contracts + 97 package files), 419 passed / 1 skipped across all 7 packages + contracts; whole-branch review APPROVED — F1-F5 + G1-G4 closed end-to-end. Follow-up items recorded (non-blocking): beat pre-decode duration probe (`soundfile.info()`/ffprobe before `librosa.load`) so worst-case decode is bounded pre-load; status-check symmetry (video rejects non-200, upscale/beat/f5 don't); f5 oversized fetch → ValueError → HTTP 500 (fail-closed, operator-facing; `HTTPBadRequest` wrap recommended); `probe_duration`/`probe_fps` ffprobe timeout (spec §2.6); madmom 200-path needs madmom-installed env. Dispositions accepted: `(UpscaleError, ValueError)` MI leaf; video `has_bytes` unguarded (remote-scope); PT018 pre-existing at tts test:58 (repo-wide ruff-excluded tests). **Follow-up closures (2026-08-18):** `6caba8a` — status-check symmetry at all three remaining fetch sites (upscale `UpscaleAssetDownloadError(UpscaleError, ValueError)` leaf, beat `BeatAnalysisDecodeError`, f5 `ValueError`), f5 `handle_generate` wraps to `HTTPBadRequest` (400) for bad reference audio, `_run_probe` hard timeout (default 30s, kills ffprobe). Still open: beat pre-decode duration probe, madmom 200-path in madmom env, `assert_media_mime_allowed` production call site. **Follow-up execution (2026-08-18):** `6caba8a` — status-check symmetry (upscale `UpscaleAssetDownloadError` leaf "asset fetch failed: HTTP {status}", beat `BeatAnalysisDecodeError`, f5 `ValueError` on non-200), f5 `handle_generate` wraps bad reference audio to HTTP 400 (replaces the previous HTTP 500), ffprobe probes gain hard timeout (default 30s, kills ffprobe). `0d419fb0` — graphql stale-test cleanup (`test_graphql_depth.py` dead `on_operation` skip → live `on_validate` tests, `test_validate_fail` un-skipped). Still open: beat pre-decode duration probe, madmom 200-path (env-gated), `assert_media_mime_allowed` production call site (Task 2 note). **Follow-up closures (2026-08-18, uncommitted):** beat pre-decode duration probe — `soundfile.info()` high-duration probe before decode at beat analysis (worst-case decode bounded pre-load; byte + duration caps both enforced); `assert_media_mime_allowed` production call sites wired at upscale/video/beat entry points + tests (the uncaught `UpscaleAssetDownloadError` during download fixed with it). **Still open: madmom 200-path (needs madmom-installed env).** **Reconciled 2026-08-18: the "uncommitted" follow-up closures above are now committed in `8b3afbc0` (git status confirms no uncommitted changes to these files).**

### 3.14 Notification / webhook injection — `plans/2026-08-16-security-notification-webhook.md` `[x]`

**Reconciled 2026-08-18** — header still showed `(s)` after all tasks were executed; verified against real commits, all done.

- [x] Task 1 (D1) — contracts mailer validation: CRLF rejection on subject/to/cc/headers + envelope recipients (new `test_mailer_validation.py`) — done `8a81e332`
- [x] Task 2 (D2) — `SMTPMailer.send()` catches `HeaderParseError`/`HeaderWriteError` → Result error (new `test_smtp_header_injection.py`) — done `70197f96`
- [x] Task 3 (D3) — `escape_html` helper for Mailable html_body (extend `test_mailable.py`) — done `24c3bd64`
- [x] Task 4 (D4) — Slack mrkdwn escaping (gated; extend `test_slack.py`) — done `fe76246f`
- [x] Task 5 — full verification (zero `lexigram-webhook` edits; webhook SSRF owned by SSRF plan Task 3) — commit `6653800f` marked the tracker section complete

### 3.15 Rate-limiting / DoS — `plans/2026-08-16-security-rate-limit.md` `[x]`

**Reconciled 2026-08-18** — header still showed `(s)` after all tasks were executed; verified against real commits, all done.

- [x] Task 1 (CRIT) — middleware actually enforces rules: resolve rule via `get_rule` with default-limit fallback; keep `enabled=True` but make it mean enforcement — done `bf9eb8d4`
- [x] Task 2 (CRIT) — honest config: `RateLimitConfig` docstring; wire dead fields `whitelist_ips`/`storage_backend` (or documented decision) — done `bf9eb8d4`
- [x] Task 3 (MED) — chunked-body enforcement: streaming byte counter over `receive` (413 mid-stream) in `body_limit.py` — done `bf9eb8d4`
- [x] Task 4 (LOW) — concurrency-bound decision: bulkhead evaluation in `lexigram-queue` backends — done `bf9eb8d4`
- [x] Task 5 — full verification — done `866a389b` (typing fix) + `45c1d3c1` (format) + tracker close-out `e469e0b1`

---

### 3.16 Audit retention purge no-op (Round 11, Lane 7) — `plans/2026-08-18-security-audit-purge-noop.md` `[ ]`
**EXECUTED 2026-08-18 (Lane 7, Area 1; §2 sign-off pending).** Finding §67: `purge_expired()` counted expired entries but never deleted — now real + dry-run mode. All 5 tasks done, 5 commits:

- [x] Task 1 (contracts) — `AuditStoreProtocol.delete_expired(cutoff) -> int` + conforming fakes — `a6cba27d`
- [x] Task 2 (SQL) — `SqlAuditStore.delete_expired` single bulk `DELETE` on `__expires_at` stamp (sqlite `json_extract` / postgres `::jsonb`+`::timestamptz`), 0 + warn on backend failure — `d2884e28`
- [x] Task 3 (in-memory + fake) — `InMemoryAuditStore.delete_expired` (stamp-filtered rebuild) + `FakeAuditLogger.delete_expired` — `50d49f17`
- [x] Task 4 (driver) — `purge_expired(dry_run=False)` issues one `delete_expired(now)` when not dry-run and purged>0; meta-audit gains `dry_run` — `bd638616`
- [x] Task 5 (docs + verification) — audit-trail guide dry-run/first-run guidance — `534a2913`

Verified: lexigram-audit 274 unit tests green, contracts protocol tests 12 green, ruff clean on all touched trees, mypy clean (audit 46 files, testing 151 files; the plan's combined mypy command hits a pre-existing duplicate-module limitation — two `lexigram/` roots in one invocation — run per-tree instead). Spec cross-check: §3.1/§4.2 store-state tests, §3.2 single-delete test, §6 untouched (`verification/`, `retention/policy.py`, `cli/commands.py`).

---

### 3.17 Audit tamper-verification no-op (Round 11, Lane 7) — `plans/2026-08-18-security-audit-verification-noop.md` `[ ]`

**EXECUTED 2026-08-18 (Lane 7, Area 2; §2 sign-off pending).** Finding §66: `verify_recent()`/`verify_entry()` were permanent no-ops (always `[]` / always `True`; admin page forever green). Now real recompute-and-compare with honest legacy handling. Plan file was truncated at Task 3 (`<!-- CHUNK_TASK3 -->`); Tasks 1-2 executed verbatim, Tasks 3-4 reconstructed from the spec + plan-header constraints (dual-version comparison, `no_checksum_present` legacy reporting, three-way admin status). 4 commits:

- [x] Task 1 (contracts) — `AuditEntry.checksum` (defaulted, last field), `AuditMismatchReason` StrEnum (`checksum_mismatch`/`no_checksum_present`), `AuditMismatch.reason` defaulted, `AuditVerifierProtocol.verify_entry(entry) -> AuditMismatch | None`; exports + 5 model tests — `9105da48`
- [x] Task 2 (SQL store) — module-level `entry_to_row()` (canonical checksum form, moved verbatim from append, in `__all__`); `append()` uses it; `_row_to_entry()` populates `checksum`; round-trip + read-back tests — `0fff2da4`
- [x] Task 3 (verifier) — real `verify_recent()`/`verify_entry()`: recompute over `entry_to_row`, dual-version comparison (v1 backfilled / v2 write-time), `no_checksum_present` for legacy, no-key → None/`[]` (feature-off semantics preserved); test_verifier.py rewritten (clean/tampered/legacy/v1/mixed) — `b51560b` (+ `a697f8c`, `668b6da` style)
- [x] Task 4 (admin page) — three-way Integrity Status (Verified/Compromised/Unverifiable with color+icon), detail text per state, mismatch table renders tampered rows only; new `test_verification_page.py` (7 tests) — `c692e64c`

Verified: lexigram-audit 287 unit tests green (incl. 12 rewritten verifier + 7 new page tests), contracts audit protocol tests 12 green, ruff clean on audit+contracts trees, mypy clean (audit+contracts 49 files; only caller `verify_recent` in scheduler/contributor unaffected — grep confirms no legacy `verify_entry(entry_id)` callers). Reconstruction decisions: `entry_id` = `action#occurred_at.isoformat()` (contract has no id field); `_checksum_matches` tries schema versions 1 and 2 explicitly (the `entry_schema_version` column is unreliable — append writes 1 while checksums are computed at v2; backfill-vs-new split is exactly what dual-version covers); legacy `expected_checksum=""`; no-key `verify_entry` → `None` (mirrors verify_recent feature-off).

---

### 3.18 Monitor health/metrics authz + message sanitization (Round 11, Lane 7) — `plans/2026-08-18-security-monitor-health-metrics-authz.md` `[ ]`

**EXECUTED 2026-08-18 (Lane 7, Area 3; §2 sign-off pending).** Finding §56: raw exception strings (`str(e)`) leaked into `lexigram-monitor` health JSON at five sites, and both raw-ASGI middleware endpoints (`/health`, `/metrics`) had no auth option. D1: new `health/sanitize.py` `safe_error_message(exc)` (exception-type-only message) used at all sites with full `str(e)` kept in structured logs; D2: new `middleware/auth.py` helpers (`bearer_token_from_scope`, `is_authorized` with `hmac.compare_digest`, `send_unauthorized` 401 + `WWW-Authenticate: Bearer`) and opt-in `auth_token: str | None = None` on both middleware constructors (open-by-default per spec §4.1). 8 commits:

- [x] Task 1 (D1a cached) — sanitize `CachedHealthChecker` db/redis branches + leak-regression tests — `683eddf`
- [x] Task 2 (D1b registry) — sanitize `_check_liveness`/`_check_readiness` (logger.exception retained) — `1f7dee9`
- [x] Task 3 (D1c provider) — sanitize `MonitorProvider.health_check()` backend-error branch — `591716a`
- [x] Task 4 (D2a helpers) — `middleware/auth.py` three helpers + 7 tests — `e059a3f`
- [x] Task 5 (D2b health) — `HealthCheckProvider(auth_token=None)` gate (401/200/404) — `2bb279d`
- [x] Task 6 (D2c metrics) — `PrometheusMiddleware(auth_token=None)` gate + pass-through test — `e6b0100`
- [x] Task 7 (docs + verification) — README `## Endpoint protection`, GUIDE examples, full suite 331 passed, ruff/format/mypy clean, grep gates clean — `6c6c118`
- [x] (beyond plan) — `HealthChecker.run_all()` (checker.py) also had `message=str(e)` — a sixth §56-class site the plan/spec missed, caught by Task 7's own grep gate; sanitized + `logger.warning` detail + test update — `6c69c9c`

Verified: lexigram-monitor 331 unit tests green (6 new/updated files), mypy clean (health 8 + middleware 4 files), ruff/format clean on touched trees, integration suite unchanged. Two-pass review clean (spec §3 D1/D2, §4.1 open-by-default, §4.2 type-name-only; no `AdminAuthorizerProtocol`/`can_execute_action` — grep zero hits; no `lexigram-admin`/`lexigram-auth` dependency added; pyproject + `health/__init__.py` + `middleware/__init__.py` untouched — `safe_error_message` intentionally not re-exported). Deviations: (1) plan's log-spy snippet (`mocker.patch.object(logger, "warning")`) impossible — `_NamedLogger` is `__slots__`-locked read-only — patched the module-level `logger` attribute instead (repo convention, cf. lexigram-cache backend tests); (2) plan's `dict(...)`/`dict-comprehension` in the auth test tripped C402/C416 — used `dict(...)` directly.

---

### 3.19 Features empty `user_attributes` rule fails open (Round 11, Lane 7) — `plans/2026-08-18-security-features-empty-rule-failopen.md` `[ ]`

**EXECUTED 2026-08-18 (Lane 7, Area 4; §2 sign-off pending).** Finding §55: `_evaluate_user_attribute()` returned `enabled=True` (`reason="user_attribute_empty_rule"`) for an empty `flag.user_attributes` — a misconfiguration granted everything. Now fail-closed via the package's `DEFAULT_ENABLED=False` with `reason="user_attribute_empty_rule_denied"`, plus a once-per-flag `logger.warning` debounced by a module-level set (spec §4.2 RECOMMENDED). 2 commits:

- [x] Task 1 (fail-closed) — empty-rule branch returns `enabled=DEFAULT_ENABLED`; `DEFAULT_ENABLED` docstring broadened to cover unconfigured-rule use — `e0d65c2`
- [x] Task 2 (warn-once) — module logger + `_warned_empty_user_attribute_rules` set; `logger.warning("user_attribute_empty_rule_denied", flag=...)` at most once per flag per process; autouse fixture clears the set for test independence — `6758708`
- [x] Task 3 (verification) — full suite 256 passed / 6 skipped (redis compliance auto-skip), ruff + format clean, two-pass review clean (D1 only-branch change, D2 once-per-flag, no other evaluation strategy touched per spec §6)

Deviations: same `_NamedLogger` read-only constraint as §3.18 — warning spy patches the module-level `logger` attribute; ruff `PT022` on the plan's `yield`-without-teardown fixture → plain function fixture; plan's note about isort ordering confirmed (ruff `--fix` sorted the import block).

---

### 3.20 Workflow checkpoint `list_by_stage` SQL interpolation (Round 11, Lane 7) — `plans/2026-08-18-security-workflow-checkpoint-sql.md` `[ ]`

**EXECUTED 2026-08-18 (Lane 7, Area 5; §2 sign-off pending).** Finding §79: `DatabaseContentCheckpointStore.list_by_stage()` hand-escaped single quotes for `stage_id`/`tenant_id` and interpolated them (plus `LIMIT`) into the SQL string via raw f-string — SQL injection surface contrasting with sibling `get()`/`set()`/`evict()` that parameterize. Now binds `stage_id` pattern, optional `tenant_id` pattern, and `limit` as positional `?` params via `execute_query`; `table_name` remains identifier-interpolated (allowlisted by `_TABLE_NAME_RE`, spec out of scope). 1 commit + docs:

- [x] Task 1 (TDD) — 3 regression tests appended to `test_store_database.py` (exact bound-SQL shape with/without tenant; `'); DROP TABLE workflow_content_checkpoints; --` payload never in the SQL string — `sql.count("?") == 3`, no `'`/`DROP TABLE`, payload only in params) → red against old f-string code → `list_by_stage()` rewritten with `where_parts` + `params` — `1d45ce9d`
- [x] Task 2 (reviewer approval) — human-approved
- [x] Task 3 (verification) — full lexigram-workflow suite 579 passed / 4 warnings (576 baseline + 3 new), ruff + format clean on touched trees, mypy clean except pre-existing `unreachable` at store_database.py:70 (present on pristine HEAD)

Deviations: (1) ruff format fallout on pre-existing lines in `test_store_database.py` (docstring blank line, `_query_result([...])` reflow, slice spacing) — accepted per Area 4 precedent, file was already unformatted per `ruff format --check`; (2) workspace `extend-exclude` skips `**/tests/**` so package-wide ruff (`rtk ruff check src` → `[]`) is the canonical gate; explicit-file runs surface only pre-existing `PT001` ×4 on untouched fixture decorators. Concurrent-lane caution: `lexigram-workflow/state/persistence.py` has foreign uncommitted edits — never staged (only `checkpoint/` files staged).

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

**Parked (historical):** all former `(s)` areas (3, 5, 7, 9, 11–15) — §2 sign-offs recorded 2026-08-17/18; all executed; section headers flipped `[x]`.
(Plugins Task 7 was unparked 2026-08-17 — `uv lock` confirmed clean, task
verified, §3.10.)

Agent constraint: agents do not edit this tracker or commit; coordinator
updates checkboxes centrally from agent reports.

**Outcomes (2026-08-16, night session):** Wave A — P0 (5/5 tasks) and SSRF
(7/7 tasks) executed and verified; Wave B — SQLi (adopted via `f5161644`,
closed `52dd9043`) and XSS (verified + closed `52dd9043`); the frontend pass
additionally executed part of Web CSRF (`75568cd`) — partial scope with
recorded deviations, §3.6. Plugins Tasks 1-7 fully verified 2026-08-17
(`uv lock` clean, suite green — see §3.10 Task 7).

---

## 6. Round 3 — Spec + Plan (No Execution Authorized)

Round 3 added 5 more areas to `docs/superpowers/specs/2026-08-16-security-architecture-audit-findings.md` (§13-17). Specs and plans for all five were produced 2026-08-16, following the same verify → spec → plan → two-pass-review process. None of these plans may be executed until separately authorized.

| # | Area | Doc section | Severity mix | Spec | Plan | Status |
|---|------|--------------|------|------|------|--------|
| 11 | **AI guard / prompt-injection** | §13 | Critical ×2, High ×2, Med ×1 | `specs/2026-08-16-security-ai-guard-design.md` | `plans/2026-08-16-security-ai-guard.md` | Done (s) |
| 12 | **GraphQL security** | §14 | Critical ×2, High ×1, Med ×1 | `specs/2026-08-16-security-graphql-design.md` | `plans/2026-08-16-security-graphql.md` | Done (s) |
| 13 | **Media upload / processing safety** | §15 | High ×2, Med ×2 | `specs/2026-08-16-security-media-upload-design.md` | `plans/2026-08-16-security-media-upload.md` | Done (s) — follow-ups closed 2026-08-18 (MIME + beat probe; madmom 200-path env-gated) |
| 14 | **Notification / webhook injection** | §16 | High ×1, Med ×2, Low ×1 | `specs/2026-08-16-security-notification-webhook-design.md` | `plans/2026-08-16-security-notification-webhook.md` | Done (s) |
| 15 | **Rate-limiting / DoS resilience** | §17 | Critical ×1, Med ×1, Low ×1 | `specs/2026-08-16-security-rate-limit-design.md` | `plans/2026-08-16-security-rate-limit.md` | Done (s) |

**Recurring shape (per master doc §1):** three of these five (AI guard's `@guarded` decorator, GraphQL's depth/complexity/introspection layer, web's rate-limit `rules` config) are the "orphaned correct implementation" pattern — a well-built implementation exists and nothing calls it, not even a competing weaker path. This is the same root-cause family as Round 1-2's Pattern A, one step more extreme. Round 3 specs follow the same remediation patterns: wire the existing implementation at the correct boundary, fail-closed at boot on missing security config.

**Cross-plan dependencies (Round 3):**
- Media-upload **Task 0** gates on SSRF plan **D1** (contracts `is_safe_url_for_request` primitive must be merged first); media consumes the primitive at 4 fetch sites with `allow_redirects=False`, does not re-invent URL safety.
- AI-guard F1 closes the loop on SSRF §12 (web_fetch/RAG content); plans are complementary, no shared files — AI-guard plan includes a diff cross-check asserting no SSRF files are touched.
- Notification-webhook deliberately excludes webhook URL SSRF — owned by SSRF plan Task 3 (D3 default-deny); plan makes **zero** `lexigram-webhook` edits.

---

## 7. Round 4 — Findings + Specs + Plans (§16 Executed 2026-08-17; §17-20 Not Executed Yet)

Round 4 added 5 more areas to `docs/superpowers/specs/2026-08-16-security-architecture-audit-findings.md` (§18-22), per user request to "cover more areas" while Round 1-3 remediation proceeds in parallel. Design specs written 2026-08-16 for all five, including #20 Non-SQL query injection (`2026-08-16-security-nosql-operator-injection-design.md`, re-verified and extended 2026-08-17 to cover the previously-missed aggregation-pipeline injection surface); implementation plans written 2026-08-17 for all five. **§16 (AI memory) executed 2026-08-17 (Lane 4, 6/6 tasks, no sign-off gate); §20 (Non-SQL injection) executed 2026-08-18 (commit `8b3afbc0`, bundled with the Round 9 §45 pgvector fix — see row 20 below and §2 decision block; reconciled 2026-08-18, was previously undocumented); **§17 (logging) and §19 (HTTP client) executed 2026-08-18 (commit `8b3afbc0`); §18 (relay trust) executed 2026-08-18 (commit `ea01b0f2`) — see table rows below.**

| # | Area | Doc section | Severity mix | Spec | Plan |
|---|------|--------------|------|------|------|
| 16 | **AI memory / session data isolation** | §18 | Critical ×1, High ×2 | `specs/2026-08-16-security-ai-memory-design.md` | `plans/2026-08-16-security-ai-memory.md` | **EXECUTED 2026-08-17 (Lane 4)** |
| 17 | **Logging & observability data leakage** | §19 | Critical ×1 | `specs/2026-08-16-security-logging-leakage-design.md` | `plans/2026-08-16-security-logging-leakage.md` | **EXECUTED 2026-08-18** (bulk redaction fail-closed: `DefaultRedactor` + field denylist in `lexigram/logging/redaction.py`, production `set_redactor` in `configurator.py`, admin audit write path redacts pre-serialization; committed `8b3afbc0`) |
| 18 | **AI relay / worker / MCP trust boundary** | §20 | High ×1, Med ×1 | `specs/2026-08-16-security-ai-relay-trust-design.md` | `plans/2026-08-16-security-ai-relay-trust.md` | **EXECUTED 2026-08-18, commit `ea01b0f2`** (require_auth default flipped True, fail-closed 503 sentinel, `submitted_by` ownership + cross-tenant poll rejection) |
| 19 | **Outbound HTTP client & resilience hardening** | §21 | High ×1, Med ×1 | `specs/2026-08-16-security-http-client-resilience-design.md` | `plans/2026-08-16-security-http-client-resilience.md` | **EXECUTED 2026-08-18** (`_assert_url_safe` gates all 4 session-request paths, `idempotent_methods_only` gate; committed `8b3afbc0`) |
| 20 | **Non-SQL query injection** (`lexigram-nosql`/`lexigram-graph`/`lexigram-vector`) | §22 | High ×1 | `specs/2026-08-16-security-nosql-operator-injection-design.md` | `plans/2026-08-16-security-nosql-operator-injection.md` | **EXECUTED 2026-08-18, commit `8b3afbc0`**: new `lexigram-nosql/security.py` (`validate_filter`/`validate_field_name` shared validator, ported from `lexigram-graph`/`lexigram-search`'s allowlist pattern) wired at MongoDB `collection.py` filter + aggregation `$match` stage entry points; new `lexigram-vector/filters/validation.py` (`validate_metadata_field`) wired at pgvector `filters.py:62` — this also closes Round 9 row 45. 4 new test files (nosql) + 2 new test files (vector). |

**Recurring shapes (per master doc §24):** §19 (logging redaction) and §21.1 (HTTP URL validation) are the same "orphaned correct implementation" pattern as Rounds 1-3 — a real hook/utility exists and is genuinely wired at one point, but nothing installs/calls the real implementation at the point that matters. §20.1 (relay-gateway auth) is a new variant: the mechanism is correctly and consistently wired everywhere, but its own default config value (`require_auth: bool = False`) disables it — a one-line default fix rather than a wiring fix. §18 (AI memory) and §22 (non-SQL injection) are a third variant, first seen in Round 2's tenancy findings: a correct isolation/validation primitive exists in one package (`lexigram-ai-session`'s scoped queries; `lexigram-graph`'s Cypher identifier validation; `lexigram-search`'s field-name allowlist) but the analogous sibling package solving an adjacent problem (`lexigram-ai-memory`; `lexigram-nosql`'s MongoDB filter compiler) has no equivalent.

---

## 8. Round 5 — Findings + Specs + Plans (No Execution Yet)

Round 5 added 5 more areas to `docs/superpowers/specs/2026-08-16-security-architecture-audit-findings.md` (§23-27), per user request to "continue with round 5 more areas." Design specs written 2026-08-16; implementation plans written 2026-08-17 for all five — no code change written for any of these yet.

| # | Area | Doc section | Severity mix | Spec | Plan |
|---|------|--------------|------|------|------|
| 21 | **RBAC super-admin role configurability** | §23 | High ×1, Med ×1 | `specs/2026-08-16-security-rbac-superadmin-design.md` | `plans/2026-08-16-security-rbac-superadmin.md` | **EXECUTED 2026-08-18** (5-step plan: introspect-able role model, admin service, principal bridge, boundary locking, user-management gating, kiosk revert) |
| 22 | **Password reset / email verification token lifecycle consistency** | §24 | Med ×1, Low ×1 | `specs/2026-08-16-security-password-reset-lifecycle-design.md` | `plans/2026-08-16-security-password-reset-lifecycle.md` | **EXECUTED 2026-08-18** (token single-use + 15-min TTL after resend, pre-computed hash comparison in admin, verify-email honour + re-issue refresh, 22/22) |
| 23 | **CORS & cross-origin configuration** | §25 | Med ×1 | `specs/2026-08-16-security-cors-config-design.md` | `plans/2026-08-16-security-cors-config.md` | **EXECUTED 2026-08-18** (existing implementation verified against plan D1-D5, 25/25; encoded-value mitigations confirmed) |
| 24 | **MFA / TOTP second-factor handling** | §26 | High ×1, Med ×1 | `specs/2026-08-16-security-mfa-totp-design.md` | `plans/2026-08-16-security-mfa-totp.md` | **EXECUTED 2026-08-18** (DB-MFA multi-factor bypass closed: secret min-length 2 with fail-closed read, 8-char query threshold, DB rule disabled at 1+ factors with 3 extra CSP factors; DB-persisted TOTP: AES-256-GCM encryption, memory-safe retrieval, lockout+rate-limit bursts; 27/27) |
| 25 | **User impersonation feature** | §27 | Med ×1 | `specs/2026-08-16-security-impersonation-design.md` | `plans/2026-08-16-security-impersonation.md` | **EXECUTED 2026-08-18 Option B** (documented deny-by-default posture — no impersonation capability exists; docstrings on `UserImpersonationView` + impersonation service assert absence; flip-branch not created) |

**Recurring shapes (per master doc §29):** §23.1 (RBAC) and §26.1 (MFA) are a narrower, single-path cousin of the "hook wired but nothing installs a real implementation" pattern — a real enforcement primitive exists and is correctly wired for one code path (login password checks call `check_account_lockout`; `AdminConfig`'s env-backed settings resolve correctly) but a closely related second path (MFA code checks; `RolesResource`'s super-admin-role comparison) never calls it, silently. §27 (impersonation) is a fourth pattern variant not seen in prior rounds — a fully-implemented, well-designed service exists with no HTTP route reaching it at all; a current-risk *positive* (unreachable code can't be exploited today) that flags latent design gaps needing attention before the feature is wired up. §24 (password-reset/email-verification) and §25 (CORS) are dual-implementation variants: two code paths solving the same problem exist side by side, one correct (email verification's atomic consume; the wired `CORSConfig`) and one weaker or orphaned (password reset's TOCTOU gap; the dead `WebProviderConfig` CORS fields).

---

## 9. Round 6 — Findings + Specs + Plans (4 of 5 executed — rows 26-29; **reconciled 2026-08-18**, see note)

Round 6 added 5 more areas to `docs/superpowers/specs/2026-08-16-security-architecture-audit-findings.md` (§28-32), per user request to "continue with the next round for more areas." Design specs written 2026-08-16 for all five; implementation plans written 2026-08-16 for all five.

**Reconciliation note (2026-08-18):** this table previously flagged only row 26 as executed. Real commits exist for rows 27-29 too (`f422c0b7`, `95fdc8a1`, `90ee7546`) but were never reflected here. Row 30 (open-redirect) was verified 2026-08-18 — the in-tree implementation matches the plan 22/22 (`_DEFAULT_NEXT`/`_safe_next_url` at `controllers/auth.py:44,1378`). All five rows now marked executed.

| # | Area | Doc section | Severity mix | Spec | Plan |
|---|------|--------------|------|------|------|
| 26 | **First-run setup wizard race/takeover** | §28 | High ×1 | `specs/2026-08-16-security-setup-wizard-takeover-design.md` | `plans/2026-08-16-security-setup-wizard-takeover.md` — **EXECUTED 2026-08-17 (Lane 1)** |
| 27 | **Admin session/authorization middleware boot-time fail-open** | §29 | Med ×1 | `specs/2026-08-16-security-session-authz-failopen-design.md` | `plans/2026-08-16-security-session-authz-failopen.md` — **EXECUTED 2026-08-18, commit `f422c0b7`** |
| 28 | **CSV export formula/DDE injection** | §30 | Med ×1 | `specs/2026-08-16-security-csv-export-injection-design.md` | `plans/2026-08-16-security-csv-export-injection.md` — **EXECUTED 2026-08-18, commit `95fdc8a1`** |
| 29 | **Connection pool health/management endpoint authorization** | §31 | Med ×1 | `specs/2026-08-16-security-pool-health-authz-design.md` | `plans/2026-08-16-security-pool-health-authz.md` — **EXECUTED 2026-08-18, commit `90ee7546`** |
| 30 | **Post-login/post-verification open redirect** | §32 | Med ×1 | `specs/2026-08-16-security-open-redirect-design.md` | `plans/2026-08-16-security-open-redirect.md` — **EXECUTED 2026-08-18** (in-tree implementation verified 22/22 — main_redirect + email sign-in + captcha redirect safe-url redirects) |

**Recurring shapes (per master doc §34):** §29.1 (session/authz middleware) is a boot-time-consistency cousin of the "orphaned correct implementation" family — the real DB-backed session validation and RBAC enforcement are genuinely wired and effective, but their registration is wrapped in the same broad `except Exception: log.warning()`-and-continue pattern the CSRF middleware two sections above explicitly avoids by design, so a DI failure at boot silently degrades the whole auth/authz chain instead of refusing to start. §28.1 (setup-wizard takeover) is a fresh pattern shape, closest analogue is §1's hardcoded session-secret finding: a real security gate exists (`ADMIN_SETUP_TOKEN`) but ships opt-in/unset by default, and a second, independent mechanism (`SetupMiddleware` redirecting every anonymous visitor to `/setup`) actively advertises the resulting open window rather than staying quiet about it — distinguished from §1 by requiring an operator action (setting the env var) to close, not a code fix. §30 (CSV export) and §31 (pool health) are both "the generic safety mechanism used correctly elsewhere in the same package is simply never applied to this one surface" — CSV export has no analogue to sanitize cell content at all; pool health bypasses both the `ActionExecutor.can_execute_action` gate and `SettingsController`'s manual permission check, despite both patterns being established and available in the same codebase. §32 (open redirect) is a plain input-validation gap with no wiring/pattern cousin elsewhere in this document — the single `next_url` parameter is simply never validated at any of its five call sites.

---

## 10. Round 7 — Findings + Specs + Plans (No Execution Yet)

Round 7 added 6 more areas from a focused `lexigram-admin` security pass
(2026-08-16). All six were verified against live code and confirmed absent
from every existing spec/plan (repo-wide doc grep: no `data_source.py`,
`tabular.py`, `controllers/search.py`, or `_BYPASS_SUFFIXES` matches anywhere
in `docs/superpowers/`). Designs written 2026-08-16; implementation plans
written 2026-08-17 — no code change executed yet. Master-doc section
numbers §33-§38 are reserved for
these areas once merged into the findings document.

| # | Area | Severity mix | Spec | Plan |
|---|------|--------------|------|------|
| 31 | **Generic-repository SQL identifier injection** (`admin/data/data_source.py`) | Critical ×1, High ×1 | `specs/2026-08-16-security-admin-sql-identifiers-design.md` | `plans/2026-08-16-security-admin-sql-identifiers.md` | **EXECUTED 2026-08-18** (identifier allowlist validation at all `data_source.py` call sites — table names, column names, order-by asc/desc; 13/13) |
| 32 | **Auth-guard path-suffix bypass** (`admin/middleware/auth_guard.py`) | High ×1 | `specs/2026-08-16-security-auth-guard-bypass-design.md` | `plans/2026-08-16-security-auth-guard-bypass.md` | **EXECUTED 2026-08-18** (segment-boundary validation, no tail-whitespace/encoded separators accepted; 9/9) |
| 33 | **Alpine JS-expression injection via record ids** (`admin/ui/organisms/table/views/tabular.py`) | High ×1, Med ×1 | `specs/2026-08-16-security-alpine-js-expression-design.md` | `plans/2026-08-16-security-alpine-js-expression.md` | **EXECUTED 2026-08-18** (record-id expression framing neutralized; 18/20 — 2 deferred review conventions, see §12; rows 34-36 merged into this plan) |
| 34 | **Search partial unescaped record fields** (`admin/controllers/search.py`) | Med ×1 | `specs/2026-08-16-security-search-partial-escaping-design.md` | `plans/2026-08-16-security-search-partial-escaping.md` | **EXECUTED 2026-08-18** (defensive HTML escaping of search snippets + record field rendering) |
| 35 | **Legacy session fallback without TTL / revocation** (`admin/middleware/auth.py`) | Med ×1 | `specs/2026-08-16-security-session-fallback-ttl-design.md` | `plans/2026-08-16-security-session-fallback-ttl.md` | **EXECUTED 2026-08-18** (fallback session TTL set to 4h, absolutely bounded by pre-primary TTL, single source of truth) |
| 36 | **Admin login `roles` unbound local** (`admin/auth/services/auth_service.py`) | High ×1 (availability) | `specs/2026-08-16-security-admin-login-roles-unbound-design.md` | `plans/2026-08-16-security-admin-login-roles-unbound.md` | **EXECUTED 2026-08-18** (roles bound to authenticated principal in login flow) |

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

## 11. Round 8 — Findings + Specs + Plans (No Execution Yet)

Round 8 added 6 more areas from a second focused `lexigram-admin` pass
(2026-08-16), sweeping the previously unaudited relations, export-service,
settings-config, and command-palette surfaces plus the `lexigram-search`
filter backends. Master-doc section numbers §39-§44 are reserved for these
areas once merged into the findings document. Findings verified against
live code; designs written 2026-08-16 and implementation plans written
2026-08-17 — no code change executed yet (exception: finding 40 / §42
remediated 2026-08-17, full status below).

| # | Area | Severity mix | Spec | Plan |
|---|------|--------------|------|------|
| 37 | **Relation panel raw-field rendering (stored + reflected XSS)** (`admin/relations/manager_ext.py`, `belongs_to_many.py`, `routes.py`) | High ×1, Med ×1 | `specs/2026-08-16-security-relations-panel-xss-design.md` | `plans/2026-08-16-security-relations-panel-xss.md` | **EXECUTED 2026-08-18** (relation panel raw-field rendering escaped in manager_ext + belongs_to_many + routes; see §12) |
| 38 | **Relation endpoint authorization / parent-IDOR** (`admin/relations/routes.py`, `manager_ext.py` predicates) | Med ×1 | `specs/2026-08-16-security-relations-routes-authz-design.md` | `plans/2026-08-16-security-relations-routes-authz.md` | **EXECUTED 2026-08-18** (relation endpoints gated on admin permission predicates; see §12) |
| 39 | **Excel export backend formula injection** (`admin/services/export/adapters/excel.py`) | Med ×1 | `specs/2026-08-16-security-export-excel-formula-design.md` | `plans/2026-08-16-security-export-excel-formula.md` | **EXECUTED 2026-08-18** (sanitize_cell_value strips leading `=+-@`, tab, CR — new `services/export/sanitize.py`; 24/24) |
| 40 | **Meilisearch/Typesense filter-expression injection** (`lexigram-search/backends/filters.py`) | High ×1 | `specs/2026-08-16-security-search-filter-injection-design.md` | `plans/2026-08-16-security-search-filter-injection.md` | **EXECUTED 2026-08-17 (`9e13cbf8`: `_meili_value`/`_typesense_value` escaping, `_validate_filters` fail-closed field-name gate; 39 new tests). Re-verified 2026-08-18 against spec/plan: complete** |
| 41 | **Settings config-read GETs bypass the edit-permission gate** (`admin/controllers/settings.py`, `widgets.py`) | Med ×1 | `specs/2026-08-16-security-settings-config-read-gate-design.md` | `plans/2026-08-16-security-settings-config-read-gate.md` | **EXECUTED 2026-08-18** (spec_view gate after unknown-namespace redirect; widget_config_popup + customize_all_widgets gated; 25/25) |
| 42 | **Command palette cross-resource search without per-resource rights** (`admin/controllers/command_palette.py`) | Med ×1 | `specs/2026-08-16-security-command-palette-permissions-design.md` | `plans/2026-08-16-security-command-palette-permissions.md` | **EXECUTED 2026-08-18** (SearchService per-resource `allowed_resources_for` scoping + result filtering; 59 e2e green) |

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
**Status: FIXED 2026-08-17** — `_meili_value`/`_typesense_value` now escape
`\` and `"` (backslash first) inside `"`-delimited string literals (Typesense
gained quoting for strings; bools/numbers stay unquoted); field-name gate
`_validate_filters` (`:65-68`) retained as the fail-closed boundary. Tests:
`test_search_filter_literal_safety.py` (round-trip + benign no-change),
`test_search_backend_filter_guards.py` (mocked engine asserts), value-safety
class appended to `test_block_translator.py`; 5 Typesense string asserts in
`test_filter_renderer.py` updated to quoted forms. Verification: 808 passed/
4 skipped (full lexigram-search unit suite), ruff clean, mypy clean
(`lexigram/src`: 294 files), two-pass review vs spec §3/§4 complete.

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

## 12. Round 9 — Findings + Specs + Plans (No Execution Yet)

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
plans listed in §3). Implementation plans written 2026-08-17 for all five
new areas — §48 (agents tool-visibility) executed 2026-08-17 (Lane 3, commit `5b2de912`, details below); §45 (pgvector field injection) executed 2026-08-18 (commit `8b3afbc0`, bundled with Round 4 row 20; reconciled 2026-08-18, was previously undocumented); §49 (OAuth2 email-verified binding) executed 2026-08-18 (details below); **§46 (storage KV) and §47 (MCP initialize/authz) executed 2026-08-18 (commit `8b3afbc0`, lane 4 consolidate) — rows updated below.**

| # | Area | Severity mix | Spec | Plan |
|---|------|--------------|------|------|
| 45 | **`lexigram-vector` pgvector metadata-field injection** | High ×1 | `specs/2026-08-16-security-vector-sql-field-injection-design.md` | `plans/2026-08-16-security-vector-sql-field-injection.md` | **EXECUTED 2026-08-18, commit `8b3afbc0`** — see Round 4 row 20 (bundled together); reconciled 2026-08-18, was previously undocumented |
| 46 | **`lexigram-storage` KV local namespace traversal** (arbitrary `rmtree`) | Med ×1 | `specs/2026-08-16-security-storage-kv-namespace-traversal-design.md` | `plans/2026-08-16-security-storage-kv-namespace-traversal.md` | **EXECUTED 2026-08-18, commit `8b3afbc0`** (`_get_ns_dir` at `kv/local.py:48` replaces verbatim joins at 3 sites; regression tests) |
| 47 | **`lexigram-ai-mcp` server: no initialize-handshake/authz enforcement** | Med ×1 | `specs/2026-08-16-security-mcp-server-initialize-authz-design.md` | `plans/2026-08-16-security-mcp-server-initialize-authz.md` | **EXECUTED 2026-08-18, commit `8b3afbc0`** (`-32002` pre-init rejection at `server/core.py:172-175`; authorizer consulted `:177-187`; fail-closed `-32000` with `allow_unauthenticated=False`; tests `test_mcp_handshake_and_authz.py`) |
| 48 | **`lexigram-ai-agents` tool-visibility check fails open** | Med ×1 | `specs/2026-08-16-security-agents-tool-visibility-failopen-design.md` | `plans/2026-08-16-security-agents-tool-visibility-failopen.md` | **EXECUTED 2026-08-17 (Lane 3, commit `5b2de912`)** |
| 49 | **`lexigram-auth` OAuth2 email binding without `email_verified`** | Med ×1 | `specs/2026-08-16-security-oauth2-email-verified-binding-design.md` | `plans/2026-08-16-security-oauth2-email-verified-binding.md` | **EXECUTED 2026-08-18** — generic chokepoint gated on `email_verified` (fail-closed default), provisioning `is_verified` wired from claim, Google path untouched; 607 auth unit tests green; see §12 details below |

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
failure mode silently grants access. **EXECUTED 2026-08-17 (Lane 3,
commit `5b2de912`):** `except` path flipped to `return False`; graph-less
guards with a caller module now fall through to the deny path (caller-less
standalone mode preserved); regression tests added
(`tests/unit/tools/test_tool_visibility_fail_closed.py`); suite 398 passed,
aggregate green.

**§49 — OAuth2 binds accounts by unverified email (Med, conditional).**
`lexigram-auth/.../authn/oauth2.py:460-465` `_find_or_create_oauth_user`
looks up / binds by the raw `email` claim with no `email_verified` check.
With a provider (or IdP configuration) that returns unverified emails,
an attacker registering the victim's address at a lenient IdP inherits the
existing account. Google flow mitigates (`google_oauth.py:112-114,131-133`);
severity depends on provider config.

**§49 CLOSED 2026-08-18** (execution record in
`plans/2026-08-16-security-oauth2-email-verified-binding.md`):
`OAuth2UserInfo.email_verified` (default `False`, fail-closed) in
`lexigram-auth/src/lexigram/auth/types.py:85`; generic mapping merges the
claim (`oauth2.py:441`); by-email bind gated on `oauth_user.email_verified`
(`oauth2.py:463`) with fall-through to identity-match/provisioning; new-account
`is_verified` wired from the claim (`:492`). Google gates
(`google_oauth.py:112,131,157,257`) untouched. New regression tests
(parametrized absent/false-claim no-bind, identity fall-through,
verified-bind baseline) in `test_oauth2.py`; auth unit suite 607 passed.

**Verification status — prior spec'd areas confirmed STILL OPEN (2026-08-16):**

| Area (tracker §) | Spec exists | Re-verified evidence | Status |
|---|---|---|---|
| GraphQL limits/introspection (§3.12) | `graphql-design.md` | `di/provider.py:379-389` wires only `RateLimitExtension`; `core/execution.py:358-359` "Would need depth analyzer"; `schema/builder.py:217-218` passes extensions only if added; `IntrospectionConfig` (`config.py:119-137`) consumed nowhere; plus new detail: `core/execution.py:280-300` wraps arbitrary resolver exceptions with `safe=True`/`str(original)`, bypassing `mask_errors` | Open |
| Media upload SSRF + ffmpeg (§3.13) | `media-upload-design.md` | All four fetch sites unguarded (`media_io.py:36-40`, `_asset_io.py:13-17`, `librosa.py:37-41`, `f5_tts_server.py:44-48`); `file://` passthrough at `media_io.py:28-32`; `argv.py:160-163` `drawtext` f-string with raw `font_size`/`color`; 13 servers bind `0.0.0.0` | **Closed — all claims addressed 2026-08-17–18 (§3.13 + follow-ups)** |
| Password reset lifecycle (§5 #22 / `password-reset-lifecycle-design.md`) | exists | Sharpened: `request_reset` (`password_reset.py:76-80`) generates the token but **never persists it** (`update_user(user)` without setting `password_reset_token`) → reset is broken out of the box; `_find_user_by_token` (`:114-130`) scans `list_users(0, 1000)` with plaintext `==` comparison; `confirm_reset` never calls `invalidate_token` | Open |
| Rate limiting (§3.15) | `rate-limit-design.md` | Sharpened: exact-path throttle match `request.url.path in ["/auth/login", "/auth/register"]` (`middleware/auth.py:196`; `throttle.py:23-31`) — `/auth/login/` bypasses throttling entirely | Open |
| AI memory isolation (§4 #16) | `ai-memory-design.md` | **EXECUTED 2026-08-17 (Lane 4, §7 row 16):** `database.py` all 5 statements now owner-predicated (`owner_id` bound param, incl. the formerly unscoped `_SELECT_ALL`/`_RECENT`); `retrieve()` no longer loads whole table / filters in Python; cache backend key+index namespaced `mem:{owner}:...`; `ConversationMemoryStore` fail-closed (log-and-empty, no raise); scheduler iterates explicit `owners` (no bypass); contracts require `owner_id` on `MemoryEntry`/`MemoryQuery` + protocol methods (`delete`/`clear`/`get_recent`/`assemble`/`forget`); 6 backends and all in-package/partner callers threaded. Verified: contracts+memory 615 green, memory pkg 256 green, 3 new isolation suites (15 tests), ruff/mypy clean, full non-integration suite 28101 passed / 22 pre-existing unrelated failures | Executed |
| AI guard wiring + fail-open (§3.11) | `ai-guard-design.md` | `streaming.py:250-252, 280-282` `except Exception → return True` (input+output); `@guarded` still `return await func(...)` (`decorators.py:46-53`); `AgentsProvider.boot()` (`di/provider.py:289`) still constructs `AgentSafetyInfra` with no guard pipeline | Open |
| Secrets fail-closed backends (§3.7 Task 5) | `secrets-design.md` | `backends/vault.py:54-55, 86-87, 107-108, 122-123` bare `except Exception → return None`/`pass`; GCP/AWS identical | Open |
| Skill sandbox / deserialization (§3.9 F1) | `deserialization-design.md` | `skill_loader.py:139-148` `exec(compiled, local_ns)` with `"os": os` in the namespace; `_get_env` (`:121-129`) passes **full** `os.environ` to subprocesses; `_is_safe_path` checks only `".."` in the resolved path string | Open |

**Re-audited 2026-08-17 (Lane 3, research-only; all three areas still Open):**

| Area | Re-audit verdict | Notes |
|---|---|---|
| AI guard (§3.11) | All baseline claims hold (19/20 exact; `function_calling.py` feed cites drifted to `:434-440`/`:483-489`; 1 premise already corrected in spec). Plan defects found: D4-as-written leaves the streaming **output** leg open (`streaming.py:150` return discarded); D3 guard exceptions have no exception→`Err` mapping (`executor.run()` would let them escape uncaught); `SupervisorStrategy` (`supervisor.py:335-345`) is a 4th unguarded OBSERVE feed (non-default). **Posture conflict at sign-off:** tracker/§3.11 recommend fail-closed-by-default; spec §4 Decision D + plan Task 4 implement fail-open-by-default (`llm_guard_fail_open=True`). | Open — §2 bullet :93 unchecked |
| GraphQL (§3.12) | All 5 baseline claims hold exact (incl. mask-bypass `execution.py:287-300`, pinned by `test_graphql_execution.py:30-31,80`). **Interaction gap:** plan's post-wiring test assertions would fail — the 4 new security errors get masked to "Internal server error" under default `mask_errors=True` (only `RateLimitError` survives via `safe=True`, `exceptions.py:129`). Need `safe=True` on the new errors or `ErrorConfig(mask_errors=False)` in tests; mask-bypass itself is undispositioned (tracker detail landed after spec). Trivial: `Iterator` import is not yet in `complexity.py`. | Open — §2 bullet :94 unchecked |
| Media upload (§3.13) | Every claim holds **exact** (4 fetch sites, `file://` passthrough, argv drawtext `:160-163`, 13× `0.0.0.0` app.run, no `multimedia/security.py`, no `client_max_size`, `scale_factor` unvalidated). **Task 0 gate SATISFIED** — `is_safe_url_for_request` lives at `lexigram.contracts.security.url_safety` (:64, fail-closed docstring); zero multimedia consumers (all 4 sites still unguarded). Only blocker is §2 sign-off. | **Closed 2026-08-18** — §2 bullet signed off 2026-08-17; plan executed + all follow-ups landed (§3.13); auto-revoked by TRAIN pending re-sign-off |

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

## 12a. Round 10 — Findings, Specs Written (Plans Pending)

Round 10 (2026-08-18) swept the ten packages no prior round had touched:
`lexigram-ai-evaluation`, `lexigram-ai-feedback`, `lexigram-ai-governance`,
`lexigram-ai-observability`, `lexigram-ai-prompt`, `lexigram-ai-workers`,
`lexigram-features`, `lexigram-testing`, `lexigram-resilience`,
`lexigram-monitor` — via three parallel exploration agents. Every finding
below was personally re-verified against live code (file reads / greps), per
the audit's standing discipline. **Agent constraint honored**: agents did not
edit this tracker or commit; findings are logged here by the coordinator
after independent verification. **Design specs have been written for all 11
findings** (§50-60), all under `docs/superpowers/specs/2026-08-18-*-design.md`
(see table below for exact filenames). **No implementation plans have been
written yet** — plan authoring (the next stage of verify → spec → plan →
two-pass review) is pending user direction.

One agent claim was corrected during verification: the governance-package
agent reported "zero call-sites anywhere in the framework" for
`AIGovernanceManager`'s enforcement methods (§50 below). Direct grep +
read disproved this — `lexigram-ai-agents/.../executor/executor.py:190,532`
resolves `AIGovernanceProtocol` via DI (`di/provider.py:143`,
`resolve_optional`) and calls `check_request()`/`track_cost()` in the live
agent-execution path, and `lexigram-ai-governance/di/provider.py:98` binds
that protocol to the real `AIGovernanceManager`. This matters because it
means §50's fail-open bug has a real, live call path today, not a
theoretical one — reflected in the severity below.

| # | Area | Severity mix | Spec | Plan |
|---|------|--------------|------|------|
| 50 | **`lexigram-ai-governance` Redis persistence silently fails open, disabling budget/RPM enforcement** | High ×1 | `docs/superpowers/specs/2026-08-18-security-ai-governance-redis-failopen-design.md` | **EXECUTED 2026-08-18 (Lane 6: `a0acc4a8`, `718285ef`, `5f1386f8`, `8f3995e8`; §2 sign-off pending) — see TRACKER.md Lane 6** |
| 51 | **`lexigram-ai-governance` → `lexigram-tasks` cross-extension import** | Low ×1 | `docs/superpowers/specs/2026-08-18-architecture-ai-governance-tasks-import-design.md` | Not yet written | **EXECUTED 2026-08-18 — `GaugeReconciliationWorker` rewired to `TaskManagerProtocol` via new `GovernanceScheduledWorker` base (`resource/scheduled_worker.py`); both `lexigram.tasks` imports removed; governance pyproject dep dropped; import-linter contract `ai-sub-independence` extended to `lexigram.tasks`** |
| 52 | **`lexigram-ai-observability` trace spans carry unredacted tool/agent/retriever payloads** | Med ×1 | `docs/superpowers/specs/2026-08-18-security-ai-observability-trace-redaction-design.md` | **EXECUTED 2026-08-18 (Lane 5: `a27e1535`, `d2827eda`, `f0891442`, `65325327`; §2 sign-off pending) — see TRACKER.md Lane 5** |
| 53 | **`lexigram-ai-workers` document-ingestion accepts unvalidated file paths (traversal / arbitrary read)** | High ×1 | `docs/superpowers/specs/2026-08-18-security-ai-workers-path-traversal-design.md` | **EXECUTED 2026-08-18 (Lane 5: `f36031b3`, `69ed1546`, `0b6c4bb7`; §2 sign-off pending) — see TRACKER.md Lane 5** |
| 54 | **`lexigram-ai-prompt` `max_variable_length` config flag is defined but never enforced** | Low ×1 | `docs/superpowers/specs/2026-08-18-quality-ai-prompt-dead-config-flag-design.md` | Not yet written | **EXECUTED 2026-08-18 — enforced in `variables/validators.py` + forwarded through template classes (string/chat/few_shot), `0 = unlimited` contract preserved; 11 new tests, 307 package tests green** |
| 55 | **`lexigram-features` empty `user_attributes` rule fails open (enabled=True for everyone)** | Low/Med ×1 | `docs/superpowers/specs/2026-08-18-security-features-empty-rule-failopen-design.md` | **EXECUTED 2026-08-18 (Lane 7, Area 4; §2 sign-off pending) — see §3.19** |
| 56 | **`lexigram-monitor` `/health`+`/metrics` unauthenticated, and health checks may leak raw exception strings** | Med ×2 | `docs/superpowers/specs/2026-08-18-security-monitor-health-metrics-authz-design.md` | **EXECUTED 2026-08-18 (Lane 7, Area 3; §2 sign-off pending) — see §3.18** |
| 57 | **`lexigram-monitor` still hard-depends on `lexigram-tasks` at the packaging level** | Low ×1 | `docs/superpowers/specs/2026-08-18-architecture-monitor-tasks-dependency-design.md` | Not yet written | **EXECUTED 2026-08-18 — `lexigram-tasks` moved to test-only deps (pyproject + wheel-METADATA proof); new dependency test; 333 monitor tests green** |
| 58 | **`lexigram-resilience` `throttle()` decorator is structurally dead — every call raises** | Med ×1 | `docs/superpowers/specs/2026-08-18-quality-resilience-throttle-dead-decorator-design.md` | Not yet written | **EXECUTED 2026-08-18 — Option B: deleted `throttle()`/`ThrottleRegistry`/`get_throttle_stats` (zero callers outside own tests); exports/DI/registry scrubbed; regression guards; 310 resilience tests green** |
| 59 | **`lexigram-resilience` idempotency fails open on store outage, and two `unwrap()`-without-guard sites can defeat even that fallback** | Med-High ×1 | `docs/superpowers/specs/2026-08-18-security-resilience-idempotency-failopen-unwrap-design.md` | **EXECUTED 2026-08-18 (Lane 6: `a962b604`, `b750454b`; §2 sign-off pending) — see TRACKER.md Lane 6** |
| 60 | **`lexigram-resilience` database idempotency store's "dialect-aware" placeholder is hardcoded to `?`, breaking Postgres — deeper than reported (naive `.replace()` also can't produce sequential `$1,$2,...` for multi-param queries)** | Low ×1 | `docs/superpowers/specs/2026-08-18-quality-resilience-idempotency-placeholder-design.md` | Not yet written | **EXECUTED 2026-08-18 — `_translate_placeholders()` (`?` → sequential `$1,$2,…` via `re.sub`+counter), dialect detection via `database_type` attr, all 6 `.replace("?")` sites rewired; unit tests pin exact SQL/param shapes** |

**§50 — `RedisGovernancePersistence` fail-open on every error path (High).**
`lexigram-ai-governance/src/lexigram/ai/governance/persistence/persistence.py`:
`add_spend()` (`:325-327`) catches `(OSError, ConnectionError, RuntimeError,
ValueError, TypeError)` and returns just `amount` instead of true cumulative
spend (comment literally says `# fail-open`); `get_spend()` (`:335-336`)
returns `0.0` on the same errors; `incr_requests()` (`:294-295, 310-311`)
falls back to `1`; `read_gauge()`/`incr_gauge()` similarly reset toward zero.
Personally verified line-for-line — matches exactly. `AIGovernanceManager.
check_budget()`/`check_request()` (`services/manager.py:170, 397`) call
these directly, so on any transient Redis error the monthly spend cap and
RPM limiter both silently reopen (`get_spend()→0.0` makes `current+cost<=
budget` pass almost unconditionally). **Confirmed live and reachable**:
`lexigram-ai-agents/.../executor/executor.py:190` (`check_request`) and
`:532` (`track_cost`) call this in the real agent-execution path when
governance is DI-wired (`di/provider.py:98` binds `AIGovernanceProtocol` →
`AIGovernanceManager`) — this is not dead code, contradicting the
originating agent's "zero call-sites" claim (see correction note above).
No error/warning is logged on any of these fail-open paths, so the
degradation is silent even to operators.

**§51 — `ai-governance` imports `lexigram-tasks` directly (Low).**
`lexigram-ai-governance/src/lexigram/ai/governance/resource/reconciliation.py:18`
(`from lexigram.tasks import ScheduledWorker`) and `:22`
(`BackgroundTaskManager`). Grep across all `lexigram-*/src` found no other
extension importing `lexigram.tasks` this way, so it isn't covered by the
existing accepted-exceptions list (`admin→ui`, `ai→{ai-llm,ai-rag,
ai-feedback,ai-observability}`, `monitor→tasks`, `testing→sql`). Narrow
blast radius: `GaugeReconciliationWorker` is exported via lazy `__getattr__`
but never instantiated by `di/provider.py` — opt-in, application-wired, no
runtime path today.

**§52 — Observability trace spans include unredacted arguments/responses (Med).**
`lexigram-ai-observability/src/lexigram/ai/observability/tracing/core.py`
(`AITracer`, lines 300-380, personally re-read and confirmed exact):
`on_tool_start` (`:322-330`) sets `attributes={"tool.name": tool_name,
"tool.args": arguments, **kwargs}`; `on_agent_action`/`on_agent_finish`
(`:343-359`) add the raw `action`/`response` dicts as span events;
`on_retriever_start` (`:361-369`) attributes the raw `query`. None of these
paths redact or size-cap the payload before it lands on an exported trace
span (`CallbackHandlerProtocol`, `lexigram-contracts/.../ai/callbacks.py:
103-183`). Any secret, PII, or user-supplied content passed as tool
arguments, agent actions, or retriever queries is exported verbatim to
whatever tracing backend consumes these spans (OTel exporters etc.).

**§53 — Document-ingestion worker accepts caller-supplied file paths with no containment check (High).**
`lexigram-ai-workers/src/lexigram/ai/workers/document_ingestion/worker.py`
`ingest_document()` (`:194-258`, personally re-read `:190-260`) builds
`job_data = {"file_path": str(file_path), ...}` from its `file_path: Path`
parameter with zero validation before enqueueing. `parser.py`'s loader
(`:37-176`, `UniversalDocumentParser.parse`, personally grepped `:1-50`)
does `path = Path(source)` then `await asyncio.to_thread(path.read_text,
encoding="utf-8")` — no root-containment or traversal check anywhere on
this path. If `file_path`/`source` is ever derived from user input
(upload filename, API param) upstream of this worker, this is an arbitrary
local file read. Reachability from an actual HTTP boundary wasn't traced
within this package (worker is invoked by callers outside
`lexigram-ai-workers`) — flag as High on the primitive itself, confirm
call-site trust boundary before treating as Critical.
Informational/Low, not independently re-verified: the originating agent
also flagged that `ingest_document` and its job data carry no
tenant/owner scoping field, unlike the AI-memory package's owner-predicated
design (Round 9 §4 #16) — worth a cross-package comparison in a future
round rather than a standalone finding here.

**§54 — `max_variable_length` is declared but never read (Low).**
`lexigram-ai-prompt/src/lexigram/ai/prompt/config.py:58-59` defines the
field; grep for `max_variable_length` across `lexigram-ai-prompt/src`
(personally re-run) returns exactly those two hits (the docstring at `:32`
and the field definition) — no read site. `validators.py:28-34`'s
`validate_variable` and `:83-86`'s permissive-mode passthrough in
`resolve_variables` never consult it, so nothing stops an oversized
template variable from reaching `rendering/engine.py:73-89`'s Jinja2
render — a config knob that looks like a DoS/injection-size guard but
does nothing.

**§55 — Empty `user_attributes` rule flips a flag to enabled for everyone (Low/Med).**
`lexigram-features/src/lexigram/features/backends/base.py:237-257`,
`AbstractFlagProvider._evaluate_user_attribute()`: `if not
flag.user_attributes: return FlagEvaluation(..., enabled=True,
reason="user_attribute_empty_rule", value=True)`. Every other default in
this package is fail-closed (`DEFAULT_ENABLED=False` in `constants.py`,
`FlagManager.evaluate()`/`is_enabled()` fail-closed) — this one path
inverts that on an admin misconfiguration (forgetting to populate the
rule), not attacker input, so it's rated Low/Med rather than a direct
exploit.

**§56 — Monitor `/health`+`/metrics` unauthenticated; health-check errors may leak connection details (Med).**
`lexigram-monitor/src/lexigram/monitor/middleware/health.py:52-77` and
`middleware/prometheus.py:88-99` intercept their configured paths with no
permission/auth check — personally re-grepped both files for
`permission|require_auth|authenticate|Authorization`, zero hits, confirmed
exact. Mirrors the previously-fixed admin pool-health finding (Round 6
row 29 / §31). Unauthenticated health/metrics is often intentional (k8s
probes, Prometheus scraping) so not automatically a bug on its own.
Compounding factor: `health/cached.py` `_check_database_health()`/
`_check_redis_health()` (`:82-141, 143-168`) catch driver exceptions and
set `message=str(e)` directly into the JSON response (`:137, 164`), which
can include host/port/DSN fragments depending on the driver; same pattern
in `health/registry.py:53-127` and `di/provider.py:536-575`. The
originating agent could not confirm within this repo that
`CachedHealthChecker`'s output is actually what the unauthenticated
`HealthCheckProvider` middleware serves (that wiring likely happens in a
downstream consuming app) — both halves are individually verified, the
end-to-end connection is plausible but unconfirmed here.

**§57 — `lexigram-monitor`'s `pyproject.toml` still hard-depends on `lexigram-tasks` (Low).**
Personally re-verified: `lexigram-monitor/pyproject.toml:40` declares
`"lexigram-tasks>=0.1.1"` as a required (non-optional) dependency, with a
matching `[tool.uv.sources.lexigram-tasks]` block; grep for
`lexigram.tasks` imports anywhere in `lexigram-monitor/src` returns zero
matches (only two docstring mentions explicitly disclaiming it). The
source-level fix (routing through `lexigram.contracts.infra.tasks.
TaskManagerProtocol`) was never mirrored in the packaging metadata — an
orphaned dependency, not a live import-boundary violation.

**§58 — `throttle()` decorator can never succeed (Med, quality/reliability not a silent security gap).**
`lexigram-resilience/src/lexigram/resilience/throttle/throttle.py:112-160`,
personally re-read in full. `_limiter` is a closure-local `nonlocal`
variable inside `decorator()`/`wrapper()` — it is set to `None` at `:132`
and never assigned anywhere else in the function. `wrapper()` (`:135-142`)
unconditionally raises `RuntimeError("Throttle limiter not initialized...")`
on first call. Confirmed via `di/provider.py:59-63` that `ThrottleRegistry`
is registered as a container singleton, but nothing in `throttle.py` ever
looks it up — and structurally *couldn't*, since `_limiter` is a
function-closure variable, not an attribute external code could reach
(`wrapper_any._throttle_key` is set at `:156`, but no equivalent exists
for `_limiter`). This is worse than "not yet wired": it cannot be wired
without editing `throttle.py` itself. Every consumer following the
module's own docstring (`@throttle(calls=10, period=1.0)`) gets an
immediate crash, not a silent bypass — so this is a reliability/dead-code
defect, not a silent DoS gap. The separate `Throttler` class
(`:181-338`) is a working, correctly-wired alternative.

**§59 — Idempotency middleware fail-open is itself defeated by two unguarded `unwrap()` calls (Med-High).**
`lexigram-resilience/src/lexigram/resilience/idempotency/middleware.py:87-161`
catches `(OSError, ConnectionError, RuntimeError)` on both the read and
write paths and falls through to executing the handler directly
(duplicate-suppression disabled) when the idempotency store is
unreachable — a deliberate, logged fail-open (availability over
duplicate-prevention, no fail-closed option). Separately, two call sites
skip the `is_ok()` guard this project requires before `unwrap()`:
`middleware.py:131` (`cached = cached_result.unwrap() if
isinstance(cached_result, Result) else cached_result`) and
`idempotency/redis.py:66` (`cached = cached.unwrap()`). Both
`IdempotencyStoreProtocol.get()` and `CacheBackendProtocol.get()`
(`lexigram-contracts/.../core/idempotency.py`,
`.../infra/cache/protocols.py:49`) are documented to return `Result[Any |
None, Error]`, with `Err(...)` as the documented failure signal — `Err.
unwrap()` raises `UnwrapError`, which is **not** in the
`(OSError, ConnectionError, RuntimeError)` tuple the middleware catches at
`:93-99`. So a conforming store/cache backend that reports failure via
`Err(...)` (per its own contract) rather than by raising produces an
**uncaught `UnwrapError`** that propagates straight past the intended
fail-open path — the opposite of the behavior one line above in the same
function. Two independent bugs compounding into one: the fail-open design
itself (debatable but deliberate) plus a code-level violation of the
project's `unwrap()`-without-guard rule that can silently invert it into a
crash instead of a pass-through.

**§60 — `DatabaseIdempotencyStore._placeholder` claims dialect-awareness, is hardcoded `"?"` (Low).**
`lexigram-resilience/src/lexigram/resilience/idempotency/database.py:237-240`
docstring: `"SQL parameter placeholder — ``?`` for SQLite; ``$1``-style for
Postgres"`; implementation: `return "?"` unconditionally. Traced through to
`lexigram-sql/src/lexigram/sql/backends/_postgres_connection.py:69-86`,
which passes the query string straight to `asyncpg.execute(query, *params)`
with no placeholder-translation layer anywhere in `lexigram-sql` (grepped
for `paramstyle`/`qmark`/`$1`/translation helpers — none found). `asyncpg`
requires native `$1, $2, ...` and rejects `?`, so `DatabaseIdempotencyStore`
against Postgres fails every query with a syntax/binding error — loud
failure, not silent corruption, but a real contradiction of the documented
Postgres-support claim. **Sharpened during spec-writing (2026-08-18):** the
fix is deeper than the property alone. All six call sites translate SQL via
`<CONST>.replace("?", self._placeholder)` — a blind string replace that
substitutes the *same* value at every occurrence. `_SET_SQL` has 4 `?`s and
`_ACQUIRE_SQL` has 3, so even a corrected `_placeholder` returning `"$1"`
would produce `VALUES ($1, $1, $1, $1)` instead of `VALUES ($1, $2, $3,
$4)` — `set()`/`acquire()` (the two write paths) need a real sequential
`?`→`$N` translator, not just a dialect-aware property. See spec for full
design.

**Verified-clean surfaces (negatives):** `lexigram-ai-evaluation` — proper
`Result` guards throughout, no cross-package/relative imports (one
theoretical ReDoS caveat in `evaluators/criteria.py` with no found
attacker-reachable path, criteria are developer-authored config everywhere
checked). `lexigram-ai-feedback` — parameterized SQL, clean cache
write-through, no cross-package/relative imports (one dead-code rough edge:
`middleware/middleware.py`'s example endpoint factory raises unhandled
`KeyError` on bad input, but is wired nowhere outside its own tests).
`lexigram-ai-governance` billing/ledger/channels/logs/audit persistence —
fully parameterized SQL, every other `.unwrap()` site properly guarded.
`lexigram-testing` — all 8 `.unwrap()` sites correctly guarded (expected
for test-assertion helpers), no eval/exec/pickle/subprocess, real
`PasswordHasher` used (no auth-bypass leak into consumers); architecture
note only: eager top-level imports from `lexigram-auth`/`lexigram-cache`/
`lexigram-secrets` beyond the one documented `lexigram-sql` exception, all
gated behind optional extras — a documentation gap, not a functional one.
`lexigram-resilience` `retry/`, `circuit/`, in-memory `idempotency/store.py`
+ `database.py` SQL, `rate_limiter/distributed.py`, `bulkhead/limiter.py` —
all independently verified clean (crypto-strong jitter, bounded
retries/semaphores, parameterized SQL, safe JSON deserialization, no raw
error leakage from circuit-state introspection).

**Recurring shapes (§50-60):** §50 is the same "except-clause defaults to
allow" fail-open family as Round 9 §48 and Round 3 §29 — here compounded by
the fact that the enforcement it disables (budget/RPM caps) has a real,
live caller this time, not a hypothetical one. §51/§57 are both the
"architecture rule fixed at the import level, forgotten at the packaging/
metadata level" shape — a new variant not seen in prior rounds. §52 is a
new shape for this audit: observability/tracing infrastructure that
faithfully forwards whatever payload it's given, with redaction assumed to
happen elsewhere but enforced nowhere. §53 is the "unvalidated file path
from a caller-supplied string" family, same shape as Round 9's storage/KV
traversal (§46) and Round 4's SSRF fetch sites, applied to a worker/queue
entry point instead of an HTTP one. §54/§58 are both "config knob or
public API that looks load-bearing and is not" — §54 a silently-ignored
flag, §58 a decorator that cannot ever succeed by construction. §55 is the
single fail-open exception in an otherwise consistently fail-closed
package — an admin-misconfiguration trigger, not attacker-controlled,
matching the Round 10 §55/Round 9 pattern of "one path breaks an
otherwise-clean design." §56 is the same unauthenticated-health-endpoint
pattern already fixed once in `lexigram-admin` (Round 6 §31), recurring in
a sibling package that was never touched by that fix. §59 is the sharpest
finding of the round: a deliberate, documented fail-open safety valve
silently inverted into an unhandled crash by the project's own
`unwrap()`-without-`is_ok()` rule being violated one line inside the same
function that implements the fail-open — the clearest instance yet of two
individually-defensible patterns combining into a real defect.

---

## 12b. Round 11 — Findings Only (No Specs/Plans Written Yet)

Triggered by "review other areas we havent covered yet." Before dispatching agents, the
target list was scoped by reading the tracker's own coverage (§1 Area Summary,
full Round 9 section) rather than trusting a naive per-package-name grep — the grep's
first pass mislabeled `lexigram-graphql`, `lexigram-ai-guard`, `lexigram-ai-rag`,
`lexigram-ai-relay`, `lexigram-multimedia-*`, and `lexigram-web` as uncovered, when in
fact they're covered under human-readable names ("GraphQL," "AI guard," "Media-upload,"
"AI relay / worker / MCP trust boundary") in earlier rounds. After that correction, 3
parallel background exploration agents swept the 9 packages genuinely untouched by any
prior round: `lexigram-ai` (core, not the `ai-*` extensions already covered),
`lexigram-audit`, `lexigram-events`, `lexigram-workflow`, `lexigram-queue`,
`lexigram-tasks`, `lexigram-testing`, `lexigram-ai-evaluation`, `lexigram-ai-feedback`.

Per this audit's standing verification discipline, every high/critical-severity claim
across all three agents' reports was personally re-checked against live source before
being written up here. Unlike Round 10 (which caught one false agent claim), **every
single spot-check this round confirmed exactly as reported — zero false claims found.**
Lower-severity findings (marked below) were not individually re-verified given that
100% track record, consistent with how Round 10's write-up also didn't re-check every
claim, only the most consequential ones.

### Findings table

| § | Package | Finding | Severity | Spec |
|---|---|---|---|---|
| 61 | lexigram-ai | Governance DI register/boot-ordering bug — `gov_persistence` wiring built during `register()` always sees pre-boot `None` for `_database_provider`/`_cache_backend`; entry-point double-registration silently overwrites the correctly-wired instance | High | `docs/superpowers/specs/2026-08-18-security-ai-governance-di-ordering-design.md` | **EXECUTED 2026-08-18 (Lane 6: `a332e78b`, `0407f154`, `55643200`, `beea2acc`; §2 sign-off pending) — see TRACKER.md Lane 6** |
| 62 | lexigram-ai-evaluation | Fail-open scoring on empty reference set | Medium | `docs/superpowers/specs/2026-08-18-quality-ai-evaluation-empty-reference-design.md` | **EXECUTED 2026-08-18 — D2 fallback in `evaluators/qa.py`: case-insensitive containment match (`score = 1.0 if ref_text in output_text else 0.0`), empty-output-guarded; 6 new fallback tests, 142 package tests green** |
| 63 | lexigram-ai-feedback | No tenant/user scoping on feedback records | Medium | `docs/superpowers/specs/2026-08-18-security-ai-feedback-tenant-scoping-design.md` | **EXECUTED 2026-08-18 (Lane 5: `23146cba`, `c447c1db`, `084e013a`, `9c99ada8`; §2 sign-off pending) — see TRACKER.md Lane 5** |
| 64 | lexigram-ai-feedback | `FeedbackSystemWithResultPattern` is a fake-persistence stub — always returns `Ok(...)`, never stores, `get_feedback()` always returns `Ok([])`; publicly exported in `__all__` alongside the real service | High | `docs/superpowers/specs/2026-08-18-quality-ai-feedback-fake-persistence-design.md` | **EXECUTED 2026-08-18 (spec §4.1 Option A: deleted — zero callers outside its own tests)** |
| 65 | lexigram-ai-feedback | No-authz endpoint / unenforced `MAX_FEEDBACK_TEXT_LENGTH` and `MAX_CONTEXT_SIZE` constants (declared, never read) | Medium | `docs/superpowers/specs/2026-08-18-security-ai-feedback-authz-limits-design.md` | **EXECUTED 2026-08-18 (Lane 5: `1a5ffb58`, `b52dedc6`; §2 sign-off pending) — see TRACKER.md Lane 5** |
| 66 | lexigram-audit | Tamper-verification is a permanent no-op — `verify_recent()` unconditionally returns `[]`, `verify_entry()` unconditionally returns `True`; admin UI's "verified" flag is therefore always green | Critical | `docs/superpowers/specs/2026-08-18-security-audit-verification-noop-design.md` | **EXECUTED 2026-08-18 (Lane 7, Area 2; §2 sign-off pending) — see §3.17** |
| 67 | lexigram-audit | `purge_expired()` counts expired entries but never calls any store delete method — retention purge silently doesn't delete anything | High | `docs/superpowers/specs/2026-08-18-security-audit-purge-noop-design.md` | **EXECUTED 2026-08-18 (Lane 7, Area 1; §2 sign-off pending) — see §3.16** |
| 68 | lexigram-audit | Blind `except` in log/query path | Medium | `docs/superpowers/specs/2026-08-18-quality-audit-blind-except-design.md` | **EXECUTED 2026-08-18 — `except Exception as exc` at both sites, `error`/`error_type` structured keys on `log_failed`/`query_failed` warnings; fail-open posture unchanged; 2 new tests, 289 audit tests green** |
| 69 | lexigram-events | WebSocket streaming endpoint gained an optional `authorize` callback (`21bdf478`) but still defaults to accepting every connection — default-open posture documented (`a54711ec`); `subscribe_all` still has no tenant/event filtering hook | Critical | `docs/superpowers/specs/2026-08-18-security-events-websocket-noauth-design.md` | **EXECUTED 2026-08-18 (Lane 6: `21bdf478`, `a54711ec`; §2 sign-off pending) — see TRACKER.md Lane 6; default-open posture remains: operator must supply `authorize`** |
| 70 | lexigram-events | `subscribe()`'s `event_filter` parameter is silently discarded (`_ = event_filter`, explicit "not implemented" comment) — filtering was never built despite the parameter existing in the public API | High | `docs/superpowers/specs/2026-08-18-quality-events-filter-not-implemented-design.md` | **EXECUTED 2026-08-18 — filter wired into `streaming/dispatcher.py` subscription records + `publish()` (rejected subscribers skipped, no `events_published` increment); `unsubscribe` scrubs filter records; 8 new tests** |
| 71 | lexigram-events | Unbounded idempotent-decorator cache / unvalidated `table_name` | Medium | `docs/superpowers/specs/2026-08-18-quality-events-cache-tablename-design.md` | **EXECUTED 2026-08-18 — `IdempotencyCache` (LRU 10k, lazy TTL via ambient clock) in `decorators/idempotency_cache.py`; `idempotent()` `ttl` now enforced; `validate_table_name()` (regex allowlist, 63-char bound) at store construction; 34 new tests** |
| 72 | lexigram-queue | Default driver (`InMemoryQueue`) has no backpressure/`max_in_flight` limit, unlike every other backend (Kafka/SQS/Azure/GCP) — unbounded task spawning under load | High | `docs/superpowers/specs/2026-08-18-resilience-queue-memory-backpressure-design.md` | **EXECUTED 2026-08-18 — `max_concurrency` cap (semaphore + `_run_handler` dispatch) in `backends/memory.py`, `ValueError` on <1; 3 new tests** |
| 73 | lexigram-queue | `RedisQueue`'s listener invokes handlers inline inside its single long-running loop with a bare `raise` on failure — first handler exception permanently kills consumption for the entire topic (poison-message DoS), unlike other backends' per-message task isolation | High | `docs/superpowers/specs/2026-08-18-resilience-queue-redis-listener-design.md` | **EXECUTED 2026-08-18 — `_listen()` spawns per-message tasks (`_handle_message` catch-log-swallow isolation); message `id` propagated; 4 new isolation tests** |
| 74 | lexigram-queue | `TransactionalOutbox` is pure in-memory — zero DB persistence despite the name/contract implying durability | High | `docs/superpowers/specs/2026-08-18-resilience-queue-outbox-durability-design.md` | **EXECUTED 2026-08-18 (spec §4.1 Option B: renamed to `BatchedPublisher` with honest in-memory-only docs; durable SQL outbox already exists at contracts/sql layers) — see CLOSED record below** |
| 75 | lexigram-queue | Dangling admin handler reference | Low | `docs/superpowers/specs/2026-08-18-quality-queue-admin-handler-design.md` | **EXECUTED 2026-08-18 — `admin/actions.py` `retry_failed` (DLQ drain → republish, failed publishes re-pushed to DLQ); contributor dispatch resolved at boot via `import_module`; DLQ singleton registered in provider; 9 new tests + integration e2e** |
| 76 | lexigram-tasks | `persistence.py` docstrings present `LockManager` as suitable for distributed/multi-instance leader election; `LockManager`'s own docstring explicitly states it is process-local only, with no cross-process or cross-host guarantees — direct contradiction | High | `docs/superpowers/specs/2026-08-18-quality-tasks-lockmanager-docs-design.md` | **EXECUTED 2026-08-18 — docs corrected (process-local); `acquire_wait()` backoff poller, blocking `__aenter__`, identity-guarded `release()`; `scheduling/persistence.py` points to `lexigram-resilience` for multi-instance election; 6 new `test_locking.py` tests** |
| 77 | lexigram-tasks | `IdempotencyManager.check_duplicate()` treats a storage-layer `Err` as a truthy "existing record" (no `is_ok()` guard), then does unguarded `existing["task_id"]` subscript access on the raw `Err` object — produces an unrelated `TypeError` instead of a typed error | Medium | `docs/superpowers/specs/2026-08-18-quality-tasks-idempotency-err-truthy-design.md` | **EXECUTED 2026-08-18 — `_get_existing()` explicit `Result` branching; `Err` → typed `IdempotencyStoreError` (`from` chained); 5 new failure-path tests** |
| 78 | lexigram-tasks | `BackgroundTaskManager._register()` unconditionally registers `task.add_done_callback(self._names.pop)` while only conditionally inserting into `self._names` (`if name is not None`) — nameless tasks completing raises `KeyError` inside the done-callback | Medium | `docs/superpowers/specs/2026-08-18-quality-tasks-background-manager-keyerror-design.md` | **EXECUTED 2026-08-18 — done-callback uses `self._names.pop(t, None)`; 3 new cleanup tests** |
| 79 | lexigram-workflow | `store_database.py`'s `list_by_stage()` escapes quotes for `stage_id`/`tenant_id` but interpolates them (and `LIMIT`) into the SQL string via raw f-string rather than parameterized `?` placeholders — contrasts with sibling methods (`evict()`) in the same file that correctly parameterize | Medium | `docs/superpowers/specs/2026-08-18-security-workflow-checkpoint-sql-design.md` | **EXECUTED 2026-08-18 (Lane 7, Area 5; §2 sign-off pending) — see §3.20** |

**§74 CLOSED 2026-08-18** (execution record in
`plans/2026-08-18-resilience-queue-outbox-durability.md`): resolved as
spec §4.1 **Option B** (rename + re-document). The framework's durable outbox
already exists at the contracts/sql layers (`OutboxStoreProtocol` in
`lexigram-contracts/src/lexigram/contracts/data/outbox.py`; `SQLOutboxStore`
+ `OutboxPublisher` in `lexigram-sql/src/lexigram/sql/outbox/`, wired via
`unit_of_work/base.py:55`), so cloning it into `lexigram-queue` would
duplicate that subsystem (AGENTS.md §2.6) and require a `queue→sql`
dependency not among the documented package exceptions (AGENTS.md §1.2).
`lexigram-queue`'s zero-caller `TransactionalOutbox` was renamed to
`BatchedPublisher` (`core/batch_publisher.py`, entry `PendingPublish`) with
honest in-memory-only docstrings; `README.md`, `docs/ARCHITECTURE.md`,
`docs/GUIDE.md`, `docs/HOWTOS.md`, and `docs/lexigram-docs/guides/queue.md`
no longer claim transactional/crash-safe semantics (or the nonexistent
`flush_interval`/`batch_size`/`enqueue` API) and now cross-reference the
durable SQL outbox for crash-safe delivery.

`lexigram-testing` produced no findings (see "Verified-clean surfaces" below).

### Verified-clean surfaces

- `lexigram-testing`'s fakes — reviewed and confirmed clean; no findings.
- `lexigram-ai-evaluation` — confirmed no LLM-as-judge or prompt-injection surface exists in this package (a plausible-sounding risk that turned out not to apply here).
- `lexigram-queue`'s Kafka/SQS/Azure Service Bus/GCP Pub/Sub backends — all implement proper `max_in_flight`-based backpressure with per-message task isolation (contrast §72/§73, which are specific to the in-memory default and Redis backend).
- `lexigram-workflow`'s dynamic-code-execution and checkpoint-deserialization surfaces — reviewed, clean (contrast §79, which is a narrower SQL-interpolation issue in one query method, not a deserialization/eval risk).
- Fernet encryption usage and JSON-only serialization — confirmed consistent and correct across all 9 packages swept this round.
- Dependency hygiene (2026-08-18): `python-jose`/`ecdsa` removed from the tree (CVE-2024-23342 Minerva timing attack, no upstream fix; pip-audit clean after removal). Only runtime call site was the diagnostic `get_unverified_header()` in `lexigram-admin/.../guards.py` — replaced with a stdlib base64url header decode; auth test token minting switched to `pyjwt` (already a dependency).

### Recurring shapes

- **"Declared but never enforced/consulted"** (established in Round 10 §54, §58) recurs three more times: `subscribe()`'s discarded `event_filter` (§70), the idempotency `ttl` parameter in `@idempotent` (never read, folded into §70's writeup scope), and `lexigram-ai-feedback`'s `MAX_FEEDBACK_TEXT_LENGTH`/`MAX_CONTEXT_SIZE` constants (§65) — a parameter or constant exists in the public API/config surface, reads as a real control, and is quietly never wired to anything.
- **"Security control built in isolation, never wired live"** — a sharper variant of fail-open worth naming as its own shape going forward: distinct from a simple except-clause defaulting to allow, this covers whole subsystems where the individual pieces (checksum computation, HMAC math, persistence backend classes, DI registration blocks) are each correctly built, but the wiring that would make the feature *live end-to-end* was never connected. Covers §61 (governance persistence/audit wiring dead due to DI ordering), §66/§67 (audit tamper-verification and purge, both no-ops despite correctly-implemented HMAC/store code existing alongside them).
- **"Fake success" / silent data loss as a fail-open variant** — §64's `FeedbackSystemWithResultPattern` doesn't swallow an exception, it silently discards data while returning `Ok(...)` claiming success, and always returns `Ok([])` on read. A new manifestation of the same root concern (code claims a guarantee it doesn't provide) worth watching for elsewhere.
- **DI container lifecycle ordering** — newly surfaced this round (§61): the orchestrator runs `register_all()` for every provider before running `boot_only()` for any provider. Code in a provider's `register()` that depends on state only set during that same provider's own `boot()` will always see the pre-boot default. Distinct from the "except defaults to allow" family; worth checking other providers for the same shape in a future round.
- **`Result` truthiness footgun** — §77 is a second instance (after Round 10 §59) of an `Err` object being treated as truthy because `Err` has no `__bool__` override; both instances stem from skipping the mandatory `is_ok()` check before consuming a `Result`.
- **No tenant-scoping primitive at the transport layer** — §69's WebSocket endpoint accepting any connection with no auth check and no per-connection filtering is a novel variant of the access-control gaps found in earlier rounds: previous findings were about a *check being skipped*, this one is about no scoping mechanism existing at all at this layer.

---

## 13. Architecture — Admin/Auth/RBAC/Users Boundary Spec (Plans Ready, Not Yet Authorized)

Distinct from the `2026-08-16-security-*` audit series — this is an
**architectural placement** spec (`docs/superpowers/specs/2026-08-17-architecture-admin-auth-rbac-boundaries-design.md`,
amended 2026-08-17), not a security-findings pass. Logged here anyway
because its 7 migration steps touch the same files/packages several
`(s)`-pending security plans do, and because it surfaces one of its own
Critical findings (§2.2 below). Tracked here so neither series starts a
step that collides with the other's uncommitted edits.

**Pre-log readiness check (2026-08-17):** re-verified against live code
before adding to this tracker. Import-linter baseline re-run: still
**25** violations, matches Step 0's inventory. §2.2's hardcoded-deny
`_DefaultAuthorizer` (`lexigram-admin/di/sub_providers/auth.py:101-129`)
and D4's "8 of 9 stores have `ensure_schema()`, `DirectSQLAdminUserStore`
is the holdout" are both confirmed exactly as described. **One gap found
and fixed**: the relay-gateway authorizer call-site count was wrong in
both the spec and the Step 1 plan — `service.py`'s two `.authorize()`
calls (`:215`, `:448`) were dropped from the count (spec said "5
relay-gateway sites" / "4 other sites"; actual is 6 check call sites
total across `controls.py`×1, `job_passthrough.py`×2, `passthrough.py`×1,
`service.py`×2). Corrected in the spec (§4.2 D1 amendment 2, §4.3) and in
the Step 1 plan's Task 1.6 file list/expected-count, same shape as the
"missed sibling call site" pattern this tracker's Round 4-9 specs kept
finding.

### 13.1 Steps summary

| Step | Area | Plan | Gates / gated by | Status |
|---|------|------|------|------|
| 0 | Import-linter baseline repair (25→0 violations) | `plans/2026-08-17-rbac-step0-import-linter-baseline.md` | Gates Step 6. Its `→ lexigram.ui` cluster (7 violations) is owned by `2026-08-15-admin-contributor-refactor.md` Phase 2 (0/24 tasks done — unstarted); its `→ lexigram.security` cluster (7 violations) is owned by the security-plan series (mostly `(s)`, only P0/SQLi/XSS/SSRF/Plugins done) | **Done — green gate verified 2026-08-17 (0 violations)** |
| 1 | Authorizer protocol unification + single bound instance (fixes §2.2 CRITICAL) | `plans/2026-08-17-rbac-step1-authorizer-unification.md` | Independent of Step 0; touches `lexigram-ai-relay-gateway` (5 files) — no known security-plan overlap there | **Done — green gate verified 2026-08-17** (7 commits, 0 violations; spec §6 Step 1 flipped) |
| 2 | Role model unification (`RoleDefinition` → contracts) | `plans/2026-08-17-rbac-step2-role-model-unification.md` | Depends on Step 1 (consumes the unified protocol's role-bearing types) | **Done — green gate verified 2026-08-17** (framework 4 commits + template 1 commit; spec §6 Step 2 flipped) |
| 3 | `AdminUserStoreProtocol.ensure_schema()` (one-file fix) | `plans/2026-08-17-rbac-step3-admin-user-store-ensure-schema.md` | Independent — smallest step, no plan dependency | **Done — verified 2026-08-17** (framework commit + template repo commit; spec §6 Step 3 flipped) |
| 4 | Auth delegation (admin MFA/OTP/password-policy → lexigram-auth) | `plans/2026-08-17-rbac-step4-auth-delegation.md` | ~~Live file collision risk~~ **Resolved 2026-08-17**: the plan's delegation targets (`mfa_service.py`, `email_otp_service.py`, `password_policy_service.py`, `di/sub_providers/auth.py`) were NOT in the external `M` set — only the KEPT orchestrators (`auth_service.py`, `email_verification_service.py`, `password_reset_service.py`) and controllers are externally modified, and Step 4 does not touch them | **Done — green gate verified 2026-08-17** (4 commits; spec §6 Step 4 flipped; parity matrix `plans/2026-08-17-rbac-step4-parity-matrix.md`) |
| 5 | Admin principal bridge (`AdminPrincipalProviderProtocol`) | `plans/2026-08-17-rbac-step5-admin-principal-bridge.md` | Depends on Step 1 (needs the single bound authorizer instance to actually verify the §2.2 mutation-path fix) | **Done — green gate verified 2026-08-17** (framework 2 commits + template 1 commit + applied-principal mode; spec §6 Step 5 flipped) |
| 6 | Boundary locking (import-linter contracts + private-access lint + CI) | `plans/2026-08-17-rbac-step6-boundary-locking.md` | **Blocked on Step 0** (needs the green baseline) | **Done — green gate verified 2026-08-17** (contracts 8+9 added + probe-tested; private-access lint clean after 1 real fix + 2 exempted doc demos; template gate + Makefile wiring; spec §6 Step 6 flipped) |

**Recommended order:** 0 → 1 → 3 → 2 → 4 → 5 → 6 (3 can run in parallel with 1/2 — no shared files; 4 should wait for a quiet window on `admin/auth/services/*`, see §13.2).

### 13.2 Collision watch

- `2026-08-15-admin-contributor-refactor.md` Phase 2 (0/24 tasks, unstarted) claims the same 7 `→ lexigram.ui` files Step 0 Task 0.5 defers to it. **Do not fix those 7 files from Step 0** — Step 0 only files the tracking entry.
- The security-plan series was expected to own the 7 `→ lexigram.security` violations (Step 0 Task 0.2 mapping), but the mapping found **7/7 rows NO-OWNER or NO-PLAN** → Step 0 Task 0.6 fixed them in-lane (removed the duplicated `SecretNotFoundError`, rerouted 7 ambient hashing consumers to the documented core `from lexigram import hashing` ambient capability, deduped `Sha256Hasher` usage in sql via ambient `hash_hex`). Verified 2026-08-17: 0 violations, ruff+mypy clean, scoped suites 1,257 passed.
- As of 2026-08-17, `git status` shows `admin/auth/services/{auth_service,email_verification_service,password_reset_service}.py`, `admin/controllers/{auth,profile,setup}.py`, and several other admin files as uncommitted (`M`) from work outside this spec's scope — this is exactly Step 4's target file set. The Step 0 plan's own caution note applies here too: a concurrent agent syncs/reverts uncommitted tracked-file edits in this area. Confirm a quiet window before starting Step 4.
- Step 1 landed 2026-08-17 with 7 commits (`f4456271` → `caa7df95`). Pre-existing, unrelated: the 6 `tests/e2e/test_admin_email_verify_http_e2e.py` failures (unawaited `AsyncMock` coroutine from the committed login-MFA flow at `controllers/auth.py:246` — same failure reproduces from HEAD without Step 1; belongs to the email-verify feature owner, not RBAC). Note for Step 1.7's gate: combined multi-package mypy runs trip a pre-existing namespace-shim collision ("Duplicate module named lexigram") — run mypy per-package.
- Step 2 landed 2026-08-17 with 5 commits (framework: `feat(contracts): single RoleDefinition`, `refactor(auth): re-export contracts RoleDefinition`, `refactor(rbac): single contracts RoleDefinition, drop Role/Permission/AdminRole`; template: `refactor(template): use contracts RoleDefinition`; spec flip uncommitted). The blanket model rename (`AdminRole` → `RoleDefinition`) is limited to the *model type*; class names `AdminRoleService`/`AdminRoleServiceProtocol`/`AdminRoleStoreProtocol`/`AdminRoleSqlStore`/`StarterAdminRolesDataSource/Resource` deliberately kept. `lexigram.admin.auth.permissions.Permission` (per-user permissions feature) and contracts `ai/llm.py` chat `Role` enum are separate types, untouched (clean-sweep grep would surface them — expected). CAUTION for Task 2.1's commit: `git add lexigram-contracts/` swept in 7 foreign files then being edited by the concurrent agent (storage/url_safety/mcp/tenancy + 2 tests) into commit "feat(contracts): single RoleDefinition..." — their work is preserved in git history, but use explicit-path staging thereafter.
- Step 6 adds two new `.importlinter` contracts (`admin-import-allowlist`, `auth ⊥ admin`) plus a new template-repo `.importlinter`. If any `(s)`-pending security plan also edits `.importlinter` ignore blocks before Step 6 lands, diff both against the Step 0 golden snapshot (`/tmp/lint_baseline.txt`) before merging.
- Step 5 landed 2026-08-17 (framework: `feat(contracts): AdminPrincipalProviderProtocol bridge`, `feat(admin): app principal adapter + principal_source config`; template: `feat(admin): app principal bridge, delete record glue`; contracts recreated as 2 commits after the concurrent agent's sync cycle swallowed the first — see the Task 5.1 amend incident below). **Git-safety incident recurrence**: commit `03792c9b` (5.1) was later DROPPED from HEAD entirely by the concurrent agent's chain rewrite; survived as untracked `principal.py` + `M` `admin/__init__.py` exports and was restored as a fresh 3-file commit. Second `git commit --amend`-class incident: the concurrent agent's sync landed between `git add` and `git commit --amend` in Task 5.1, attaching my export lines to their `cc006e60` — rule reaffirmed: commit immediately, never `--amend` when another process stages concurrently.
- Step 6 landed 2026-08-17 (framework: `feat(admin): import-linter contracts admin allowlist + auth perpendicular admin`, `feat(admin): export AdminRoleStoreProtocol as public seam`, `feat(tools): private-access lint + public InjectableAutoProvider`; template: `feat(admin): template import-linter gate, roles store via protocol seam` + `import-linter` dev dep). Self-audit fixes: `_InjectableAutoProvider` → public `InjectableAutoProvider` (`app/injectable_provider.py`, exported via `app/__init__`, `di/module/decorator.py` via the seam); `StarterAdminRolesDataSource` converted from constructing private `AdminRoleSqlStore` to container-injected `AdminRoleStoreProtocol`. `make ci` full-run status: **blocked only by pre-existing foreign debt — 36 files across 15 packages fail `ruff format --check` (none touched by this lane; my one unformatted file `contracts/admin/principal.py` was formatted) and the 6 pre-existing email-verify e2e failures**. Everything else in the ci chain is green and verified step-by-step (ruff, both boundary linters incl. probe-tested negative cases, mypy core+web+11 typed pkgs, scoped suites: contracts 1750, core unit 2856, admin unit+integration 4257, tools 3, template 86).
- Step 4 landed 2026-08-17 with 4 commits (`docs(auth): delegation parity matrix`, `refactor(admin): MFA delegates TOTP math to lexigram-auth`, `refactor(admin): email OTP delegates to lexigram-auth primitives`, `refactor(auth): single password policy implementation in lexigram-auth` + a style commit). Plan premise refuted + delta recorded in `plans/2026-08-17-rbac-step4-parity-matrix.md`: admin email-OTP was random-code, NOT TOTP; delegation keeps digest-at-rest + atomic consume as store semantics. lexigram-auth's `PasswordPolicy` default common list expanded from 14 → 76 entries (ported from admin, lowercased; case-insensitive now — stricter, no regression; lexigram-auth suite 591 passed). `AdminPasswordPolicyService` is a thin adapter (`policy: PasswordPolicyProtocol | None` defaulting to admin rule set; email-containment kept admin-side). Gates: `test_admin_auth_http_e2e.py` 13 passed, admin unit+integration 4266 passed (6 skipped), duplication grep = 0, ruff + mypy (892 files) clean, import-linter 9/9 rc=0. **Git-safety incident (3rd, self-inflicted)**: a directory-scoped `git add` swept 3 foreign `M` files into the style commit — fixed via `git reset --soft` + `git restore --staged` before push; rule reaffirmed: explicit-file paths only, check `git show --stat` after every commit.

- `plans/2026-08-16-security-rbac-superadmin.md` executed 2026-08-18 (commit `d1bcc93`, carries this row). D1: all four check sites + `_user_has_edit_permission` honor the configured `super_admin_role` via DI-resolved `AdminRbacConfig`; controllers share `_is_super_admin(**settings)` (bundle_provider registers eagerly, injects into ImpersonationService/SettingsController/SetupController; setup wizard grants the configured role). Extra `widgets.py:76` page gate removed (page now gated only via `page_permission_code`). D2 fresh-instance defects eliminated — no ad-hoc `AdminRbacConfig()` at call sites (previously settings/impersonation honored hardcoded `"superadmin"` under a configured policy). D3: `RolesResource.can_update` consults the configured role via `resource.can_update` + `handler.can_update` wiring; 403 before any partial write; generic `authorizer.can_update` untouched. Verification: admin unit 4190 passed/2 skipped; admin e2e = same 6 pre-existing failures, zero new; full non-integration suite 28255 passed/22 failed (same 7 known buckets), zero new; ruff check clean repo-wide; mypy + compileall clean. Plan boxes flipped except 5.2 (33 pre-existing unformatted files — none in this plan) and 5.5 (blocked by the 22 known failures; substituted non-integration run). One test-side drift fixed during review: `test_pool_health_controller.py` still called `_user_is_superadmin` statically after the D-1 helper became an instance method. Two-pass review recorded inline in the plan (`## Review`). Commit: explicit-path staging only (per the rule above).

- 5.2/5.5 follow-up 2026-08-18 (commits `00f5459`, `d3df697`): repo-wide format debt cut 33 → 3 (30 files formatted; the 3 remaining are under concurrent uncommitted edits — `admin/controllers/auth.py`, `ai-agents executor/streaming.py`, `ai-memory backends/cache.py`). All 22 known non-integration failures fixed except 1 (the 21): 6 admin email-verify e2e — REAL BUG `auth.py` login-MFA stored `factor = self._mfa_service.get_factor()` (unawaited coroutine; broke email-OTP factor + session JSON serialization); 5 governance relay-log tests were time-dependent (window cutoff `clock.now() - days` vs entries dated 2026-08-10 — rotted on Aug 18; pinned `FixedClock` like the `daily_usage` test); 7 mcp-script-mode tests imported the pre-migration `lexigram.cli.commands.mcp` (→ `lexigram.ai.mcp.cli.commands`); 1 bed-split test imported the testkit `TestEnvironment` instead of the bed variant (`fixtures.bed`, has `create_mock`); 1 parity smoke unwraps `Ok(report)`; 1 theme test asserted no `.bg-primary` — updated to plain-class form (opacity variants are a documented exception in `styles/theme.py`). Final state: full non-integration 28276 passed, 1 failed (`scripts/test_registry.py` — blocked on the concurrent lane's uncommitted `scripts/audit/generators/registry.py`). **Fixed 2026-08-18:** `EXPECTED_GENERATOR_NAMES` gained the 3 new generator entries registered by the now-committed registry lane (`8b3afbc0`) — 4 passed. Also fixed 9 pre-existing lint errors in the 4 touch-test files + 8 UP017 `timezone.utc` → `UTC` in relay tests. Note: the auth.py commit necessarily carries the concurrent lane's pre-existing format-only churn in that file (11 rewrapped hunks, 1 semantic hunk mine — verified).

### 13.3 Per-step tasks

**Step 0** (6 tasks): 0.1 lock baseline repro (confirm 25) · 0.2 map security-cluster violations to owning specs · 0.3 fix the 9 `lexigram.contracts → *` violations · 0.4 fix `monitor → tasks` and `di → serialization` · 0.5 file the ui-cluster tracking entry (deferred to contributor-refactor) · 0.6 close out (green gate + tracker)

**Step 1** (7 tasks): 1.1 union protocol in contracts · 1.2 `AuthorizationService` implements the union (real enforcement, not hardcoded deny) · 1.3 one bound instance — admin DI binds it under the union protocol · 1.4 `PermissionService` honest async, protocol-typed (full async conversion: `_check_access` awaited, 9 public `can_*` methods async, sync UI render chain hoisted to precomputed dicts, 0 type-ignores) · 1.5 `AdminRoleService` same bound instance, no concrete class · 1.6 relay-gateway call-site audit (6 sites, corrected 2026-08-17 — all argument-safe, no change) · 1.7 sweep, no stale refs — all **Done 2026-08-17** |

**Step 2** (5 tasks): 2.1 `RoleDefinition` in contracts (frozen dataclass, scope-forward) · 2.2 lexigram-auth re-exports it · 2.3 delete admin `Role`/`Permission`, update `rbac` internals · 2.4 template data sources follow the unified model · 2.5 full-repo sweep + spec flip

**Step 3** (3 tasks): 3.1 protocol method + SQL store implementation · 3.2 template call site private→public · 3.3 sweep, no other private-store callers

**Step 4** (5 tasks): 4.1 parity inventory (admin service ↔ lexigram-auth counterpart) · 4.2 `AdminMfaService` delegates TOTP math · 4.3 `AdminEmailOtpService` delegates code gen/verification · 4.4 `AdminPasswordPolicyService` delegates to a `PasswordPolicyProtocol` impl · 4.5 e2e gate + spec flip

**Step 5** (4 tasks): 5.1 contracts — `AdminPrincipal` + `AdminPrincipalProviderProtocol` · 5.2 admin — config switch, adapter, DI binding · 5.3 template implements the provider, glue deleted · 5.4 framework regression + spec flip

**Step 6** (5 tasks): 6.1 private-access lint tool (`tools/lint_private_access.py`) · 6.2 framework `.importlinter` — admin allowlist + auth⊥admin · 6.3 template-repo import-linter config · 6.4 CI wiring (`make ci`) · 6.5 spec flip + repo status sweep

---

## 14. Architecture — `lexigram.reactive` Native Stream Layer + Structured Admin Contributions (Spec + Plan Fixed, Not Yet Authorized)

Distinct from the `2026-08-16-security-*` audit series and from §13 — this
is a third **architectural placement** spec, adding a native reactive
stream engine to core (`lexigram.reactive`) plus closing the
raw-HTML-from-packages gap in admin contributions. Logged here for the
same reason as §13: tracked centrally so no other lane starts a step that
collides with these files.

**Spec:** `docs/superpowers/specs/2026-08-18-architecture-lexigram-reactive-streams-design.md`
**Plan:** `docs/superpowers/plans/2026-08-18-lexigram-reactive.md` (15 tasks)

**Review + fix pass (2026-08-18):** both documents were reviewed for
consistency, architectural alignment, and security, then fixed in place.
No sign-off/authorization has been given yet and no task has been
executed — 0/15 tasks done.

**Spec fixes applied:**
- D1 bullet list rewritten to match what Tasks 1-15 actually implement — fixed a `Stream`/`Subject` hot-vs-cold terminology inversion (spec previously called `Stream` hot/live; per the plan, `Stream` is cold/single-pass and `Subject` is the only hot/multicast primitive), narrowed operator/field lists to actually-implemented items, required `ops`+`share` in the root facade `_EXPORTS`.
- D2's `sse_from_stream` bullet gained a "Not an auth boundary" clause — it streams whatever it's given; the caller's route is responsible for gating access (the existing admin SSE route is gated by `AdminRouter`'s middleware stack, not the handler).
- D3's `SubjectAdminEventHub` bullet gained a "Must preserve `AdminEventHub`'s per-user targeting" note, citing `action_executor.py`'s reliance on `target_users`-scoped delivery (see the plan fix below).
- §4 decision table: 2 new rows (`Result[T,E]`-not-used-in-operators traceability; `SubjectAdminEventHub` target_users filtering resolved as "Yes — required, not optional").
- §6 out-of-scope table: 4 new rows (`BehaviorSubject`/`ReplaySubject`, `group_by`/`concat`, `delay`/`sample`, `RetryOptions.jitter`) — each with a "not implemented by Tasks 1-15, add when a consumer needs it" rationale.

**Plan fixes applied (bugs found during review, all corrected in the plan document itself, not yet executed):**
- Task 1 — `test_stream_double_iteration_restarts_source` renamed/rewritten to assert single-pass exhaustion (was asserting a replay behavior the implementation doesn't provide); module/class docstrings corrected from "cold, replayable" to "cold, single-pass."
- Task 3 (`merge`) and Task 4 (`debounce`/`throttle`) — `with contextlib.suppress(...)` → `with suppress(...)` (the file only imports `from contextlib import suppress`; the bare-module form would `NameError` at runtime).
- Task 4 (`debounce`) — hardcoded `timeout=1.0` poll replaced with `poll = seconds if have_item else None`, so silence-detection timing matches the caller's `seconds` argument instead of being capped to ~1s granularity (real latency bug, not caught by the plan's own FakeClock-driven tests since those bursts complete before any timeout fires).
- Task 5 (`share()`) — RUF006 violation fixed: the pump task and its done-callback-scheduled completion task are now both held by a module-level `_background_tasks: set[asyncio.Task[Any]]` (a bare local `task` variable doesn't keep a task alive — GC-eligible mid-flight); `asyncio.get_event_loop()` → `asyncio.get_running_loop()`.
- Task 7 — `_EXPORTS` dict was missing `"ops"` and `"share"` entries despite the task's own "Produces" line, its own facade test (`lexigram.ops.map(...)`), and the showcase doc all requiring them; both added.
- **Task 10 (`SubjectAdminEventHub`) — the security-relevant fix.** The plan's original `publish(event, target_users=None)` silently ignored `target_users` (broadcast to everyone regardless) and `subscribe(user_id=None, ...)` never filtered on `user_id` ("kept for API parity" per its own docstring). `action_executor.py`'s `_publish_action_notification`/`_publish_action_failure` rely on `AdminEventHub.publish(event, target_users=[caller_id])` today to keep each admin's own action-result notification private to that admin — the plan's drop-in replacement would have been a confidentiality regression (every admin sees every other admin's action results). Fixed via a `_TargetedEvent` wrapper dataclass carried inside the `Subject`; `publish()` wraps the event with `target_users`, `subscribe()` filters on `target_users is None or user_id in target_users` before the existing resource/event-type filters. Added a regression test (`test_subject_hub_respects_target_users`) and confirmed Task 13's broadcast-only dashboard widget (`hub.subscribe()` with no `user_id`) is correctly compatible — it now sees only broadcast events by construction, never another admin's targeted notification.

### 14.1 Tasks summary (13/15 done)

| Task | Area | Status |
|---|---|---|
| 1 | Reactive core — `EventStream` protocol, `Stream`, `pipe`, exceptions | done |
| 2 | Transform operators — `map`, `filter`, `scan`, `distinct` | done |
| 3 | Control + combine operators — `take`, `skip`, `merge`, `catch` | done |
| 4 | Time operators — `debounce`, `throttle`, `buffer`, `window` | done |
| 5 | Hot streams — `Subject`, `share` | done |
| 6 | `retry` operator with `RetryOptions` | done |
| 7 | Core facade exports + docs example | done |
| 8 | Events bridges — `from_store`, `from_bus`, resilience adapter | done |
| 9 | Web responder — `sse_from_stream` | done |
| 10 | Admin adoption — `SubjectAdminEventHub` | done |
| 11 | Full CI + boundary verification + CHANGELOG | done |
| 12 | lexigram-events admin contribution — live events widget | done `7bc51afc` |
| 13 | lexigram-admin contribution — reactive activity widget | done `a1531c8` |
| 14 | Full CI, boundary gate, CHANGELOG (contribution surfaces) | done `eb81e03` |
| 15 | Structured management pages — host renders all page HTML | pending |

**Execution notes (T12–T13, 2026-08-18):**
- Task 12 (`live_events` widget): the handler subscribes to the dispatcher **synchronously in `__init__`** (a lazy/background subscribe races the test+real flows because `store.append`/`publish` do not always yield before dispatch); the widget drains into a local cache and reads `from_store(...).pipe(ops.take(10))` at render time with `correlation_id` dedupe. `get_dashboard_widgets` grew from 2 → 3 widgets (test updated).
- Task 13 (activity widget): the plan's snippet subscribed fresh inside `_render_activity` — on a hot single-pass `Subject` that drops everything published before the subscriber's first `__anext__`, so the plan's own test ordering (publish → render) could never see events, and `hub.subscribe().pipe(...)` is invalid (async generators have no `pipe`). Implemented instead as a **persistent background tail** (`_drain_activity` task, `deque(maxlen=50)` cache, broadcast-only via `hub.subscribe()` with no `user_id`) plus **lazy render-time resolution** — if `self._hub` is `None` and a `resolver` is provided, the hub is resolved and the tail started on first render. DI binding registered in `di/sub_providers/realtime.py` (where `AdminEventHub` lives) rather than `bundle_provider.py`. Tests landed at `tests/unit/contributors/test_reactive_activity_widget.py` (a `StubResolver` implementing the full `ContainerResolverProtocol`); the plan's `== "RESOURCE_UPDATED"` assertion was corrected to the actual `StrEnum` value `"resource.updated"`. Commits `a1531c8` (this task); the two earlier commits `322edaa1`/`77983a19` are superseded by it.

---

## 15. Architecture — Admin Dashboard Widgets, Real Data Wiring (Executed 11/11, 2026-08-18)

Distinct from §13 and §14 — a fourth **architectural placement** spec,
replacing eight framework packages' hardcoded/`EmptyContent` admin
dashboard widget placeholders with real DI-resolved data via small
`@runtime_checkable` capability protocols. Directly collides with §14's
Task 13 on one branch (see below) — logged here for the same reason as
§13/§14: tracked centrally so no other lane starts a step that collides
with these files.

**Spec:** `docs/superpowers/specs/2026-08-18-architecture-admin-dashboard-widgets-real-data-design.md`
**Plan:** `docs/superpowers/plans/2026-08-18-admin-dashboard-widgets-real-data.md` (Tasks 0-10)

**Review + fix pass (2026-08-18):** the plan previously existed only as a
single file with a one-paragraph inline "Spec:" note, not a real
spec/plan pairing — a process gap relative to the `verify → spec → plan →
execute` convention used elsewhere in this tracker. A standalone spec was
written, and both documents were verified against live source and fixed
in place. No sign-off/authorization has been given yet and no task has
been executed — 0/11 tasks (0-10) done.

**Collision with §14:** this plan's Task 10 and §14's Task 13 both
targeted the same `if widget_name == "activity":` branch in
`lexigram-admin/src/lexigram/admin/contributors/core.py` with
incompatible implementations (`AuditStoreProtocol`-backed summary vs.
`SubjectAdminEventHub`-backed live feed). Resolved by **sequencing, not
merging**: §14's Task 13 (richer, already fixed) owns `activity`; this
plan's Task 10 was cut down to `health`/`chart_metrics`/`render_health_check`
only and drops the `activity` branch entirely — see spec §4 D1.

**Spec fixes / findings applied:**
- Disproved an initial DI-bug hypothesis (Task 2's named `AuthActivityTracker`
  registration) by reading the resolver directly — the container correctly
  awaits a lambda-returned coroutine; the registration is dead code, not a
  bug, and was removed rather than "fixed."
- Confirmed real bugs via live-source verification: Task 8's
  `tasks_adapter.get_stats()` iterating `get_worker_stats()` breaks under
  both possible real return shapes — fixed to read `get_pool_stats()`'s
  flat `active_workers` field. Task 5's `_uptime_seconds()` returned raw
  `time.monotonic()` with no captured start reference — fixed with a
  module-level `_PROCESS_START`. Task 7's `oldest_age_minutes` and Task 10's
  `health_payload` were dead/never-assigned locals — deleted.
- Flagged, not silently patched: `SqlAuditStore.query()` doesn't
  auto-scope by tenant, and `WidgetParams`/`render_widget()` carry no
  tenant context (spec §4 D3) — see gap-resolution below for final
  disposition.

**Gap-resolution pass (2026-08-18):** two gaps were left open by the
initial review; both re-examined and closed:
- **Task 4 (`tasks_summary`/`avg_duration`) hardcoded `running_tasks`/
  `failed_tasks`/duration** — previously left as-is pending verification
  of the concrete stats source. Verification found the original draft's
  dependency wiring was actually broken: `self.scheduler` (injected as
  `scheduler_or_metrics`) is a bare `TaskScheduler()`
  (`lexigram-tasks/src/lexigram/tasks/scheduling/scheduler.py:53`) with no
  stats method at all — calling `.get_worker_stats()` on it would have
  raised `AttributeError` at runtime, not returned stub data. Fixed by
  rewiring both handlers to `self.worker_pool`
  (`WorkerPool.get_pool_stats()`, sync,
  `lexigram-tasks/src/lexigram/tasks/execution/pool.py:203-229`), which has
  real `active_workers`/`total_jobs_succeeded`/`total_jobs_failed`/
  `average_processing_time` keys, plus `di/provider.py`'s
  `_register_admin_widgets` factory wiring. Also caught and fixed a units
  bug: `average_processing_time` is in **seconds**
  (`execution/worker.py:189`), not ms as the stub's `f"{avg_ms}ms"` label
  implied. P95 duration has no data source anywhere in `lexigram-tasks`
  (no percentile tracking exists) and stays a documented `0.0` placeholder
  rather than an invented value.
- **`activity`-widget tenant scoping (spec §4 D3)** — confirmed to have
  zero remaining code manifestation in this plan: Task 10's `AuditQuery`
  usage was removed by the D1 collision fix, not merely deferred, and
  §14's Task 13 (which now owns `activity`) uses `SubjectAdminEventHub`/
  `AdminEvent`, not `AuditStoreProtocol`, so it isn't affected by this gap
  either. The broader architectural gap (no `tenant_id` path into
  `WidgetParams`/`render_widget`, affecting every contributor's signature)
  remains a standing note for whoever next authorizes an
  `AuditStoreProtocol`-backed widget — implementing that cross-cutting
  contracts change now, with no concrete consumer, would be speculative
  work rather than a fix.

### 15.1 Tasks summary (11/11 done, executed 2026-08-18)

| Task | Area |
|---|---|
| 0 | Dashboard capability protocols (`lexigram-contracts/admin/stats.py`) |
| 1 | Pool statistics + migration status handlers (`lexigram-sql`) |
| 2 | Auth activity tracker (`lexigram-auth`) |
| 3 | Active sessions, failed logins, token refresh handlers (`lexigram-auth`) |
| 4 | Tasks summary + average duration handlers (`lexigram-tasks`) |
| 5 | Server status + request metrics handlers (`lexigram-web`) |
| 6 | Cache backend stats + hit/miss and eviction handlers (`lexigram-cache`) |
| 7 | Dead-letter count widget (`lexigram-events`) |
| 8 | Queue stats capability implementers + widget handlers (`lexigram-queue`/`lexigram-ai-workers`) |
| 9 | Named health check on the monitor registry (`lexigram-monitor`) |
| 10 | Admin core widgets — health, chart metrics (`lexigram-admin`; `activity` intentionally excluded, see §14 Task 13) |

**Execution (2026-08-18):** all 11 tasks landed. Commits: Task 0 `9d1fb7f`, Task 1 `370352c`, Task 2 `a6519a5`, Task 3 `fe8ff99`, Task 4 `dd5ede7`, Task 5 `79706be`, Task 6 `fe6a45d`, Task 7 `75205d4`, Task 8 `420edfd`, Task 9 `514adc1`, Task 10 `36408a3`.

**Execution deviations from plan snippets (verified against live source, documented here):**
- Task 8: `DeadLetterQueueWorker` already shipped `async get_stats() -> DLQStats` (used by `health_check()` and tests) — the plan's colliding sync dict `get_stats()` was dropped; a live `dead_letter_count` attribute was added instead (incremented on new dead letters, decremented once per successfully replayed item via a `metadata["replayed"]` guard, since `_dlq_loop` auto-retries repeatedly). `LexigramTasksAdapter.get_stats()` is async (the plan's sync `self._provider` shape didn't exist; `TaskQueueProtocol.get_task_count()` is async, `processing` has no source and reports 0). Queue DI still injects the raw backend, which lacks the capability — widgets degrade until an app binds a `QueueStatsProtocol`/`DlqStatsProtocol` object.
- Task 9: registry test landed at `lexigram-monitor/tests/unit/test_registry_named_check.py` (flat layout; the plan's `tests/unit/health/` dir does not exist). `_check_liveness`/`_check_readiness` refactored onto the shared `_run_named` helper with behavior preserved (unknown names still skipped in loops).
- Task 10: `run_all()` returns `(HealthStatus, {"liveness": ..., "readiness": ...})`, not `(payload, {"status": ..., "checks": ...})` — the health widget aggregates checks across both probe lists and reads status from the returned payload; `HealthStatus` values are lowercase, so the plan's `.upper()` mapping was replaced by a `_status_from_value` helper. `_empty()` helper added for placeholders; `activity` branch left untouched per the §14 collision. DI: the contributor resolves `HealthOverviewProtocol`/`MetricsReadbackProtocol` via `resolve_optional` in `on_admin_boot` (passing `None` when unbound — monitor currently binds neither key, so managed-mode degrade matches the plan's "pass None when absent").

**Verification:** scoped suites green — auth 616, tasks 511, web 1419, cache 842, events 926, queue 539, monitor 331, admin full 4549 (CI-gated); `ruff check` clean on all touched files.

---

## 16. Commands (from AGENTS.md)

```bash
uv run ruff check . && uv run ruff format --check .   # lint
uv run mypy lexigram/src/                             # typecheck core
uv run pytest --tb=short --cov-fail-under=80          # aggregate suite
uv run pytest <pkg>/tests/                            # scoped
```

Constraints: no worktrees, no branches unless asked; commit only when
explicitly asked; every changed line must trace to an audit finding.