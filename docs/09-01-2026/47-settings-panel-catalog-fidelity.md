# 47 — Settings panel catalog fidelity: custom mounts and declared order (R51)

**Date:** 2026-09-03 · **Status:** shipped · **Roadmap:** doc 32
§2.3 / doc 46 follow-up · **Branch:** `arena/01a05b98-lexigram`

## 1. Problem

R50 made contributor-owned settings panels discoverable from the
Configuration Center, but a fresh bug-hunt of that path found two catalog
fidelity gaps:

1. `SettingsController._panel_links` copies each panel's canonical
   `route_path` directly into the sidebar. Contributors publish the historic
   `/admin/...` URL and the route integrator correctly remaps that route when
   the admin app is mounted at a custom prefix such as `/backoffice`. The
   sidebar did not perform the same remapping, so a custom-prefix operator
   could see a link that navigated to the wrong application path.
2. `SettingsPanelAssembler` namespaces panel definitions but does not copy
   the contributor-declared `order`. Every assembled panel therefore falls
   back to `SettingsPanelDefinition.order == 100`; the R50 controller sort is
   unable to honor contributor ordering (and only the title tie-break remains
   effective).

These are presentation/catalog bugs, not authorization bugs: permission
filtering must remain in the existing assembler, and route registration must
remain the source of truth for mounted paths.

## 2. Design

### 2.1 Normalize only at the request boundary

Keep contributor contracts and the assembled catalog canonical. The route
integrator already owns mount-relative registration, while the Settings page
owns request-specific presentation. `_panel_links` will pass each internal
panel URL through the shared `mount_admin_url` helper using
`admin_prefix_from_request(request)`. Default `/admin` URLs remain byte-for-
byte unchanged; `/admin/...` becomes `/backoffice/...` only for a
`/backoffice` request. The existing `PanelLink` remains a plain presentation
value and no handler or route metadata is leaked into the layout.

### 2.2 Preserve declaration metadata while namespacing

`SettingsPanelAssembler` will carry `panel.order` into its namespaced
`SettingsPanelDefinition`. No new protocol or schema is needed: `order` is
already part of the shared frozen contract and the controller already sorts
by `(order, title)`. Existing icon, category, permission, handler, and route
copying stays unchanged.

### 2.3 Fail-safe behavior

The URL normalization is deterministic and uses the same helper as other
admin navigation surfaces. If the optional dashboard catalog fails, the R50
spec-only fallback remains unchanged. Permission filtering is not duplicated
in the controller and no panel becomes visible merely because it is linked.

### 2.4 Out of scope

- Reworking contributor route registration or changing canonical contributor
  URLs.
- Persisting the Configuration Center secondary sidebar on a full standalone
  panel page; that is a separate UX round from catalog correctness.
- Active-state highlighting for a panel route outside the settings layout.

## 3. Implementation order

1. Add `order=panel.order` to `SettingsPanelAssembler` and a regression test
   proving the value survives namespacing.
2. Normalize panel link URLs in `SettingsController._panel_links` with the
   request's configured admin prefix; add default-prefix and custom-prefix
   tests while retaining the existing permission/user/degradation coverage.
3. Run settings/dashboard/controller tests, Ruff, and the touched-area type
   check; live-verify both the default playground link and a request-level
   custom-prefix mapping without changing the running deployment's canonical
   route.
4. Fill §4, append this round to the docs index, commit, and push to
   `arena/01a05b98-lexigram` (do not merge PR #26).

## 4. Verification

- **Unit (2026-09-03).** The new custom-prefix regression in
  `tests/unit/settings/test_settings_panel_links.py` proves canonical
  `/admin/system/info` becomes `/backoffice/system/info` at the request
  boundary while the default-prefix assertion remains unchanged. The
  settings assembler regression proves a declared `order=37` survives
  contributor namespacing. Targeted settings + dashboard tests: **15
  passed**; the touched settings/dashboard/controller sweep: **855
  passed**. Full admin unit suite: **5802 passed, 7 skipped**. Ruff passed
  on all touched Python files; mypy passed for the two touched source
  modules. `git diff --check` is clean.
- **Live (playground, root@playground.dev).** After restarting the
  playground and logging in, `GET /admin/settings` followed its normal
  redirect to `/admin/settings/admin.branding` with HTTP **200** and a
  single System → System Info sidebar link. The rendered link remains
  `href="/admin/system/info"` and `hx-get="/admin/system/info"` on the
  default mount, confirming the fix preserves existing deployments. The
  custom-prefix remap is covered at the controller request boundary so it
  can be exercised without changing the playground's canonical `/admin`
  mount; the mounted route itself remains owned by `RouteIntegrator`.
