# 33 — Security headers: TTL re-resolution instead of once-per-process caching (R37)

## 1. Problem

`SecurityHeadersMiddleware` reads the four `admin.security.*` keys
(`csp`, `hsts_max_age`, `frame_options`, `csp_report_only`) from the
settings store **once per process** and caches the resolved
`AdminSecurityHeaders` service forever (`_resolved`).

Consequence, observed live during R36 verification: saving a change in
the Security settings panel (e.g. flipping the new "CSP Report-Only
Candidate" field to `off`) has **no effect on response headers until
the server is restarted**. The settings panel silently lies — the CSP
tab (which reads settings uncached) flips immediately while the actual
headers keep the stale policy. For a professional-grade admin tool the
control loop must close without a restart, and doc 32 §4 had to
document the restart requirement as a wart.

## 2. Design

### 2.1 TTL-based re-resolution (chosen)

Add a `settings_ttl` parameter (default **30.0 seconds**) to
`SecurityHeadersMiddleware`:

- `_resolve_headers` re-reads the store when the cached resolution is
  older than the TTL (`time.monotonic()` based; immune to wall-clock
  jumps). Within the window, requests reuse the cached service exactly
  as before — 4 store reads per window per worker (SQLite-backed,
  negligible).
- `settings_ttl <= 0` restores the legacy resolve-once behaviour for
  deployments that want zero steady-state reads.
- **Stale-over-defaults on refresh errors:** if a periodic re-read
  fails (`RuntimeError`/`ValueError`/`TypeError`), keep serving the
  previously resolved service instead of silently downgrading to
  compile-time defaults mid-flight. Only the *first* resolution falls
  back to defaults on error (unchanged from today). The retry
  timestamp is still advanced so a flapping store is not hammered on
  every request.
- New `invalidate()` method clears the cache so future wiring (or
  tests) can force an immediate re-read after a settings save; the
  save-path plumbing itself stays out of scope (see §2.3).

No wiring change needed: `bundle_provider` passes kwargs only for
`settings_store`/`report_endpoint`, so the new default applies
automatically.

### 2.2 Alternative rejected: save-path invalidation hook

Having the settings controller call `invalidate()` on the middleware
instance would give instant propagation, but the middleware stack is
built as `(cls, kwargs)` pairs and instantiated at wrap time — the
instance is not reachable from the save path without new registry
plumbing, and in-process invalidation does nothing for multi-worker
deployments anyway. TTL is worker-safe, self-healing, and bounded at
30 s of staleness; `invalidate()` is still exposed so an explicit hook
can be layered on later without redesign.

### 2.3 Out of scope

- Wiring `invalidate()` into the settings save path (needs a
  middleware-instance registry; TTL already bounds staleness).
- Per-request resolution (4 store reads per request is waste).
- Any change to header semantics — resolved values, merge behaviour,
  and the raw-header preservation in `send_with_headers` are untouched.

## 3. Implementation order

1. `middleware/security_headers.py` — add `settings_ttl`, monotonic
   timestamp, refresh + stale-on-error logic, `invalidate()`; update
   class docstring (drop "once per process").
2. Tests (`test_security_headers_settings.py`): rename the
   cached-once test to reflect the TTL window contract; add TTL expiry
   re-reads and picks up changed values; refresh-error keeps last-good
   service (not defaults); `invalidate()` forces re-read;
   `settings_ttl=0` never re-reads.
3. Live verify (playground, default 30 s TTL): save `off` in the
   panel, confirm the `Content-Security-Policy-Report-Only` header
   disappears within ~30 s **without restarting**; restore the empty
   default and confirm it returns.
4. Update this doc §4 + README row; commit + push (no merge).

## 4. Verification

**Automated** — `test_security_headers_settings.py` grows a
`TestSecurityHeadersTtl` class (5 tests): TTL expiry re-reads the four
keys and picks up a changed `frame_options` (8 store reads total, new
service instance); the R34/R36 report-only kill-switch applies after
expiry without a restart; a refresh error keeps the last-good service
(same instance, no downgrade to compile-time defaults) *and* advances
the retry timestamp (exactly 1 failed read, the immediately following
request does not hammer the store); `invalidate()` forces an immediate
re-read; `settings_ttl=0` never re-reads even with a lapsed timestamp
(legacy resolve-once behaviour, still 4 reads). The pre-existing
cached-once test is renamed `test_resolution_is_cached_within_ttl`
(same 4-read assertion — two immediate calls share one window). All
other overrides/error/default tests unchanged. Full unit suite:
**5633 passed / 7 skipped, coverage 77.12%**.

**Live (playground, default 30 s TTL, single process — no restarts at
any point):**

1. T0: `Content-Security-Policy-Report-Only` present on `/admin/`.
2. Saved `csp_report_only=off` via the settings panel; an immediate
   request still carried the header (within the TTL window, as
   designed).
3. T+31 s: header **absent** — the middleware re-read the store and
   rebuilt the service on its own.
4. Restored the empty default; T+31 s: header **present** again.

Doc 32 §4's "after a restart (the middleware resolves headers once per
process)" caveat is now obsolete for deployments on this revision —
security header changes converge within one TTL window per worker.

No wiring changes were needed: `bundle_provider` does not pass
`settings_ttl`, so the 30 s default applies everywhere the middleware
is constructed with a store.
