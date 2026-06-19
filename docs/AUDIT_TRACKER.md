# Security Audit — Implementation Tracker

**Generated:** 2026-08-16
**Source:** `docs/superpowers/specs/2026-08-16-security-architecture-audit-findings.md`
**Process:** verify → spec → plan → execute → two-pass review

Status of all 10 security remediation areas from Round 1-2 of the audit.
Each plan is a multi-task, verification-gated workstream; nothing has been
executed yet (all plans Not started). Round 3 (§6 below) added 5 more
findings areas but is findings-only — no spec or plan has been authorized
for it yet.

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

---

## 6. Round 3 — Findings Only (No Spec/Plan Yet)

Round 3 added 5 more areas to `docs/superpowers/specs/2026-08-16-security-architecture-audit-findings.md` (§13-17), produced via direct sequential grep/read investigation (the background research agents failed on an account-level spend limit before producing output). Per standing instruction, this round is **findings only** — no spec, plan, or remediation code has been authorized or written for any of these. Do not fabricate spec/plan filenames for these rows until the user explicitly asks for them.

| # | Area | Doc section | Severity mix | Spec | Plan | Status |
|---|------|--------------|------|------|------|--------|
| 11 | **AI guard / prompt-injection** | §13 | Critical ×2, High ×2, Med ×1 | — not authorized | — not authorized | Findings only |
| 12 | **GraphQL security** | §14 | Critical ×2, High ×1, Med ×1 | — not authorized | — not authorized | Findings only |
| 13 | **Media upload / processing safety** | §15 | High ×2, Med ×2 | — not authorized | — not authorized | Findings only |
| 14 | **Notification / webhook injection** | §16 | High ×1, Med ×1, Low ×1 | — not authorized | — not authorized | Findings only |
| 15 | **Rate-limiting / DoS resilience** | §17 | Critical ×1, Med ×1, Low ×1 | — not authorized | — not authorized | Findings only |

**Recurring shape (per master doc §1):** three of these five (AI guard's `@guarded` decorator, GraphQL's depth/complexity/introspection layer, web's rate-limit `rules` config) are the "orphaned correct implementation" pattern — a well-built implementation exists and nothing calls it, not even a competing weaker path. This is the same root-cause family as Round 1-2's Pattern A, one step more extreme.

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