# 10 — Security Headers: Wire the Orphaned Middleware (Full Plan)

**Date:** 2026-09-02 · **Status:** ✅ Done · **Branch:** `arena/01a05b98-lexigram`

## 1. Problem

`src/lexigram/admin/middleware/security_headers.py` contains a complete,
tested implementation of OWASP-recommended HTTP security headers:

- `AdminSecurityHeaders` — a `SecurityHeadersProtocol` service that merges
  `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`,
  `Referrer-Policy`, `Permissions-Policy`, and `Content-Security-Policy`
  into a response header mapping via `setdefault` (route overrides win).
- `SecurityHeadersMiddleware` — an ASGI wrapper that applies the service to
  every HTTP response, with optional runtime overrides read once per process
  from a settings store (`admin.security.csp`, `admin.security.hsts_max_age`).

The class is registered in the DI container
(`di/sub_providers/auth_registrations.py`) and the settings panel already
ships a **Security Headers** page (`settings/panel/security_spec.py` →
`SecuritySettings` model), **but the middleware was never added to the wired
admin middleware chain** in `BundleProvider._mount_middleware`. The result:
no admin response carries any security header today. This was flagged as a
follow-up during the initial codebase audit (doc 01).

### Latent defects found while wiring (fixed here)

1. **Duplicate-header collapse.** The middleware rebuilt the ASGI header list
   from a `dict`, which collapses repeated header names. A response carrying
   multiple `Set-Cookie` headers (e.g. logout flows that delete one cookie
   and set another) would silently lose all but one cookie the moment the
   middleware was wired. Fix: keep the original raw header list verbatim and
   *append* only the missing security headers.
2. **Case-sensitive merge.** `dict.setdefault("Content-Security-Policy", …)`
   does not see a route-set `content-security-policy` (ASGI header names are
   case-insensitive), so wiring could emit duplicate/conflicting headers.
   Fix: the middleware compares names case-insensitively when deciding which
   headers to append.
3. **No frame-embedding override.** `X-Frame-Options: DENY` was hard-coded.
   Deployments that intentionally embed the admin (reverse-proxy preview
   panes, internal portals) had no escape hatch short of replacing the
   service. Fix: a `frame_options` knob on `AdminSecurityHeaders`, a matching
   `SecuritySettings.frame_options` field (surfaced automatically on the
   settings page), and an `admin.security.frame_options` runtime override.
   An empty value omits the header; the CSP `frame-ancestors` directive can
   then govern embedding on modern browsers.

## 2. Design

### 2.1 Placement — outermost of the admin stack

`core/routing.py` applies `middleware_stack` in reverse via
`add_middleware`, so **index 0 = outermost** (only `SessionMiddleware`,
added afterwards, wraps it). The security-headers middleware is inserted at
index 0 **at the end of `_mount_middleware`**, guaranteeing headers on every
admin response, including:

- Setup/CSRF/auth-guard short-circuit redirects and 403s,
- error pages rendered by `AdminErrorMiddleware`,
- tenant-middleware rejections (tenant also `insert(0)`s, but earlier, so it
  ends up inside security headers).

Because `SessionMiddleware` appends its `Set-Cookie` *outside* this layer,
and the middleware now preserves raw headers verbatim, cookies are never
affected.

### 2.2 Settings store

`_mount_settings_service` runs before `_mount_middleware`, so
`ctx.settings_service` is available. Wiring builds a
`TenantConfigStore(ctx.settings_service)` (the same adapter the settings
panel uses) and hands it to the middleware. The store is optional: without
it the middleware serves compile-time defaults (`DEFAULT_CSP`, HSTS 2 years,
`X-Frame-Options: DENY`). Overrides are read once per process on first
request and cached; read errors log `admin.security_headers.settings_error`
and fall back to defaults.

Runtime keys (editable on the **Security Headers** settings page):

| Key | Default | Meaning |
|---|---|---|
| `admin.security.csp` | `DEFAULT_CSP` | Full CSP header value |
| `admin.security.hsts_max_age` | `63072000` | HSTS max-age seconds |
| `admin.security.frame_options` | `DENY` | `X-Frame-Options`; empty ⇒ omit |

> Note: because values are cached once per process, settings changes take
> effect on the next restart — same trade-off the middleware already
> documented, kept deliberately to avoid a settings read per request.

### 2.3 CSP compatibility

`DEFAULT_CSP` keeps `'unsafe-inline'` for `script-src`/`style-src`, so the
current inline shell scripts, htmx attributes, and inline style attributes
keep working unchanged. Tightening the CSP (nonce/hash-based) is R18's job,
paired with the design-token consolidation.

### 2.4 Merge semantics

`AdminSecurityHeaders.apply()` remains `setdefault`-based (protocol
unchanged). The ASGI wrapper now:

1. takes the raw `(name, value)` byte pairs untouched,
2. builds a lowercase name set,
3. appends only security headers whose lowercase name is absent,
4. encodes appended values as latin-1 (HTTP header charset).

Route-level overrides therefore win regardless of case, duplicates survive,
and body messages pass through untouched (SSE streaming unaffected — only
`http.response.start` is inspected).

## 3. Changes

| File | Change |
|---|---|
| `middleware/security_headers.py` | `frame_options` knob (empty ⇒ omit header); append-only, case-insensitive, duplicate-preserving ASGI merge; `admin.security.frame_options` override |
| `settings/panel/models.py` | `SecuritySettings.frame_options` field (settings page picks it up automatically) |
| `di/bundle_provider.py` | Wire `SecurityHeadersMiddleware` at stack index 0 with a best-effort `TenantConfigStore`; logs `admin.security_headers_middleware_wired` / `_skipped` |
| `tests/unit/test_security_headers_middleware.py` | New cases: duplicate `Set-Cookie` preserved, case-insensitive override, frame_options omission |
| `tests/unit/middleware/test_security_headers_settings.py` | frame_options override + empty-string omission via store |
| `tests/unit/test_bundle_provider.py` | Wiring test: middleware present at index 0 with a settings store |

## 4. Verification

- Unit: middleware behaviour matrix + wiring presence at index 0.
- Live (playground): `curl -I` on `/admin/login`, an authenticated HTMX
  response, a 403/redirect short-circuit, and a static asset — all must
  carry the six headers; SSE endpoint must still stream.
- Full suite + e2e must stay green.

## 5. Implementation notes (post-verify)

- Full unit suite: **5317 passed / 8 skipped, coverage 75.90%** (12 new
  tests). E2E: 72 passed / 2 skipped.
- Live-verified on the playground: all six headers present on the login
  page, the unauthenticated 307 redirect, the authenticated dashboard, an
  HTMX partial, a 404, and vendored static assets. The login response's
  duplicate `set-cookie` pair survived verbatim — proof the collapse fix
  holds on real traffic.
- End-to-end settings override verified through the UI: saved
  `frame_options = ""` on the Security Headers settings page (audit-logged
  `DENY → ""`), restarted, confirmed `X-Frame-Options` absent while the
  other five headers stayed; restored `DENY` and confirmed it returned.
- SSE note: the playground's `_sse/widgets` route is skipped there (no
  `ReactiveSseBridgeProtocol`), so streaming was not live-testable; by
  construction the wrapper only touches `http.response.start` and the
  pass-through unit test covers body/stream messages.
