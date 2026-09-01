# 13 — Accessibility Pass + Dead Alpine Handler Class (R17 / B13) (Full Plan)

**Date:** 2026-09-02 · **Status:** 🚧 In progress · **Branch:** `arena/01a05b98-lexigram`

## 1. Audit findings (live HTML, playground)

The baseline is stronger than the roadmap assumed — the shell already ships
`<html lang>`, a skip link, labeled `<main>`/`<nav>` landmarks,
`aria-current` nav marking, `aria-expanded`/`aria-controls` on sidebar
sections, labeled pagination with `aria-current="page"`, real `<button>`s
for column sorting with `focus-visible` rings, keyboard-operable column
resizers (`role="separator"` + arrow-key handlers), labeled row/select-all
checkboxes, and `role="dialog"`/`aria-modal`/`x-trap` on the shared
SlideOver. The gaps that remain:

### 1.1 B13 (critical, functional): Alpine `x_on_*` kwargs render as dead attributes

`el()` converts kwarg underscores to hyphens (`hx_post` → `hx-post`), so
`x_on_click="…"` renders as `x-on-click="…"`. **Alpine only binds
`x-on:event` (or `@event`) — `x-on-click` is silently ignored.** Live-HTML
verified: the admin pages ship `x-on-keydown-down`, `x-on-click`,
`x-on-mouseenter`, `x-on-htmx-after-request` — all dead.

Impact (everything below was *silently broken* for mouse and keyboard):

| Component (file) | Dead behaviour |
|---|---|
| Command palette (admin `command_palette.py`) | ↑/↓/Enter navigation, option click, option hover-select — the palette could open but never execute anything |
| SlideOver (`lexigram-ui slide_over.py` + auto-footer Cancel via `button.py`) | header ✕ Close and footer Cancel buttons (only ESC/backdrop worked) |
| Button loading state (`button.py`) | `loading` spinner never engages/clears |
| Modal (`modal.py`) | trigger open + footer close |
| Section (`section.py`) | collapse/expand |
| Tabs (`tabs.py`) | mobile `<select>` navigation |
| Toggle/Checkbox premium switch (`toggle.py` molecule) | click toggling |
| Page builder (`builder.py`) | move-up/move-down/remove/add block |
| Query builder (`query_builder.py`) | all 7 action buttons |
| Task progress (`task_progress.py`) | `beforeunload` cleanup |

Note: `hx_on_click` → `hx-on-click` is **valid** — htmx explicitly supports
the all-dash `hx-on-` alias (verified in the vendored `htmx.min.js`), so
htmx sites are untouched.

**Fix:** replace every Alpine `x_on_*` kwarg with an explicit dict key in
canonical syntax (`{"x-on:click": …}`, `{"x-on:keydown.down.prevent": …}`).
**Guard:** a source-scan regression test in *both* packages fails on any
new `x_on_` usage with fix guidance (same staleness-guard pattern as design
tokens / schema fingerprint).

### 1.2 A11y gaps (verified on live pages)

1. **Command palette** is a `role="dialog"` with a plain text input and a
   `role="listbox"` whose every option renders `id="option-1"` (duplicate
   ids), no `aria-selected`, no combobox wiring, no focus trap (the
   `alpine-focus` plugin is loaded but unused here).
2. **Row-select checkboxes** all render `id="ids"` (duplicate DOM ids) in
   all four table views (tabular, grid, stacked, calendar).
3. **Flash/toast close buttons** (`shell_scripts.py` × 3) are icon-only
   `<button>`s with no accessible name.
4. **Result count** (“Showing X to Y of Z results”) is not a live region,
   so HTMX-driven filter/sort/page swaps announce nothing to screen
   readers.
5. **Decorative icons**: 82 inline SVGs on the products list, only 9 with
   `aria-hidden` — `get_icon()` (lexigram-ui) does not default to
   `aria-hidden="true" focusable="false"`.

## 2. Changes

| File | Change |
|---|---|
| **lexigram-ui** `atoms/button.py`, `molecules/{builder,modal,section,tabs,toggle}.py`, `organisms/{query_builder,slide_over,task_progress}.py` | B13: all Alpine `x_on_*` → canonical `x-on:` dict keys |
| **lexigram-ui** `atoms/icons.py` | `get_icon()` defaults `aria-hidden="true" focusable="false"` unless the caller passes an ARIA label/role |
| **lexigram-ui** `tests/unit/test_no_dead_alpine_attrs.py` | New: source-scan guard + rendered-output checks |
| **admin** `ui/organisms/command_palette.py` | B13 fix + combobox pattern (`role="combobox"`, `aria-expanded`, `aria-controls`, `aria-activedescendant`), unique option ids, `:aria-selected`, `x-trap` on the dialog, `aria-label` on the input |
| **admin** `ui/organisms/table/views/{tabular_rows,grid,stacked,calendar}.py` | unique per-row checkbox ids (`id="row-select-{rid}"` etc.) |
| **admin** `ui/templates/shell_scripts.py` | `aria-label="Dismiss notification"` on the three flash close buttons |
| **admin** `ui/organisms/pagination.py`, `dashboard/page_renderer.py` | “Showing …” block becomes `role="status" aria-live="polite"` |
| **admin** `tests/unit/ui/test_a11y_regressions.py` | New: source-scan guard + palette ARIA + unique checkbox ids + labeled close buttons + live-region assertions |

## 3. Verification

- Unit: new guard/regression tests green in both packages; both full
  suites green (admin 5357-baseline, lexigram-ui suite).
- Live: re-fetch dashboard/list/palette HTML — zero `x-on-*` dead
  attributes; palette input exposes combobox ARIA; checkbox ids unique;
  close buttons labeled; result count is a polite live region; SVG
  aria-hidden coverage jumps.
- e2e suite green.

## 4. Implementation notes (post-verify)

**Status: ✅ Shipped.**

* B13 fixed at all 18 Alpine call sites in lexigram-ui and 5 in the admin
  command palette. `hx_on_*` left untouched (valid htmx `hx-on-` alias,
  verified against the vendored `htmx.min.js`).
* The existing `Icon` atom's `aria_hidden=False` opt-out is preserved: it
  now passes an explicit `"aria-hidden": None` through to `get_icon()`,
  which suppresses the new decorative default (`el()` drops None-valued
  attributes).
* Two admin tests (`test_button.py`, `test_section.py`) had baked in the
  broken `x-on-click` output as expected behaviour — updated to assert the
  canonical form.
* Remaining hand-rolled SVGs (flash status icons in `shell_scripts.py`,
  topbar search glyph, userbox chevron) marked decorative explicitly.

**Verification (all green):**

* lexigram-ui unit: **1275 passed** (was 1270; +5 new guards), cov 76.64%.
* admin unit: **5366 passed / 8 skipped** (+9 new guards), cov 76.04%.
* admin e2e: **72 passed / 2 skipped**.
* Live (playground, `/admin/` + `/admin/products` after restart):
  * dead `x-on-*` attributes: **10 → 0**;
  * SVG `aria-hidden` coverage: **9/82 → 82/82**;
  * palette: `role="combobox"`, `aria-controls`, `aria-activedescendant`,
    `x-trap.noscroll`, bound unique option ids, `:aria-selected` all
    present;
  * row checkboxes: 10 unique `row-select-{id}` ids, `id="ids"` gone;
  * result count is `role="status" aria-live="polite"`; 3 flash close
    buttons labeled `Dismiss notification`.

