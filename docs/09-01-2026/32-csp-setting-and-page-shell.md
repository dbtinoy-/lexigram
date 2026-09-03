# 32 — CSP Report-Only Setting + Structured-Page Shell Fix (R36)

**Date:** 2026-09-02 (docs series 09-01-2026)
**Branch:** `arena/01a05b98-lexigram` · follows R34 (doc 30) / R35 (doc 31)

## 1. Problems (both found in the same recon sweep)

### 1.1 The R34 report-only control has no UI

R34 introduced the settings key `admin.security.csp_report_only`
(middleware: absent/empty → strict candidate ON, `off`-values →
suppressed, other string → custom policy) and R35's CSP tab *displays*
the resolved status — but the **Security Headers settings panel**
(`/admin/settings/admin.security`, `SecuritySettings` model) only exposes
`csp` / `hsts_max_age` / `frame_options`. Operators cannot turn
report-only monitoring off or supply a custom candidate without writing
`tenant_configs` rows by hand. The control loop
(settings panel → middleware → CSP tab) is missing its first link.

### 1.2 Instance-based contributor pages render without the admin shell

`GET /admin/system/info` (the core contributor's System Info settings
panel) returns a **bare HTML fragment** — no `<html>`, no CSS, no nav —
on direct navigation. Root cause in `dashboard/page_handlers.py` +
`dashboard/route_integrator.py`:

- Class handlers → `AdminPageHandler`, which wraps non-HTMX responses in
  the admin shell (`_wrap_in_shell`) and strips inline headers on
  cluster pages (`_apply_cluster_header`).
- **Instance/function handlers → `StructuredPageHandler`, which renders
  `PageContent` and sends it as-is — always, even for full-page browser
  navigations.**

Every contributor management page or settings panel registered with a
pre-built handler instance ships unstyled. The contract
(`PageContent` in, framework owns chrome) clearly intends both wrappers
to behave identically at the response layer.

## 2. Design

### 2.1 `SecuritySettings.csp_report_only` field

Add a `str` field to the model (panel specs auto-derive their forms from
the Pydantic model, so `/admin/settings/admin.security` picks it up with
no other change; persistence lands on exactly the key the middleware
reads):

- default `""` — semantics identical to *absent* per
  `resolve_report_only_csp("")` → strict candidate ON, so a fresh save
  of the panel with untouched defaults does not change behaviour;
- title "CSP Report-Only Candidate", description spelling out the three
  states (empty → strict candidate on, `off` → disabled, any other
  value → custom policy) and pointing at the Security → CSP tab.

No middleware change needed: R34 already reads the key.

### 2.2 Shared shell-wrapping for `StructuredPageHandler`

Extract the two response-layer behaviours of `AdminPageHandler` into
module-level helpers (bodies unchanged):

- `apply_cluster_header(request, response)` ← `_apply_cluster_header`;
- `wrap_page_in_shell(request, response, *, title, container=None)` ←
  `_wrap_in_shell`, with `title` a parameter (the class variant derives
  it from the page class name; the structured variant uses
  `PageContent.title`) and `container` optional — every use of it is
  already inside best-effort try/except with request-state fallbacks,
  so `None` degrades to defaults.

`AdminPageHandler` delegates to the helpers (no behaviour change).
`StructuredPageHandler.__call__` gains the same response ladder:
render `PageContent` → `apply_cluster_header` → `wrap_page_in_shell`
unless `wants_fragment(request)` (HTMX requests keep receiving the bare
fragment, which is the point of fragments).

### 2.3 Out of scope

Surfacing the System Info panel in the settings sidebar (it is
registered as a *contributor* settings panel while the settings page
lists only ConfigRegistry specs — unifying those catalogs is a separate
design question), and any change to `render_page_content` itself.

## 3. Implementation order

1. `settings/panel/models.py` — add the field.
2. `dashboard/page_handlers.py` — extract helpers, wire both wrappers.
3. Tests: field present with `""` default + panel-spec derivation;
   structured handler wraps full-page navigations in the shell, keeps
   fragments bare for HTMX, and preserves the PageContent title;
   AdminPageHandler behaviour unchanged (existing suites).
4. Live verify: settings panel shows the new field and saving `off`
   suppresses the Report-Only header + flips the CSP tab badge; then
   `/admin/system/info` renders inside the shell while an `HX-Request`
   fetch still returns the fragment.

## 4. Verification

**Automated** — new `tests/unit/dashboard/test_structured_page_shell.py`
(8 tests): spec derivation includes `csp_report_only` alongside the
three R14 keys; empty default resolves to `STRICT_CSP` (R34 behaviour
preserved); `off` suppresses; custom string round-trips; structured
full-page navigations return a shell-wrapped document (`<html>`,
`<title>` from `PageContent.title`); an `HX-Target` fragment fetch
stays bare; contract-violation error pages are shell-wrapped too.
`test_specs.py::test_security_spec_nodes` updated for the fourth node.
Full unit suite: **5628 passed / 7 skipped, coverage 77.11%**.

Notes discovered while testing:

- `SecuritySettings` is a `DomainModel` (dataclass-backed, not plain
  Pydantic) — the panel derives nodes from `SecuritySpec.get_nodes()`,
  so the tests assert against the node catalog, not `model_fields`.
- `wants_fragment` keys off `HX-Target` (≠ `body`), not `HX-Request`;
  boosted navigations therefore correctly receive the full shell.

**Live (playground)** —

1. `/admin/settings/admin.security` renders the new "CSP Report-Only
   Candidate" field (auto-derived, no template change).
2. Saving `off` persists `admin_ui.admin.security.csp_report_only` =
   `"off"` — exactly the key `SecurityHeadersMiddleware` reads — and
   the CSP tab immediately flips to "Report-only monitoring is
   disabled (admin.security.csp_report_only)". After a restart (the
   middleware resolves headers once per process) the
   `Content-Security-Policy-Report-Only` header is absent.
3. Restoring the empty default flips the tab back to "On — strict
   default" and the header returns on a fresh process.
4. `/admin/system/info` now returns a full shell document (~100KB,
   `<title>System Info`, sidebar, breadcrumbs) instead of the bare
   2.4KB `space-y-6` fragment; an `HX-Request` + `HX-Target` fetch
   still returns the bare fragment (2424 bytes, no `<html>`).

Two robustness follow-ups landed during live verification:

- `wrap_page_in_shell` skips theme resolution when `container is
  None` instead of relying on the catch-all (no spurious tracebacks).
- `StructuredPageHandler` now accepts an optional `container`
  (threaded through both `route_integrator` call sites), so structured
  pages resolve real branding/theme instead of silently logging
  `admin.settings_service_resolve_failed` and falling back to
  defaults on every navigation.

