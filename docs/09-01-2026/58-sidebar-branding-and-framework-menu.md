# 58 — Sidebar branding control and framework menu consolidation (Full Plan)

**Date:** 2026-09-03 · **Status:** complete · **Roadmap:** R58 · **Branch:**
`arena/01a05b98-lexigram`

## 1. Purpose and acceptance criteria

The first sidebar pass moved account actions to the topbar and promoted
framework destinations into the primary navigation. The remaining shell
polish is easy to miss but important on every admin page: the collapse control
is currently separated from the brand at the bottom of the sidebar, and
framework-owned links are spread across several sections. This Full Plan
consolidates that interaction without weakening contributor navigation,
permissions, custom mounts, or responsive behavior.

The implementation is complete only when:

- the sidebar collapse toggle is adjacent to the logo/site name in the sidebar
  header, with an accessible name and keyboard/focus behavior;
- collapsed mode hides both the logo mark and site name in the header while
  leaving the toggle as the only header control;
- expanded mode preserves the logo link, branding text, and a predictable
  toggle position without changing the sidebar's responsive drawer contract;
- framework-owned destinations (cluster centers, Plugins, and privileged
  administration destinations) appear under one accessible, collapsible
  `Framework` section instead of separate top-level groups;
- contributor-owned resource, integration, security, and custom groups remain
  independently extensible and retain their existing order, active state,
  permission filtering, badges, and custom-prefix URL behavior;
- the framework section can be opened with a keyboard, exposes truthful
  `aria-expanded`/`aria-controls` state, and opens by default when the active
  destination is inside it;
- the sidebar utility footer remains available, including Settings and
  application-provided system links, and no account menu is reintroduced into
  the sidebar;
- direct navigation API compatibility is preserved, including the legacy
  full user-menu option and the existing `include_navigation=False` personal
  menu used by the topbar;
- focused navigation/sidebar/shell tests, the relevant admin unit suite,
  changed-source static checks, and `git diff --check` pass. Browser/playground
  round-trip verification remains intentionally deferred.

## 2. Audit findings

### 2.1 Collapse control is detached from the brand

`Sidebar.render()` places the logo mark and site name in the header but puts
the collapse toggle in the footer. Operators associate the toggle with the
navigation chrome, so its current location costs scan time and leaves the
header unbalanced. In mini mode the logo mark remains visible while the site
name is hidden, even though the desired compact state is a single toggle.

### 2.2 Framework destinations are fragmented

`NavigationManager.resolve_nav()` currently emits separate `Operations`,
`Tools`, and `Administration` groups for generated cluster centers, Plugins,
and superadmin destinations. Each group is individually collapsible in the
shell, but together they form one framework-owned navigation surface. A single
`Framework` dropdown reduces visual noise while leaving contributor-defined
sections such as `Integrations` and `Security` independent.

### 2.3 Section state should reflect the active destination

`SidebarSection` persists expansion in local storage but starts closed when no
saved preference exists. A newly opened framework route can therefore render
inside a collapsed section, making the active destination difficult to find.
The generic section component should accept optional initial expansion metadata
so the manager can request an open framework section when one of its links is
active, without taking persistence control away from the browser.

## 3. Design

### 3.1 Header branding and collapse control

- Keep the existing `Sidebar` public constructor and `sidebarMini` Alpine
  state. Move the existing toggle button into the header next to the logo and
  text; remove the duplicate footer toggle.
- Add `x-show="!sidebarMini"` to the logo link and full site-name node. In
  collapsed mode the header contains only the toggle, centered with a stable
  focus target. In expanded mode the brand remains a home link and the toggle
  stays aligned at the trailing edge.
- Keep the logo link's accessible label and image alt text meaningful. The
  toggle retains an explicit `aria-label` and `type="button"`; no navigation
  or authentication logic moves into the component.
- Leave the footer dedicated to `SystemBox` utilities. The mobile drawer,
  `sidebarOpen`, width binding, and custom admin prefix remain unchanged.

### 3.2 One framework dropdown

- Treat manager-generated cluster landing entries, Plugins, and superadmin
  Users/Roles/Security/Email entries as framework-owned destinations. Collect
  them into one `Framework` group with a stable icon and a generated marker
  that does not affect authorization.
- Preserve deduplication against resource and contributor links by URL. A
  contributor-provided item that already owns a destination remains in its
  source group; generated duplicates are not emitted.
- Keep `Operations`, `Tools`, and `Administration` available as recognized
  legacy labels for ordering/consumer data, but do not emit them separately
  from the current manager. Existing direct `user_menu_items()` callers keep
  their legacy navigation list because the change is limited to the rendered
  primary sidebar.
- Add a generic `default_expanded`/icon contract to group headers. The
  framework header requests an open initial state when any framework item is
  active; the user's stored local-storage preference still wins thereafter.
- Keep contributor groups and unknown groups in the existing stable ordering
  after the framework block. No package contributor needs to edit the manager
  to remain visible.

