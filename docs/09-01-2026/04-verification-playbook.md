# 04 — Verification Playbook

How the 2026-09-01 fixes were verified, and the repeatable procedure for
verifying any future change to lexigram-admin. Auth/authz changes require
**both** layers: unit tests *and* a live playground pass.

## 1. Unit suite (fast, always)

```bash
# from repo root
uv run pytest experimental/apps/lexigram-admin/tests/unit -q
```

- Baseline 2026-09-02: **5305 passed, 8 skipped**, coverage
  ≈ 75.9% (configured minimum 60%).
- The suite adds `--cov` flags from `pyproject.toml`; use `--no-cov` for
  quick single-file runs.
- New regression tests added this date:
  - `tests/e2e/test_first_run_scenario_e2e.py` — **the first-run scenario**
    (roadmap R5): real SQL stores via `create_app()`, full operator journey.
    Run it for any change touching auth/authz/middleware/bootstrap:
    `uv run pytest experimental/apps/lexigram-admin/tests/e2e/test_first_run_scenario_e2e.py --no-cov`
  - `tests/unit/middleware/test_super_admin_marking.py` (B1)
  - `tests/unit/middleware/test_setup_middleware.py` — caching tests (P1)
  - `tests/unit/auth/test_email_verification_store.py` — `mark_verified` (B3)
  - `tests/unit/auth/test_email_verification_service.py` — `mark_verified` (B3)
  - `tests/unit/ui/test_shell_sections.py` — `.view`/`.read`/superuser nav (B2)
  - `tests/unit/controllers/test_setup_claim_first_admin.py` — row_count
    fallback (B8)
  - `tests/unit/controllers/test_error_humanizer.py` — shared humanizer (R4)
  - `tests/unit/middleware/test_error_negotiation.py` — content-negotiated
    403/404/405/500 (R7)
  - `tests/unit/middleware/test_permission_scheme.py` — canonical permission
    scheme + legacy alias bridge (R6)
  - `packages/lexigram-sql/tests/unit/test_query_log_single_emission.py` —
    one query-log entry per statement (R9):
    `uv run pytest packages/lexigram-sql/tests/unit/test_query_log_single_emission.py --no-cov`
  - `tests/unit/settings/test_default_csp.py` — default CSP is fully
    first-party (doc 03)
  - `tests/unit/schema/test_text_area.py` — Trix vendored, no CDN (doc 03)
  - `tests/unit/test_admin_layout.py` — vendored assets, no CDN (B6)
  - `tests/unit/controllers/test_security_controller.py` — Security Center
    gate/revoke/unlock/CSRF (R12, doc 05)
  - `tests/unit/auth/test_session_fleet_listing.py` — fleet session listing
    store+service, LIMIT injection guard (R12)
  - `tests/unit/navigation/test_navigation_manager.py::TestSecurityMenuEntry`
    — superadmin-only Security menu entry, fail-closed (R12)
  - `tests/unit/auth/test_lockout_timestamp_coercion.py` — lockout
    timestamps coerced to aware datetimes; login-vs-locked-account 500 (B9)
  - `tests/unit/controllers/test_roles_controller.py` — Roles UI: gate,
    permission parsing, CRUD, held-role delete guard (R10, doc 06)
  - `tests/unit/controllers/test_users_controller.py` — Users UI: role
    options, last-superadmin demotion guard (fail-closed), audited
    assignment (R10, doc 06)
  - `tests/unit/controllers/test_route_collection.py` — path parameters
    forwarded to decorated controller routes (B11, doc 06)
  - `tests/unit/rbac/test_role_service.py` — role CRUD audit rows carry
    `actor_id` attribution (R10)
  - `tests/unit/navigation/test_navigation_manager.py::TestAccessControlMenuEntries`
    — superadmin-only Users/Roles menu entries, fail-closed (R10)
  - `tests/unit/services/test_console_mailer.py` — protocol conformance,
    receipts, health (R11, doc 07)
  - `tests/unit/services/test_notification_diagnostics.py` — mailer
    introspection + `notify_test_email` Ok/Err paths (R11)
  - `tests/unit/controllers/test_email_controller.py` — Email delivery
    page: gate, status card states, CSRF, self-only test send (R11)
  - `tests/unit/di/test_mailer_fallback.py` — console fallback registers
    in debug only and never overrides a bound backend (R11)
  - `tests/unit/services/test_saved_views.py` — query sanitization
    (whitelist, legacy aliases, volatile-param drops), name/resource
    validation, upsert, caps, corrupt-payload tolerance (R13, doc 08)
  - `tests/unit/controllers/test_saved_views_controller.py` — auth guard
    (any signed-in admin), CSRF session-id chain (`csrf_session_id` OR
    `admin_user_id`), save/delete redirects (R13)
  - `tests/unit/resources/test_list_renderer_saved_views.py` — views bar
    visibility, escaping, default-aware active matching, never breaks the
    list page (R13)
  - `tests/unit/resources/test_bulk_outcome.py` — bulk outcome messages
    (legacy-identical happy path, partial/total failure, "and N more"
    caps, ASCII header safety incl. non-ASCII record ids) (R14, doc 09)
  - `tests/unit/resources/test_bulk_handler_outcomes.py` — per-row
    failure isolation, storage rejections/missing rows reported with
    reasons, purge-without-hook → 503, warning/error toasts with
    duration in HX-Trigger (R14)

