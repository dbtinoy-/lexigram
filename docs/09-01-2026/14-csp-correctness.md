# 14 — CSP Correctness & Hardening (R18 / B14) (Full Plan)

**Date:** 2026-09-02 · **Status:** 🚧 In progress · **Branch:** `arena/01a05b98-lexigram`

## 1. Findings

### 1.1 B14 (critical, functional): the enforced CSP breaks Alpine in real browsers

`DEFAULT_CSP` ships `script-src 'self' 'unsafe-inline'` — **without
`'unsafe-eval'`**. The vendored `alpine.min.js` is the **standard** Alpine
build: it compiles every directive expression through the `AsyncFunction`
constructor (verified in the vendored file:
`Object.getPrototypeOf(async function(){}).constructor`). CSP classifies
Function-constructor use as eval, so in any browser that enforces this
header **every Alpine expression throws `EvalError`** — sidebar toggles,
dropdowns, command palette, slide-overs, dark mode: all dead. htmx's
`hx-on-*` handlers are compiled with `new Function` and fail the same way.

This never showed up in verification because all previous checks were
curl-based (headers + static HTML); no real browser enforced the policy.
A Playwright confirmation was attempted but browser binaries cannot be
downloaded in this sandbox (CDN blocked) — the static evidence above and
Alpine's own documentation (the standard build explicitly requires
`unsafe-eval`; a separate restricted "CSP build" exists) are conclusive.

**Fix:** add `'unsafe-eval'` to `script-src`. This is not a loosening in
practice — the current value doesn't deliver the stricter policy, it
delivers a broken product. The real long-term tightening path is the
Alpine **CSP build** migration (below).

### 1.2 Additional hardening that costs nothing

Live-page audit (dashboard + list): zero external resources, all forms
post same-origin, no plugins, no `<base>` tag. So these directives can be
added with no behavioural impact:

* `object-src 'none'` — blocks plugin/embed vectors outright.
* `base-uri 'self'` — prevents `<base>`-tag hijacking of relative URLs.
* `form-action 'self'` — exfiltration guard: forms can only submit
  same-origin even if markup is injected.

### 1.3 Why `'unsafe-inline'` stays (for now)

Measured on the live dashboard/list pages: **11 inline `<script>` blocks**
(Alpine component registrations, flash templates, theme boot), **2
`<style>` blocks**, **26 inline `style=` attributes** (sticky column
offsets, dynamic widths), **4 `onclick=` attributes**. Dropping
`'unsafe-inline'` requires either a per-request nonce threaded through the
whole `el()` render pipeline (and htmx fragment swaps re-executing scripts
lose their nonce on clone — browsers hide nonce content post-parse), or
migrating to the Alpine CSP build plus externalizing every inline block.
That is a standalone project, not a flag flip. Documented as the follow-up
(“CSP v2”) with the prerequisite steps.

## 2. Changes

| File | Change |
|---|---|
| `settings/panel/models.py` | `DEFAULT_CSP`: add `'unsafe-eval'` to `script-src`; append `object-src 'none'; base-uri 'self'; form-action 'self'`; update the rationale comment |
| `tests/unit/settings/test_default_csp.py` | assert `'unsafe-eval'` in `script-src` (B14 regression — Alpine standard build), assert the three new directives |
| `docs/09-01-2026/14-csp-correctness.md` | this plan + CSP v2 roadmap |

`SecuritySettings.csp` defaults to `DEFAULT_CSP`, so the settings panel
and the middleware inherit the fix; operator overrides stored in
`tenant_configs` are untouched by design.

## 3. CSP v2 roadmap (out of scope here)

1. Swap `alpine.min.js` for the Alpine CSP build; convert all inline
   directive expressions to registered `Alpine.data` components (large:
   every `x-show="open"`-style expression must become a method/property
   reference).
2. Externalize the remaining inline `<script>`/`<style>` blocks into
   static assets; move per-page data into `<script type="application/json">`
   data islands (non-executable, CSP-exempt).
3. Replace inline `style=` attrs (sticky offsets, widths) with CSS custom
   properties set via Alpine `:style` bindings or classes.
4. Then drop `'unsafe-inline'` and `'unsafe-eval'` together.

## 4. Verification

- Updated CSP unit tests green; both middleware/settings suites green;
  full admin unit suite green.
- Live: `Content-Security-Policy` header contains the corrected
  `script-src` and the three new directives on authed + unauthed routes.

## 5. Implementation notes (post-verify)

**Status: ✅ Shipped.**

* `DEFAULT_CSP` corrected and hardened exactly as planned; the rationale
  comment in `models.py` now explains why `'unsafe-eval'` must not be
  removed before the CSP v2 migration.
* New regression tests: `test_script_src_allows_eval_for_standard_alpine_build`
  (also asserts eval stays scoped to `script-src`, never `default-src`)
  and `test_hardening_directives_present`.
* No other test or source pinned the old CSP string.

**Verification (all green):**

* CSP/middleware tests: 28 passed; full admin unit suite **5368 passed /
  8 skipped**, cov 76.04%; e2e **72 passed / 2 skipped**.
* Live (after restart): corrected header served on authed (`/admin/`),
  unauthed (`/admin/login`), and static-asset routes:
  `script-src 'self' 'unsafe-inline' 'unsafe-eval'` +
  `object-src 'none'; base-uri 'self'; form-action 'self'` present.
* Real-browser confirmation of the pre-fix breakage was not possible in
  this sandbox (Playwright browser CDN blocked); conclusive static
  evidence recorded in §1.1.

