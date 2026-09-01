# 01 — Bug Audit & Fixes (2026-09-01)

Scope: `experimental/apps/lexigram-admin` (with one supporting change in the
playground). Bugs were found by booting the real provider lifecycle
(`register → boot → mount_to_app`) against SQLite via
`playground/serve.py` and exercising the full first-run → login → CRUD flow
over HTTP, combined with static tracing of the middleware and DI wiring.

Legend: **B** = bug, **P** = performance. Severity reflects impact on a
fresh production install.

---

## B1 (critical) — Super admin locked out of every resource

**Symptom.** The first account created by the setup wizard (granted the
configured `superadmin` role) received **403** on every resource route
(`/admin/products`, …) and an **empty sidebar**. A fresh install was
effectively unusable.

**Root cause.** The setup wizard grants
`AdminRbacConfig.super_admin_role` (default `"superadmin"`), but every
permission engine downstream only recognized `is_superuser == True` or the
hardcoded role names `admin` / `superuser`
(`lexigram-auth _check_mixin.has_any_permission`). Nothing ever translated
"holds the configured super-admin role" into "bypasses permission checks".

**Fix (defense in depth, all layers consistent).**

| Layer | Change |
| ----- | ------ |
| `middleware/auth.py` | New `_mark_super_admin(user)` runs right after `_load_user`: holders of the configured role get `user.is_superuser = True` on the request's user record. Single choke-point every authenticated request passes through, so *all* downstream checks (authz middleware, nav filtering, lexigram-auth bypass) see one consistent flag. Guests/None are never touched; records that reject attribute assignment log `auth.super_admin_mark_unsupported` and degrade gracefully. |
| `middleware/authorization.py` | `_is_super_admin(user)` (strict `is True` on `is_superuser`, or configured role via `rbac.super_admin.is_super_admin`) short-circuits `_resource_capabilities` to all-True capabilities. The permission engine is never consulted for super admins — it has no knowledge of the configured role. |
| `ui/templates/shell_sections.py` | `_user_has_permission` honors `is_superuser` for both dict-shaped and object-shaped users, so the sidebar renders all items for super admins. |
| `di/bundle_provider.py` | Both middlewares receive `super_admin_role` from `(config.rbac or AdminRbacConfig()).super_admin_role` — configuration is the single source of truth; renaming the role in config Just Works. |

**Why this design.** Alternatives considered and rejected:
- *Granting `*` permission at setup*: leaks into permission listings, hard
  to revoke, and doesn't cover accounts given the role later.
- *Hardcoding `superadmin` in the engines*: violates the no-magic-strings
  principle and breaks deployments that rename the role.
- Marking at load time keeps role → capability translation in exactly one
  place and works for any future engine that respects `is_superuser`.

**Tests.** `tests/unit/middleware/test_super_admin_marking.py` (marking,
custom role names, non-holders untouched, None-safety, authz capability
bypass, regular users still denied); superuser cases in
`tests/unit/ui/test_shell_sections.py`.

---

## B2 (high) — Sidebar/`middleware` permission scheme mismatch (`.read` vs `.view`)

**Symptom.** A user granted `products.view` (the permission the
authorization middleware actually checks) still saw no "Products" link,
because the sidebar inferred `products.read` from the URL. Users granted
only `.view` could reach pages by typing URLs but had invisible navigation.

**Fix.** `shell_sections.py` now infers **both** `{resource}.view` and
`{resource}.read` for resource links and shows the item when the user holds
either. Explicitly-declared `permission` keys on nav items are unchanged.

**Long-term note.** The dual-scheme acceptance is deliberate: it is
backward compatible with existing `.read` grants while matching the
middleware's `.view` scheme. Roadmap item R6 (doc 02) proposes unifying on
a single canonical scheme with a documented migration.

**Tests.** `TestInferredPermissionSchemes` in
`tests/unit/ui/test_shell_sections.py` (`.view` shows, `.read` shows,
neither hides, superuser sees all).

---

## B3 (critical) — First admin bricked by email verification

**Symptom.** With email verification enabled (the default) and no mailer
configured (the norm on a fresh install), the first admin could **never log
in**: login redirected to "verify your email", the verification email could
not be sent, and there was no other account to fix it with. Total lockout.

**Root cause.** The setup wizard treated the first admin like any
self-registered user and gated login on an emailed link.

**Fix.** The operator has already proven control of the deployment by
presenting the **setup token** — a strictly stronger ownership proof than a
mailed link. The first admin is therefore verified out-of-band:

- `AdminEmailVerificationStoreProtocol.mark_verified(user_id)` — new
  protocol method; SQL store implements it as an idempotent upsert
  (`COALESCE` preserves an existing `email_verified_at`; pending tokens are
  cleared).
