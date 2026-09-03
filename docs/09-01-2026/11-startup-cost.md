# 11 — Startup Cost Audit: Schema-Version Marker (R15) (Full Plan)

**Date:** 2026-09-02 · **Status:** ✅ Done · **Branch:** `arena/01a05b98-lexigram`

## 1. Problem (measured)

Every boot — warm or cold — `AdminAuthSubProvider.boot()` resolves eight SQL
stores and runs their `ensure_schema()` **sequentially**:

| Store | Warm-boot DDL statements |
|---|---|
| `login_attempt_sql` | 3 (table + 2 indexes) |
| `lockout_sql` | 3 (table + 2 indexes) |
| `audit_log_sql` | 4 (table + 3 indexes) |
| `password_reset_token_sql` | 1 |
| `mfa_sql` | 1 |
| `roles_sql` (RBAC) | 1 |
| `email_verification_sql` | 2 (table + index) |
| `email_otp_sql` | 1 |

≈ **16 DDL statements per boot** (`CREATE TABLE/INDEX IF NOT EXISTS`, plus a
few existence probes), all round-trips in series, even when the schema is
fully current — confirmed by inspecting the playground's warm-boot query
log. On SQLite this is sub-millisecond noise; on a managed Postgres with
1–5 ms RTT it is 20–80 ms of serial latency per boot **per worker**, the
DDL takes locks it doesn't need, and it fills query logs with no-op DDL
(the same noise class R8 eliminated elsewhere).

The stores themselves are already safe: every one memoizes with
`self._initialized` and re-checks lazily on first use, so the *hot path*
costs nothing. The waste is exclusively the eager boot loop.

## 2. Design — fingerprint marker, fail-open

### 2.1 One marker row instead of sixteen statements

New table `admin_schema_markers(component PK, fingerprint, updated_at)`
managed by `AdminSchemaMarker`
(`src/lexigram/admin/auth/store/schema_marker.py`):

- **Boot, marker current** (the common case): `CREATE TABLE IF NOT EXISTS`
  for the marker itself + one `SELECT` → **2 statements**. The ensure loop
  is skipped and each resolved store is marked ready (`_initialized = True`,
  set only when the attribute already exists) so first requests don't pay
  the probes either.
- **Boot, marker missing/stale**: the loop runs exactly as before; only if
  **all eight** ensures succeed is the marker upserted (`ON CONFLICT …
  DO UPDATE`, same idiom `tenant_configs` already uses on SQLite ≥ 3.24 and
  Postgres). A partial failure leaves the marker absent so the next boot
  retries — fail-open on availability, per the standing guiding principle.
- **Marker machinery fails** (no DB, exotic backend): logged at debug,
  `skip = False`, boot behaves exactly as today. The marker can never make
  boot worse.

### 2.2 No manual version constant — a DDL fingerprint

Instead of an integer schema version that humans forget to bump, the marker
stores a **SHA-256 fingerprint of the DDL itself**:

- `compute_schema_fingerprint()` parses the eight store modules with `ast`,
  collects every string literal containing `CREATE TABLE` / `CREATE INDEX` /
  `CREATE UNIQUE INDEX` (f-string constant parts included), normalizes
  whitespace, sorts, and hashes. Pure source inspection — never runs at
  boot.
- The build-time constant `ADMIN_AUTH_SCHEMA_FINGERPRINT` is what boot
  compares against; a staleness-guard test recomputes the fingerprint from
  source and fails with the new value in the message whenever any store's
  DDL changes without updating the constant (same pattern as the
  design-token staleness guard). Changing DDL therefore *automatically*
  invalidates every deployment's marker on upgrade.

### 2.3 Trade-off, stated

With the marker current, stores are marked ready without probing, so a
manually dropped table no longer self-heals silently — queries fail loudly
instead. That is the correct posture for a schema someone mutated by hand;
the remedy is deleting the marker row (`DELETE FROM admin_schema_markers
WHERE component = 'admin.auth_stores'`) and restarting, and the skip log
(`admin_auth.schema_current`) says exactly that.

Out of scope, by choice: `tenant_configs` (1 statement at mount, separate
lifecycle in `_mount_settings_service`), `admin_users`/`admin_sessions`
(already lazy — first-request, memoized). The marker's `component` key
leaves room for them to adopt the same mechanism later.

## 3. Changes

