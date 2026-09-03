# 56 — Sidebar information architecture and account placement (Full Plan)

**Date:** 2026-09-03 · **Status:** Implemented · **Branch:**
`arena/01a05b98-lexigram`

## 1. Problem

The current admin shell has two competing navigation models. Resources and
contributor links appear in the primary sidebar, but infrastructure cluster
links and superadmin destinations are hidden in the user dropdown. The
sidebar footer also owns the only visible account control, so the operator's
identity, account actions, and application navigation are mixed together.

This makes important destinations difficult to discover, creates avoidable
navigation duplication, and leaves the primary sidebar visually incomplete.
The existing navigation manager already knows the route registry, cluster
centers, superadmin state, configured prefix, and contributor groups. The fix
should use that information at request time rather than hard-coding a
playground-specific menu.

## 2. UX/DX goals

- Make the sidebar the canonical place for application destinations.
- Keep personal account actions in an account menu in the topbar, where users
  expect identity and sign-out controls.
- Surface the infrastructure cluster as a first-class sidebar destination and
  retain its contextual secondary navigation once opened.
- Surface superadmin-only Users, Roles, Security, and Email links in a clearly
  labeled Administration section, with the existing fail-closed gate.
- Keep resources grouped under a human-readable Workspace section instead of
  exposing an implementation label such as Default.
- Keep Settings discoverable as a persistent utility link in the sidebar
  footer, while retaining it in the user-menu API for backwards compatibility
  when consumers call that API directly.
- Preserve custom navigation contributions, custom mount prefixes, permission
  filtering, active-state semantics, and application-provided system links.
- Make the account control accessible, responsive, keyboard-operable, and
  visually consistent with the existing premium shell.

## 3. Proposed information architecture

Primary sidebar, in this order:

1. **Overview** — Dashboard and any existing core top-level actions such as
   Exports.
2. **Workspace** — application resources (the default resource group is
   labeled Workspace; configured groups keep their configured labels).
3. **Operations** — registered cluster centers such as Infrastructure. A
   cluster center owns the secondary navigation for its service areas.
4. **Security** — contributor security links when those contributors are
   enabled.
5. **Integrations** — webhook and other integration links when available.
6. **Search/Tools** — searchable utility destinations contributed by the
   deployment, including Plugins when the existing plugin landing route is
   exposed.
7. **Administration** — Users, Roles, Security, and Email for superadmins
   only.
8. **Sidebar utilities** — Settings and application-supplied system links at
   the bottom of the sidebar.

The topbar retains search/command-palette, notifications, theme, and the
current user's avatar/name. The account dropdown contains Profile and any
consumer-supplied personal menu entries, followed by Sign out. Navigation
links are not duplicated there in the rendered shell.

## 4. Implementation design

### 4.1 Navigation manager

- Add first-class cluster landing entries to the primary nav while keeping
  `build_secondary_nav()` and cluster URL namespacing unchanged. The landing
  entry is active for both the namespaced center path and legacy contributor
  paths during redirects/custom-prefix deployments.
- Build default Settings utility metadata from the request prefix and merge it
  with application-provided system menu items without duplicating matching
  labels or URLs.
- Add Plugins to a Tools group when the existing plugin destination is
  enabled, preserving the current shell's discoverability.
- Add a superadmin-only Administration group using the same `_is_super_admin`
  test as the existing user-menu entries. Avoid duplicate resources by URL.
- Apply a stable group-priority ordering after merging contributions while
  preserving the relative order of unknown/custom groups. This keeps the
  visual information architecture consistent without taking ordering control
  away from contributor items within their groups.
- Add an opt-out parameter for user-menu navigation entries. The existing
  default remains backwards-compatible for direct API callers, while the
  AdminShell renderer requests the personal-only menu to prevent duplicate
  sidebar destinations.

### 4.2 Sidebar and account placement

- Remove the UserBox from the sidebar footer; retain SystemBox for utility
  links and the collapse control.
- Render UserBox from TopBar when an authenticated user exists. Add a
  topbar-friendly variant that does not depend on `sidebarMini`, keeps the
  user name visible when the sidebar is collapsed, uses compact topbar
  spacing, and exposes menu semantics and an accessible avatar fallback.
- Keep user normalization tolerant of dict-shaped users, AdminUser records,
  and protocol-compatible objects. No authentication or authorization logic
  moves into the UI component.
- Keep generated cluster/tool/administration entries under the manager's
  existing authorization boundary rather than accidentally treating their
  landing paths as resource permissions.
- Keep SystemBox permission filtering and add active-state styling for direct
  utility links.
- Rename the default resource group from Default to Workspace at the
  navigation-builder presentation boundary. Configured groups and contributor
  group labels remain unchanged.

### 4.3 Styling and responsive behavior

- Add semantic shell hooks for the topbar account control, sidebar utility
  region, Administration/Operations sections, and active utility links.
- Preserve the existing mobile drawer, mini-sidebar, dark mode, focus rings,
  reduced-motion behavior, and same-origin route handling.
- Ensure the topbar account dropdown does not expand to the full width of the
  action row and remains inside the viewport on narrow screens.

## 5. Implementation map

