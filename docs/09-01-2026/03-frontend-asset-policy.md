# 03 — Frontend Asset Policy (vendoring, pinning, CSP)

Standing policy for all browser-facing JavaScript/CSS in lexigram-admin.
Adopted 2026-09-01 after the lucide/SortableJS incident (bug B6, doc 01).

## Policy

1. **All shell-critical assets are vendored** under
   `src/lexigram/admin/static/` and served from the admin's own static
   mount (`{prefix}/static/...`). The admin panel must render fully — icons
   included — with **zero external network access**. Air-gapped and
   egress-restricted deployments are first-class.
2. **Exact version pinning, no ranges, never `@latest`.** The version is
   part of the review diff when an asset is updated.
3. **Source of truth is the npm registry tarball**, not a CDN download:
   `https://registry.npmjs.org/<pkg>/-/<pkg>-<version>.tgz`. CDNs rewrite
   files and are frequently blocked; tarballs are content-addressed and
   auditable.
4. **Optional/heavy libraries** (rich-text editors, charting) may load
   lazily but must honor a configurable URL so operators can point them at
   local copies. Defaults should still be pinned versions.
5. **Asset prefix derivation**: templates/layouts must derive URLs from the
   configured mount (`ctx.base_url` / `static_prefix`), never hardcode
   `/admin`, so non-default mounts (`/backoffice`) serve their own assets.

## Current inventory

| Asset | Version | File | Loaded by |
| ----- | ------- | ---- | --------- |
| htmx | 1.9.10 | `static/js/htmx.min.js` | authed shell (`views/templates/base.html`) |
| Alpine.js | 3.x | `static/js/alpine.min.js` | authed shell, `AdminLayout` |
| Alpine focus plugin | 3.x | `static/js/alpine-focus.min.js` | authed shell, `AdminLayout` |
| Lucide icons | 0.544.0 | `static/js/lucide.min.js` | authed shell, `AdminLayout`, `StandaloneLayout` |
| SortableJS | 1.15.0 | `static/js/sortable.min.js` | `AdminLayout` (dashboard widgets) |
| Trix | 2.0.8 | `static/js/trix.umd.min.js`, `static/css/trix.css` | `RichTextField.render_assets()` (rich-text fields) |
| admin.js | in-repo | `static/js/admin.js` | authed shell |

Icon initialization: `lucide.createIcons()` runs on `DOMContentLoaded` and
re-runs on `htmx:afterSwap` (partial swaps insert fresh `data-lucide`
nodes). Any new HTMX-swapped surface must keep this behavior.

## Known remaining CDN references (migration queue)

Resolved 2026-09-01:

- **Trix — DONE.** Vendored 2.0.8 under the static mount;
  `RichTextField.render_assets(asset_prefix=...)` resolves `{prefix}`
  URL templates against the admin mount (override the class attributes with
  absolute URLs to serve from elsewhere). Tests:
  `tests/unit/schema/test_text_area.py` (vendored paths, no CDN, files exist).
- **`controllers/resource/list.py` fallback — DONE.** The default
  `render_list` fallback (NOT just a docstring — a live code path for
  subclasses that don't override it) loaded htmx from unpkg; it now uses the
  vendored copy, deriving the mount prefix from the request `root_path`.
- **Default CSP — DONE.** `DEFAULT_CSP` no longer allows any third-party
  origin (`unpkg` removed from `script/style/connect-src`).
  `'unsafe-inline'` remains until R18 (inline style/script consolidation).
  Operators using the external chart CDNs must extend `script-src` via the
  security settings panel. Tests: `tests/unit/settings/test_default_csp.py`.

Still open:

| Site | Ref | Plan |
| ---- | --- | ---- |
| `services/charts.py` | Chart.js **pinned to 4.4.1** and Plotly 2.27.0 — both class-attribute `script_url`s (2026-09-01) | Override `ChartJSRenderer.script_url` / `PlotlyRenderer.script_url` to self-host; vendor when charts ship in the default dashboard. Note: the default CSP blocks these CDNs — chart users must extend `script-src` or self-host. |
| `lexigram-ui` `HeadConfig.icon_library_url` | lucide 0.263.1 (unpkg, pinned) | Different package with external consumers; keep the configurable default, document pointing it at a local copy. Admin does not use this path. |

## How to add or update a vendored asset

```bash
# 1. Fetch the exact tarball
curl -sL -o /tmp/pkg.tgz https://registry.npmjs.org/<pkg>/-/<pkg>-<ver>.tgz
mkdir -p /tmp/pkg && tar xzf /tmp/pkg.tgz -C /tmp/pkg

# 2. Copy the minified UMD build
cp /tmp/pkg/package/dist/... \
   experimental/apps/lexigram-admin/src/lexigram/admin/static/js/<name>.min.js
```

Then: reference it via the derived asset prefix in every layout that needs
it, update the inventory table above, and update/extend the head-content
unit tests (`tests/unit/test_admin_layout.py` asserts local paths and
**no `unpkg.com`** in rendered heads — keep that assertion green).
