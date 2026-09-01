# 12 — Request-Scoped Session→User Cache (R16) (Full Plan)

**Date:** 2026-09-02 · **Status:** ✅ Done · **Branch:** `arena/01a05b98-lexigram`

## 1. Problem (measured)

Every authenticated admin request pays **two sequential DB round-trips**
before the handler runs, in `AdminAuthMiddleware._load_user`:

1. `session_service.get_session(session_id)` → `SELECT` on
   `admin_sessions` (+ TTL checks),
2. `user_store.get_by_id(admin_id)` → `SELECT` on `admin_users`.

HTMX-heavy pages fire bursts of requests (page + widgets + nav push +
polling), so a single dashboard render can pay this pair 4–6 times within a
second or two. On SQLite it is noise; on a managed Postgres with 1–5 ms RTT
it is 2–10 ms of serial latency added to *every* request, plus query-log
noise (the same class of waste P1 removed for the setup `COUNT(*)` and R15
removed for boot DDL).

## 2. Design — short-TTL in-process cache, revocation-invalidated

### 2.1 The cache

New `SessionUserCache`
(`src/lexigram/admin/auth/services/session_user_cache.py`):

- Maps `session_id → (user, user_id, expires_at_monotonic)`.
- **Short TTL, default 5 s**, configurable via
  `admin.auth.session_cache_ttl` (`ge=0`; **0 disables** the cache
  entirely — `get` always misses, `put` is a no-op).
- **Bounded size** (default 512 entries): oldest entry evicted on
  overflow — the cache can never grow without bound, even under a
  session-flooding attempt.
- Time source is `time.monotonic` (injectable for tests); no wall-clock
  skew sensitivity.
- Pure in-process dict operations on the event loop — no locks needed, no
  I/O, can never raise in practice.

### 2.2 Read path (middleware)

`AdminAuthMiddleware` accepts an optional `session_cache`:

- Session-service path only (the canonical path). After reading
  `session_id` from the signed cookie: cache **hit** → return the cached
  user, **zero queries**. Miss → run the exact two-query flow as today,
  then `put(session_id, user)`.
- Failure paths (session expired/revoked/user inactive) invalidate the
  cache entry before returning guest — a dead session can never be
  re-served from cache.
- Guests / misses are **never cached** (no negative caching: a freshly
  created session must work on the very next request).
- The legacy fallback path (no session service) is not cached — it is
  compatibility-only.

### 2.3 Invalidation (the security story)

All revocation flows in the codebase funnel through exactly two methods on
`AdminSessionService` — `revoke_session` (logout, Security Center remote
revoke, expiry-triggered revocations inside `get_session`) and
`revoke_all_user_sessions` (password change, administrative teardown).
Both now invalidate the cache (`invalidate(session_id)` /
`invalidate_user(user_id)`), so **same-process revocation takes effect
immediately** — the TTL only bounds staleness for:

- **Multi-worker deployments**: a revoke handled by worker A leaves worker
  B's cache entry alive for ≤ TTL (≤ 5 s by default). This is the standard
  in-process-cache trade-off; operators who cannot accept it set
  `session_cache_ttl: 0`.
- **Role/profile edits**: a changed user record is re-read after ≤ TTL.

Absolute/idle session-TTL enforcement precision is likewise reduced by at
most the cache TTL (5 s against a 1 h idle window — negligible, and
strictly bounded).

### 2.4 Wiring

- `auth_registrations.py` builds one `SessionUserCache` from
  `admin.auth.session_cache_ttl`, registers the **instance** as a
  singleton, and hands it to the configured `AdminSessionService` (for
  invalidation).
- `bundle_provider._mount_middleware` resolves it best-effort (cache is an
  optimization, never a boot blocker) and passes it to
  `AdminAuthMiddleware`.

## 3. Changes

| File | Change |
|---|---|
| `auth/services/session_user_cache.py` | New: `SessionUserCache` (TTL, size bound, invalidate by session/user, disabled at TTL 0) |
| `middleware/auth.py` | Optional `session_cache`: hit short-circuits `_load_user`; success populates; failure paths invalidate |
| `auth/services/session_service.py` | Optional `session_cache`; `revoke_session`/`revoke_all_user_sessions` invalidate |
| `config/auth.py` | `session_cache_ttl: int = 5` (`ge=0`, 0 disables) |
| `di/sub_providers/auth_registrations.py` | Build + register cache singleton; wire into session service |
| `di/bundle_provider.py` | Resolve cache best-effort, pass to `AdminAuthMiddleware` |
| `tests/unit/auth/test_session_user_cache.py` | New: cache semantics (TTL, eviction, invalidation, disable) |
| `tests/unit/test_session_user_cache_middleware.py` | New: middleware hit/miss/populate/invalidate + revocation immediacy |

## 4. Verification

- Unit: cache semantics; middleware hit skips both queries (call-count
  asserted); miss populates; revoked session invalidates and later
  requests miss; session-service revoke paths invalidate; TTL 0 disables.
- Live (playground): after login, burst-request the dashboard — query log
  shows the session+user SELECT pair once per TTL window instead of once
  per request; logout then reuse the old cookie → guest immediately (no
  cached resurrection).
- Full suite + e2e green.

## 5. Implementation notes (post-verify)

- Admin unit suite: **5357 passed / 8 skipped, coverage 76.04%** (22 new
  tests: 11 cache semantics in `test_session_user_cache.py`, 11
  middleware/service integration in
  `test_session_user_cache_middleware.py`). E2E: 72 passed / 2 skipped.
- Live-verified (playground):
  - Boot log shows `admin.session_user_cache_wired` (and R15's
    `admin_auth.schema_current` still active).
  - **Burst test:** login, then 5 × `GET /admin/` within the TTL window →
    query log shows exactly **1** `admin_sessions` SELECT and **1**
    `admin_users` SELECT (was 5 pairs before the change).
  - **Revocation immediacy:** warm a second session's cache entry, revoke
    it via Security Center, and re-request — all within ~0.6 s (≪ 5 s
    TTL): the revoked session was redirected to login immediately; the
    cache entry did not survive the revoke.
  - **Logout:** warm own entry → logout → next request is guest
    (redirect to login) immediately.
- Incidental live-verification note: the Security Center revoke POST
  requires the *fresh* `csrf_session_id` cookie set by the page GET —
  fetching the form without persisting cookies yields
  `csrf.token_signature_mismatch` → 403 (correct fail-closed behaviour,
  worth knowing when driving the API with curl).
