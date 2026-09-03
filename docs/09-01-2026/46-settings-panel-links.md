# 46 — System Info in the settings sidebar: surfacing contributor panels (R50)

**Date:** 2026-09-03 · **Status:** shipped · **Roadmap:** doc 32
§2.3 follow-up (catalog unification) · **Branch:** `arena/01a05b98-lexigram`

## 1. Problem

The settings page sidebar is built exclusively from **ConfigRegistry
specs** (`SettingsController._build_categories`), while contributor
**settings panels** — today exactly the core contributor's read-only
System Info diagnostics page (`SettingsPanelDefinition`, route
`/admin/system/info`) — live in a parallel catalog assembled by
`SettingsPanelAssembler` that nothing on the settings page reads. The
result: System Info is reachable only by typing its URL. Doc 32 §2.3
explicitly deferred "unifying those catalogs".

## 2. Design

### 2.1 Unify at the presentation layer, not the type layer

Specs are *editable namespaces* (form posts, revisions, audit);
contributor panels are *self-owned pages*. Forcing panels into
`ConfigCategory`/spec shape would fake namespaces and break the save
pipeline's assumptions. The catalogs stay separate; the **sidebar**
becomes the union — which is all §2.3 ever needed. Since doc 32 the
structured page handler shell-wraps full navigations and returns bare
fragments for `HX-Target` fetches, so a panel link can carry the exact
same `hx-get → #main-content` behaviour as spec links: one navigation
model, two catalogs.

### 2.2 Changes

- `settings/panel/types.py`: `PanelLink` value type (`title`, `url`,
  `icon`, `category`) — deliberately *not* the contracts-level
  `SettingsPanelDefinition` (which carries a live handler reference;
  the layout should render data, not hold handlers).
- `ConfigLayout(panel_links=...)`: after the spec categories, panels
  render grouped by their `category` label ("System" for System Info)
  with the same link classes + htmx attributes as spec links. No
  panels ⇒ output byte-identical to today.
- `SettingsController(dashboard=None)`: duck-typed provider with
  `async get_settings_panels(user)` (the `DashboardAssembler`
  singleton). New `_panel_links(request)` helper: current user →
  assembler (permission-filtered there) → `PanelLink`s; any error →
  `[]` and a warning — the settings page never breaks because a
  contributor's panel catalog does. Both render sites (`index`,
  `_render_spec_page`) pass the links.
- `di/mount/controllers.py`: in the existing SettingsController block,
  best-effort `resolver.resolve(DashboardAssembler)` → `dashboard=`.

### 2.3 Out of scope

- Active-state highlighting for panel links (panels render on their
  own routes, not under `/admin/settings/…`; the sidebar isn't on
  screen when a panel is open in full navigation).
- Merging the two catalogs at the type level.

## 3. Implementation order

1. `PanelLink` + `ConfigLayout` rendering + component tests.
2. Controller helper + ctor param + render-site plumbing + tests.
3. Mount wiring; live verify: sidebar shows "System" → "System Info"
   linking to `/admin/system/info` with htmx attrs.
4. Doc §4 + README row + commit/push (no merge).

## 4. Verification

**Unit (2026-09-03).** New suite `tests/unit/settings/test_settings_panel_links.py`
— 11 tests: `PanelLink` defaults/immutability; `ConfigLayout` renders nothing
extra without panels (output byte-identical to before), renders grouped links
with the full spec-link htmx attribute set (`href` + `hx-get` +
`hx-target="#main-content"` + `hx-swap="innerHTML"` + `hx-push-url` +
`data-admin-navigation` + `data-settings-nav`), sorts groups alphabetically and
places them after spec categories; controller `_panel_links` returns `[]`
without a dashboard, forwards the current user for permission filtering, sorts
by `(order, title)`, applies icon/category fallbacks, skips route-less panels,
and degrades to `[]` on assembler failure. Regression:
`tests/unit/settings` + `tests/unit/controllers` → **731 passed**. Ruff clean;
mypy shows only the pre-existing `union-attr` baseline error in
`di/mount/controllers.py`.

**Live (playground, root@playground.dev).** After restart,
`GET /admin/settings` (followed redirect to first spec page) renders exactly one
`data-testid="settings-panel-links"` group: header **System**, link **System
Info** with

```html
<a href="/admin/system/info" hx-get="/admin/system/info"
   hx-target="#main-content" hx-swap="innerHTML" hx-push-url="true"
   data-admin-navigation data-settings-nav class="block px-3 py-2 pl-9 …">
```

`GET /admin/system/info` → 200 full document (~100 KB); the same URL with
`HX-Target: main-content` → 200 bare fragment (~2.4 KB, no `<html>`), so the
htmx swap into `#main-content` behaves identically to spec links (doc 32
fragment contract). All CSS classes used (`pl-9`, `space-y-1`, `mb-4`,
`truncate`, link classes) verified present in the prebuilt `tailwind.css`.