| Area | Change |
| --- | --- |
| `admin/navigation/manager.py` | Primary placement, cluster landing, utility/admin groups, stable group ordering, and personal-only user-menu option. |
| `admin/navigation/nav_item_builder.py` | Human-readable Workspace label for the default resource group. |
| `admin/ui/organisms/sidebar.py` | Account removal from sidebar footer; utility/footer semantics. |
| `admin/ui/organisms/topbar.py` | Render the authenticated UserBox in the topbar. |
| `lexigram-ui/ui/organisms/userbox.py` | Add a reusable topbar variant without sidebar-state coupling. |
| `admin/ui/organisms/systembox.py` | Active utility presentation and aria-current support. |
| `admin/ui/templates/shell_sections.py` | Preserve explicit manager authorization for generated shell destinations while retaining resource permission inference. |
| `admin/engine/renderer.py`, page wrappers | Request personal-only user menu for the rendered shell. |
| `admin/static/css/admin.css` | Account, utility, section, and responsive polish. |
| `admin/tests/unit/...` | Navigation placement, permissions, deduplication, user-menu compatibility, and rendered shell regressions. |
| `docs/09-01-2026/README.md`, roadmap | Record the completed sidebar information-architecture work and deferred browser verification. |

## 6. Acceptance criteria

### Information architecture

- [x] Dashboard/core actions remain first and resources render under
      Workspace or their configured group labels.
- [x] Registered cluster centers appear as primary Operations links; their
      secondary nav and active state remain correct.
- [x] Security/integration/tool groups are ordered consistently, while custom
      groups and item order remain supported.
- [x] Superadmin-only administration links appear only for superadmins and
      are absent for regular users.
- [x] Settings is visible in the sidebar utility region; application-provided
      utility entries are preserved, mounted, and deduplicated.
- [x] No rendered primary/sidebar destination is duplicated in the topbar
      account menu.

### Account and accessibility

- [x] Authenticated user identity and account dropdown render in the topbar,
      including dict and protocol-shaped user objects.
- [x] Profile and Sign out remain available; custom personal menu entries keep
      their permission filtering.
- [x] The sidebar no longer renders the UserBox, and moving/collapsing the
      sidebar does not hide the topbar user's name.
- [x] Account and utility controls have accessible labels, menu semantics,
      keyboard escape/outside-close behavior, focus rings, and safe avatar
      fallback rendering.
- [x] Desktop, mini-sidebar, mobile drawer, dark mode, and reduced-motion
      paths remain intact.

### Compatibility and verification

- [x] Custom admin prefixes are used for every generated link.
- [x] Existing direct `NavigationManager.user_menu_items()` callers retain
      their default compatibility behavior; the renderer opts into the
      personal-only placement.
- [x] Focused navigation/sidebar/topbar tests pass, followed by the admin UI
      regression suite.
- [x] Changed-source Ruff, targeted mypy, generated HTML assertions, and
      `git diff --check` pass.
- [x] The tracker records the implementation; playground/browser verification
      remains explicitly deferred and PR #26 remains open and unmerged.

## 7. Non-goals

- No redesign of the dashboard widgets or page content.
- No change to authorization middleware, route guards, or superadmin policy.
- No new database/settings schema for navigation state.
- No automatic playground startup or browser round-trip in this repository
  step.
- No removal of the backwards-compatible navigation manager API.

## 8. Rollout and follow-up

The change is server-rendered and additive. Existing consumer-provided
navigation contributions continue to flow through the same manager and shell
interfaces. Deployments with custom groups keep their labels and within-group
ordering; only the presentation order of recognized shell sections changes.

The sidebar collapse preference remains local to the browser. Future work may
add user-configurable pinned links or saved navigation layouts, but those are
not required for a coherent default information architecture.

## 9. Implementation notes

Implemented on 2026-09-03. `NavigationManager.resolve_nav()` now promotes
registered cluster centers into an Operations section, adds the Plugins
landing route under Tools, adds superadmin-gated administrative destinations,
normalizes Settings and supplied utility links to the request's admin prefix,
and applies stable section ordering without reordering contributor items.
Explicit empty cluster registries remain respected; the built-in registry is
used only when app state does not provide a real registry.

`user_menu_items()` retains its legacy full-navigation default and adds the
keyword-only `include_navigation=False` mode used by the renderer and page
wrappers. The personal menu therefore contains Profile and Sign out while the
application destinations are rendered once in the sidebar. Sidebar rendering
now keeps SystemBox and the collapse control in a utility footer; TopBar owns
the reusable, sidebar-state-independent UserBox variant.

Regression coverage includes custom-prefix and cluster ordering/active-state
cases, superadmin gating, topbar account markup, sidebar account absence,
utility rendering, and the existing full admin unit suite. Changed-source Ruff,
targeted mypy, focused UI tests, the complete admin unit suite (5,856 passed,
7 skipped), shared UI tests (203 passed), and `git diff --check` passed. The
repository's unrelated pre-existing format drift remains isolated to
`page_handlers.py`; the changed lines are formatted. Playground/browser
round-trip verification remains intentionally deferred, and PR #26 remains
open and unmerged.