### 3.3 Accessibility and responsive behavior

- Preserve the current `aria-current="page"` behavior on active links and
  `aria-controls` linkage from each section button to its item container.
- Use a real button for section expansion and the header toggle. Avoid links
  with click-only behavior for controls; retain focus-visible rings and
  reduced-motion-compatible transitions.
- In mini mode, framework item icons/initials remain available according to
  the existing sidebar behavior; the header brand is not announced as a
  visible control. On small screens the same header is inside the drawer and
  the existing mobile open/close controls remain responsible for the drawer.

## 4. Implementation map

| Area | Change |
| --- | --- |
| `admin/navigation/manager.py` | Collect generated framework destinations into one stable `Framework` group while retaining deduplication and legacy user-menu compatibility. |
| `admin/ui/templates/shell_sections.py` | Preserve group metadata, including icon/default expansion, while preparing contributor and framework sections. |
| `admin/ui/organisms/sidebar.py` | Move the collapse toggle into the header, hide both brand nodes in mini mode, and support active/default-expanded section state. |
| `admin/tests/unit/navigation/test_navigation_manager.py` | Update generated primary-nav expectations and add framework grouping regressions. |
| `admin/tests/unit/navigation/test_sidebar_information_architecture.py` | Assert framework consolidation without changing contributor group behavior. |
| `admin/tests/unit/ui/test_sidebar_a11y.py` | Assert header toggle placement, mini-mode branding hooks, and section expansion semantics. |
| `admin/tests/unit/ui/test_shell_sections.py` | Keep generic group preparation and metadata compatibility covered. |
| `docs/09-01-2026/02-improvement-roadmap.md`, `README.md` | Record R58 completion and the intentionally deferred browser verification. |

## 5. Implementation order

1. Create this Full Plan before changing the shell.
2. Add generic group metadata/default expansion without changing existing
   contributor defaults.
3. Refactor manager-generated framework entries into one `Framework` group and
   update focused navigation expectations.
4. Move the sidebar toggle beside the brand, hide both brand nodes in mini
   mode, and add accessibility regressions.
5. Run focused navigation/sidebar/topbar tests, the relevant admin unit suite,
   Ruff/mypy/compile checks, and `git diff --check`.
6. Update this plan, the roadmap, and the dated plan index with exact results;
   commit and push only to `arena/01a05b98-lexigram`. Do not merge PR #26.
7. Leave playground/browser round-trip verification explicitly unchecked.

## 6. Compatibility and security notes

This is a presentation-only navigation change. Existing request-time
permission filtering remains in `prepare_navigation()` and
`NavigationManager._is_super_admin()`; the generated framework marker must
not bypass either boundary accidentally. URLs continue to be created from
the request's configured admin prefix. The sidebar does not receive or render
account actions, and no new write/authentication path is introduced.

The existing `NavigationManager.user_menu_items()` default remains unchanged
for integrations that call it directly. `AdminRenderer` continues to request
`include_navigation=False`, so the topbar remains personal-only.

## 7. Verification matrix

- Navigation manager tests for Framework grouping, active state,
  deduplication, superadmin filtering, contributor groups, and custom prefixes.
- Sidebar rendering tests for header toggle placement, hidden logo/name hooks,
  footer utility preservation, mini mode, and section ARIA state.
- Full admin unit suite with `--no-cov` and the shared UI accessibility tests.
- Ruff on changed Python files, targeted mypy, compileall, and
  `git diff --check`.
- Browser/playground round-trip: intentionally deferred.

## 8. Completion record

Completed 2026-09-03 on `arena/01a05b98-lexigram`. The sidebar collapse
control now lives in the header beside the brand in the expanded state and is
the only visible header control in mini mode; both the logo mark and site name
use the existing Alpine state to hide together. The footer remains a
system-utility surface, while account identity/actions remain owned by the
topbar.

`NavigationManager.resolve_nav()` now collects registered cluster centers,
Plugins, and superadmin destinations into one generated `Framework` group.
Generated links retain request-time active state, permission boundaries,
custom-prefix URL construction, and URL deduplication against resources and
contributors. Existing contributor groups remain independently extensible;
a reserved-label collision is merged into one section rather than producing
two Framework dropdowns. Group metadata now carries icons and optional
initial expansion through the shell, and active sections open by default only
when no persisted local-storage preference exists.

Verification completed:

- [x] Focused navigation/sidebar/shell suite: `64 passed, 2 warnings`.
- [x] Full admin unit suite: `pytest -q --no-cov tests/unit` — `5884 passed,
  8 skipped, 14 warnings in 33.06s`.
- [x] Targeted mypy over the five changed production modules: passed.
- [x] Changed-source `compileall`: passed.
- [x] Ruff check/format and `git diff --check`: passed.
- [x] Roadmap and dated plan index updated before delivery.
- [ ] Playground/browser round-trip remains intentionally deferred, per the
  standing session decision.