- `AdminEmailVerificationService.mark_verified(user_id)` — delegates to the
  store and writes an `EMAIL_VERIFIED` audit event with
  `{"reason": "out_of_band_setup"}` so the bypass is fully auditable.
- `controllers/setup.py` calls it after first-admin creation. The service is
  looked up via `getattr(..., "mark_verified", None)`: a custom verification
  service that predates the protocol method falls back to the legacy
  email-sending path instead of crashing. Failure of the auto-verify itself
  is caught, logged (`setup.first_admin_auto_verify_failed`), and never
  fails setup.

**Tests.** Store: `test_mark_verified_upserts_and_clears_token`,
`test_mark_verified_preserves_existing_verified_at`
(`tests/unit/auth/test_email_verification_store.py`). Service:
`test_mark_verified_delegates_to_store`,
`test_mark_verified_audits_out_of_band_verification`
(`tests/unit/auth/test_email_verification_service.py`). Verified live:
fresh DB → setup → `email_verified_at` set at creation → login goes straight
to `/admin/` with enforcement **enabled**.

---

## B8 (critical, found during verification) — `claim_first_admin` false "already complete" on SQLite

**Symptom.** On SQLite, submitting the setup form **created the account but
told the operator "Setup is already complete. Please log in with your
existing account."** — the entire success path (audit event, auto-verify,
success notice) was skipped. This also masked B3's fix during verification.

**Root cause.** `DirectSQLAdminUserStore.claim_first_admin` decides
inserted-vs-lost-race from `QueryResult.row_count`, but the
aiosqlite-backed pipeline reports `row_count=0` even for successful
`INSERT … SELECT … WHERE NOT EXISTS` statements. Both the winner and the
loser looked identical.

**Fix.** When neither returned rows nor `row_count` prove the insert, the
store now **selects back the per-call UUID**. The admin id is a fresh
`uuid4()` generated by *this* call, so its presence in the table proves this
call inserted the row — a concurrent submission would have inserted a
different id. Race-safe, driver-agnostic, and zero extra cost on drivers
that report properly (Postgres RETURNING / real row counts short-circuit
before the fallback).

**Tests.** `test_direct_sql_claim_verifies_insert_when_row_count_unreported`
and `test_direct_sql_claim_errs_when_row_absent_after_zero_count` in
`tests/unit/controllers/test_setup_claim_first_admin.py` (existing
concurrency tests unchanged and passing).

---

## B4 (low) — Duplicate `<title>` on standalone pages

**Symptom.** Login/setup/verify pages emitted two `<title>` tags (one from
the base HTML document, one from `StandaloneLayout.render_head_content`),
producing wrong browser-tab titles and invalid HTML.

**Fix.** `StandaloneLayout` now overrides `render()` to compose the full
`"Page | App"` title once and pass it to the base document renderer; the
extra `<title>` in `render_head_content` was removed. Exactly one title tag
per page, verified live (`<title>Login | Lexigram Admin</title>`).

---

## B5 (high DX) — `bootstrap.create_app()` returned an empty app

**Symptom.** The documented one-call entry point built an `AdminProvider`,
**discarded it**, and returned a bare Starlette app with no admin mounted —
every route 404. The "hello world" of the package didn't work.

**Fix.** `create_app()` now runs the full provider lifecycle
(`register → boot → mount_to_app`) and returns a ready-to-serve app. New
capabilities, all optional and backward compatible:

- `database_url=` (defaults to `sqlite+aiosqlite:///admin.db`) — a fresh
  container + `DatabaseProvider` is created when none is supplied.
- `container=` — bring your own pre-populated DI container (custom stores,
  existing database) and `create_app` mounts into it.
- `**kwargs` forwarded to `AdminProvider` (e.g. `contributors=[...]`).

`create_admin_provider()` remains the advanced path for embedding into an
existing application lifecycle.

---

## B6 (medium) — Icon/JS assets: `@latest` CDN on some pages, missing entirely on others

**Symptom.**
- Standalone pages loaded `https://unpkg.com/lucide@latest` — unpinned
  (silent breaking upgrades) and a hard runtime dependency on a third-party
  CDN (pages had no icons in any egress-restricted environment).
- The authenticated shell (`views/templates/base.html`) loaded **no icon
  library at all** — every `data-lucide` element in the header, sidebar,
  and toasts silently rendered as nothing.
- `AdminLayout` also pulled SortableJS from unpkg.

**Fix.** Vendored pinned builds into the admin's own static mount (already
the pattern for htmx/Alpine):

- `static/js/lucide.min.js` (lucide 0.544.0, npm tarball)
- `static/js/sortable.min.js` (sortablejs 1.15.0, npm tarball)