## 2. Live playground (for anything touching auth, authz, middleware, layouts)

The playground (`experimental/apps/lexigram-admin/playground/`) is a
**committed** dev asset — only the SQLite files (`playground.db*`) are
gitignored. Since R8 (2026-09-01), a clean boot must produce **zero
tracebacks**: optional contributors whose dependencies aren't registered
log one-line `admin.contributor_disabled` / `webhook.admin_contributor_disabled`
INFO entries instead. A traceback at boot is a regression.

### Boot

```bash
rm -f experimental/apps/lexigram-admin/playground/playground.db*   # ALWAYS all three files (-wal/-shm too)
uv run python experimental/apps/lexigram-admin/playground/serve.py  # 0.0.0.0:8000, setup token: dev-setup-token
```

The playground boots the real lifecycle (`register → boot → mount_to_app`)
against SQLite with two demo resources (products, customers) and **default
security settings** — email verification enforcement is intentionally left
ON so the first-run path is exercised exactly as a fresh production install
would experience it.

### End-to-end smoke flow (curl)

```bash
J=/tmp/jar.txt; B=http://localhost:8000; rm -f $J

# Setup — expect 302 (success) and NOT "already complete"
curl -s -c $J $B/admin/setup -o /tmp/s.html
CSRF=$(grep -o 'name="csrf_token" value="[^"]*"' /tmp/s.html | sed 's/.*value="//;s/"//')
curl -s -b $J -c $J -X POST $B/admin/setup \
  -d "csrf_token=$CSRF" -d "setup_token=dev-setup-token" \
  -d "email=root@playground.dev" -d "name=Root Admin" \
  -d "password=<strong password>" -d "confirm_password=<same>" -D -

# Login — expect 302 → /admin/  (NOT /admin/verify-email)
curl -s -b $J -c $J $B/admin/login -o /tmp/l.html
CSRF=$(grep -o 'name="csrf_token" value="[^"]*"' /tmp/l.html | sed 's/.*value="//;s/"//')
curl -s -b $J -c $J -X POST $B/admin/login \
  -d "csrf_token=$CSRF" -d "email=root@playground.dev" -d "password=<pw>" -D -

# Authenticated surface
curl -s -b $J $B/admin/ -o /tmp/d.html -w "dash %{http_code}\n"          # 200
curl -s -b $J -o /dev/null -w "products %{http_code}\n" $B/admin/products   # 200 (B1)
grep -c 'href="/admin/products"' /tmp/d.html                              # ≥1 sidebar link (B1/B2)
grep -c "<title>" /tmp/d.html                                             # exactly 1 (B4)
grep -o '<script src="[^"]*"' /tmp/d.html                                 # only /admin/static/... (B6)
grep -c "unpkg" /tmp/d.html                                               # 0 (B6)
grep -c "LEX_ERR" /tmp/d.html                                             # 0 (B7)
```

### Database spot-checks

```bash
sqlite3 experimental/apps/lexigram-admin/playground/playground.db \
  "SELECT user_id, email_verified_at FROM admin_email_verifications;"
# first admin must have email_verified_at set at creation time (B3)
```

### Log spot-checks (server stdout)

- `setup.first_admin_email_auto_verified` after setup POST (B3).
- Audit row `email_verified` with `{"reason": "out_of_band_setup"}` (B3).
- Exactly **one** `SELECT COUNT(*) FROM admin_users` after the first
  post-setup request; none on subsequent requests (P1).
- No `[LEX_ERR_*]` text in any `Location:` response header (B7).

## 3. Environment notes (sandbox/CI quirks)

- Passwords containing the email local-part are rejected by policy — pick
  unrelated strong passwords for test accounts.
- Delete SQLite sidecars together (`playground.db*`); removing only the db
  file with a live `-wal` causes `disk I/O error` on next boot.
- `unpkg.com`/`jsdelivr.net` may be blocked in CI sandboxes;
  `registry.npmjs.org` is the reliable source for asset tarballs (doc 03) —
  and since B6, the admin UI no longer needs any of them at runtime.
- Known cosmetic boot noise: webhook-contributor traceback for
  `WebhookSubscriptionStoreProtocol` (roadmap R8) — boot continues normally.