| File | Change |
|---|---|
| `auth/store/schema_marker.py` | New: `AdminSchemaMarker`, `ADMIN_AUTH_SCHEMA_FINGERPRINT`, `compute_schema_fingerprint()`, `SCHEMA_SOURCE_MODULES` |
| `di/sub_providers/auth.py` | Boot loop consults the marker: skip + mark stores ready when current; upsert marker after a fully successful ensure pass |
| `tests/unit/test_schema_marker.py` | Fingerprint staleness guard; marker is_current/mark_current/upsert; error tolerance |
| `tests/unit/test_sub_providers/test_auth_sub.py` | Boot-loop matrix: current → skipped+marked ready; stale → ensures run + marker written; ensure failure → marker not written; marker error → ensures run |
| `packages/lexigram-sql/.../providers/_query_mixin.py` | **B12 fix** (§6): `execute` classifies reads vs writes; writes go through the committing `execute_modify` path |
| `packages/lexigram-sql/tests/unit/test_execute_commit_regression.py` | New: 8-test commit/persistence regression suite |
| `packages/lexigram-sql/tests/integration/test_migrations.py`, `test_monitoring_slow_query.py` | Test hygiene: relative `sqlite:///test.db` → `tmp_path`-backed absolute paths (§6.3) |

## 4. Verification

- Unit: marker behaviour + boot matrix + fingerprint guard.
- Live (playground): boot #1 after the change runs the ensures and writes
  the marker; boot #2 logs `admin_auth.schema_current`, shows **zero** store
  DDL in the query log, and login/CRUD still work end to end.
- Full suite + e2e green.

## 5. Implementation notes (post-verify)

- Admin unit suite: **5335 passed / 8 skipped, coverage 75.95%** (18 new
  tests: 13 in `test_schema_marker.py`, 5 boot-matrix cases in
  `test_auth_sub.py`). E2E: 72 passed / 2 skipped. lexigram-sql suite:
  **1403 passed / 48 skipped** (8 new regression tests — see §6).
- Live-verified (playground, three consecutive boots):
  - Boot A ran the full ensure pass (9 `CREATE TABLE`s in the query log)
    and upserted the marker (`admin_auth.schema_marker_written`); a
    **separate** sqlite3 connection immediately saw the committed row.
  - Boot B logged `admin_auth.schema_current` and its query log contained
    exactly **1** `CREATE TABLE` (the marker table itself) — zero store
    DDL. Login → dashboard → security audit page all 200.
  - Deleting the marker row and booting again (boot C) restored the full
    ensure pass and re-wrote the marker — the recovery path works.
- Boot DDL statements on the warm path: **~18 → 3** (marker CREATE+SELECT +
  tenant_configs), and the eight lazy first-request probes are skipped too.

## 6. B12 — discovered en route: `DatabaseService.execute` never committed DML on SQLite

Verifying §4 exposed a latent **data-loss bug in `lexigram-sql`**, not in
the admin app: boot #1's marker `INSERT` logged `Query SUCCESS`, yet after
a clean shutdown a fresh connection saw no row.

### 6.1 Root cause (probe-proven)

`DatabaseService.execute`
(`packages/lexigram-sql/src/lexigram/sql/providers/_query_mixin.py`) routed
**all** SQL — reads and writes alike — through `execute_query`, whose
sqlite driver path does `fetchall()` and **never commits**. Under
python-sqlite3's legacy isolation, DML opens an implicit transaction that
is silently **rolled back when the connection closes**. DDL is unaffected
(it runs autocommit), which is why tables always persisted while rows
vanished. Historically the damage was masked: any later query-builder
write on the same connection (e.g. the session `INSERT` at login) committed
and flushed the pending rows along with it. Every admin store that writes
via `db.execute` — audit log, login attempts, lockouts, settings — was
exposed. Postgres (asyncpg autocommit) was not affected.

A standalone probe (boot → `execute(INSERT)` → shutdown → fresh sqlite3
read) reproduced it deterministically: pre-fix `rowcount=0` and no row
after shutdown; post-fix `rowcount=1` and the row persists.

### 6.2 Fix (at the source, in lexigram-sql)

`execute` now classifies the statement:

- **Reads** (`SELECT/PRAGMA/EXPLAIN/WITH/SHOW` prefix, or any statement
  with `RETURNING`) → `execute_query`, unchanged.
- **Writes** → new `_execute_write`, which mirrors the read path's
  pipeline/metrics/error handling but executes via `db_provider.execute`
  (crud dispatcher → `execute_modify`), which **commits** unless inside an
  explicit `transaction()` block. Rowcounts are now real; failures still
  convert to a failed `QueryResult`.

### 6.3 Regression coverage

`packages/lexigram-sql/tests/unit/test_execute_commit_regression.py`
(8 tests): INSERT/UPSERT/UPDATE/DELETE survive service shutdown, real
rowcount, SELECT and CTE-SELECT stay on the read path, failed write →
failed result, explicit-transaction rollback still respected.

Fixing this also surfaced two pre-existing test-hygiene bugs the old
no-commit behaviour had been hiding: `tests/integration/test_migrations.py`
and `tests/integration/test_monitoring_slow_query.py` used **relative**
`sqlite:///test.db` connection strings, which now materialize a stray
`test.db` at the package root mid-run and tripped
`test_package_structure_p0::test_fixture_artifacts_are_canonicalized`
(order-dependent: only in full-suite runs, cleaned up by a session-end
fixture before anyone could see it). Both now use `tmp_path`-backed
absolute paths.