All three layouts (`StandaloneLayout`, `AdminLayout`,
`views/templates/base.html`) now reference the local files;
`base.html` additionally initializes `lucide.createIcons()` on
`DOMContentLoaded` and re-runs it on `htmx:afterSwap` so icons survive
partial page swaps. Zero `unpkg.com` references in served admin pages
(verified live). See doc 03 for the standing policy.

---

## B7 (medium UX/security) — Raw framework error chains leaked into user-facing URLs

**Symptom.** When the verification email could not be sent at login, the
user was redirected to
`?error=[LEX_ERR_ADMIN_010]+Verification+email+could+not+be+delivered:+[LEX_ERR_ADMIN_009]+…+https://docs.lexigram.dev/…`
— an internal error chain with error codes and doc links, URL-encoded into
the address bar.

**Fix.** The full chained error is still logged for operators
(`auth.login_verification_send_failed`); the query string now carries a
fixed, friendly message ("We couldn't send the verification email right
now. Please try again later or contact your administrator."). Verified live.

**Follow-up (roadmap R7).** Audit remaining `quote_plus(str(err))` sites and
route all user-facing error strings through a single humanizing helper.

---

## P1 (medium) — SetupMiddleware ran `COUNT(*)` on every admin request

**Symptom.** Every authenticated request paid a `SELECT COUNT(*) FROM
admin_users` round-trip forever, just to decide whether to redirect to the
setup wizard.

**Fix.** Once a positive count is observed the result is cached on the
middleware instance and the query stops. While the count is 0 the check
keeps running (so the wizard redirect still engages the moment it should).
Rationale: admin accounts are never bulk-deleted in normal operation; the
worst case of a stale positive is skipping a redirect until restart, while
the win is one fewer DB query on *every* request. Degrade-open behavior on
DB errors is unchanged. Verified live: exactly one `COUNT` after login,
none on subsequent requests.

**Tests.** `test_positive_count_is_cached_across_requests`,
`test_zero_count_keeps_checking_until_admin_exists`
(`tests/unit/middleware/test_setup_middleware.py`).

---

## B12 (critical, lexigram-sql, found during R15 verification) — `DatabaseService.execute` never committed DML on SQLite

**Symptom.** During R15's live verification, boot #1's schema-marker
`INSERT` logged `Query SUCCESS`, yet after a clean shutdown a fresh
connection saw no row. Reproduced with a standalone probe: any
`service.execute("INSERT/UPDATE/DELETE ...")` on the sqlite driver reported
success with `rowcount=0` and its effects vanished at connection close.

**Root cause.** `DatabaseService.execute`
(`packages/lexigram-sql/src/lexigram/sql/providers/_query_mixin.py`) routed
*all* SQL through the read path (`execute_query` → sqlite `fetchall`, no
commit). Under python-sqlite3's legacy isolation, DML opened an implicit
transaction that was silently rolled back on close; DDL (autocommit) always
persisted, which masked the bug. Historically data survived only because a
later query-builder write (e.g. the session `INSERT` at login) committed the
connection and flushed pending rows with it. Every admin store writing via
`db.execute` — audit log, login attempts, lockouts, settings — was exposed.
Postgres (asyncpg autocommit) was unaffected.

**Fix (in lexigram-sql, at the source).** `execute` now classifies the
statement: reads (`SELECT/PRAGMA/EXPLAIN/WITH/SHOW` prefix or `RETURNING`)
keep the read path; writes go through a new `_execute_write` →
`db_provider.execute` → `execute_modify`, which commits (and still respects
explicit `transaction()` blocks). Rowcounts are now real. Full design and
verification in [11-startup-cost.md](11-startup-cost.md) §6.

**Tests.** `packages/lexigram-sql/tests/unit/test_execute_commit_regression.py`
(8 tests: persistence across shutdown for INSERT/UPSERT/UPDATE/DELETE, real
rowcount, read-path preservation, failed-write semantics, explicit-transaction
rollback).

---

## Known issues deliberately deferred (tracked in doc 02)

| Item | Reason deferred |
| ---- | --------------- |
| Webhook contributor boot traceback (unregistered `WebhookSubscriptionStoreProtocol`) | Cosmetic at boot (caught + continues); proper fix is in the webhook extension's registration, not admin. Roadmap R8. |
| Setup page hx-boost/Alpine interplay | Needs a browser-level repro; no functional breakage found via HTTP. |
| Duplicate audit-log lines in console logging | Duplicate *log emission*, single row inserted; logging-pipeline issue. Roadmap R9. |
| JSON 403 body for browser navigation requests | Should render the styled error page for `Accept: text/html`. Roadmap R10. |
| `lexigram-ui` `HeadConfig.icon_library_url` default still points at unpkg (pinned 0.263.1) | Different package; changing the default could break consumers that don't serve the file. Policy + migration in doc 03. |
