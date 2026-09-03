# 48 — Settings panel navigation context (R52)

**Date:** 2026-09-03 · **Status:** shipped · **Roadmap:** doc 32
§2.3 / doc 46 follow-up · **Branch:** `arena/01a05b98-lexigram`

## 1. Problem

R50 made contributor-owned settings panels discoverable from the
Configuration Center, but the interaction still behaves like a dead-end:

- panel links target the shell's entire `#main-content`, so clicking System
  Info removes the Configuration Center's secondary sidebar instead of
  changing only its content column;
- a direct refresh or copied link to a panel receives the normal admin shell,
  but has no contextual "Back to Settings" action; operators must rely on
  browser history or the top-level user menu;
- because the sidebar is not re-rendered for an in-layout panel swap, the
  selected panel cannot receive active styling or `aria-current` state after
  navigation.

This is a UX regression in the new R50 navigation path, not a reason to
merge the contributor and ConfigRegistry catalogs or to weaken panel
permission filtering.

## 2. Design

### 2.1 Give the Configuration Center a stable content target

`ConfigLayout` will assign `id="settings-content"` to its main content
column (including the empty state). Contributor `PanelLink`s will keep the
same `href`, `hx-get`, push-url, accessibility, and navigation attributes but
will target `#settings-content`. Spec links remain on `#main-content` because
their response intentionally re-renders the complete settings layout so the
active spec/category state and form are server-authoritative. A panel fetch
therefore swaps only the right column and leaves the settings sidebar in
place.

### 2.2 Make standalone panel pages recoverable

The host-side structured page renderer will accept an optional contextual
`back_url` and render a compact, accessible "Back to Settings" link. The
route integrator supplies the mount-aware `/settings` URL only to settings
panel wrappers (class and instance handlers), never to ordinary management
pages. The link uses the existing HTMX navigation contract and targets
`#main-content`, which lets the Settings controller return its normal
fragment when leaving a standalone panel. When a panel was fetched into the
stable `#settings-content` target, the wrapper omits the redundant back link;
the visible sidebar is already the correct return path.

No contributor changes to `PageContent` are required. The panel handler still
returns only structured content, and the host owns all navigation markup.

### 2.3 Keep active state truthful after an in-place swap

Panel links will carry a narrow `data-settings-panel-nav` marker. The
already-global shell navigation script will synchronize only those links on
HTMX history pushes and browser `popstate`: compare URL pathnames, toggle the
existing active/inactive utility classes, and set/remove `aria-current="page"`.
This is delegated from the shell so it survives content swaps; it does not
make panel data or permissions client-controlled. Initial and history-restored
states are synchronized best-effort from `location.pathname`.

### 2.4 Fail-safe and compatibility rules

- Default `/admin` and custom-prefix URLs continue to use the R51
  mount-normalization boundary.
- Ordinary structured management pages keep byte-compatible rendering when no
  `back_url` is supplied.
- If the optional navigation script is unavailable, links still work as
  ordinary HTMX links and the server-rendered direct-page back link remains
  available.
- No panel is exposed without the existing assembler permission filter.

### 2.5 Out of scope

- Changing contributor route ownership, panel permissions, or the canonical
  `/admin` URLs.
- Adding a second panel-specific API or changing the shared `PageContent`
  contract.
- Re-rendering the entire shell for an in-place panel navigation.

## 3. Implementation order

1. Add the stable `settings-content` target and panel-specific HTMX target /
   marker to `ConfigLayout`, with layout markup regressions.
2. Add optional `back_url` support to `render_page_content`, thread a
   mount-aware settings URL through both structured panel wrappers, and cover
   standalone versus in-layout requests.
3. Add delegated active-state synchronization to the global shell navigation
   script and contract tests for the marker/class behavior.
4. Run the settings/dashboard/UI/controller suites, Ruff, and mypy; live-test
   Settings → System Info in-place, browser URL push, direct panel refresh, and
   the Back to Settings path.
5. Fill §4, append this round to the docs index, commit, and push to
   `arena/01a05b98-lexigram` (do not merge PR #26).

## 4. Verification

- **Unit (2026-09-03).** Settings/sidebar, structured-page renderer/shell,
  route-integrator, and shell-navigation contract tests: **45 passed**;
  the new browser navigation tests are collected and skip cleanly when the
  optional browser binary is unavailable. The full admin unit suite is
  **5809 passed, 7 skipped**. Ruff passed for all touched Python files;
  mypy passed for the four touched source modules. The generated navigation
  script also passes `node --check`, and `git diff --check` is clean.
- **Live (playground, root@playground.dev).** After the playground restart,
  `GET /admin/settings` renders one stable `id="settings-content"` region,
  one System Info panel link targeting `#settings-content`, and the shell's
  delegated history synchronizer. The panel endpoint with
  `HX-Request: true` and `HX-Target: settings-content` returns HTTP **200**,
  a **2,424-byte** fragment with no `<html>` wrapper and no redundant Back
  to Settings link; this is the response that preserves the sidebar during
  the in-place swap. A direct `GET /admin/system/info` returns HTTP **200**
  with the full shell and a contextual Back to Settings link. Returning via
  the link with `HX-Target: main-content` returns the settings fragment with
  the stable content region, confirming the recovery path.


