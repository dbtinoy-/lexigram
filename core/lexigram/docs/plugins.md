# Plugins (lexigram.plugins)

Entry-point plugin discovery and boot-time enable/disable state, shipped inside
the core `lexigram` package.

## Activation

- **Auto (recommended)**: set `lx.discovery.auto_discover = true` — the same
  switch that auto-discovers modules from the `lexigram.modules` entry-point
  group also picks up `PluginsModule`, so every application boot runs the
  plugin engine.
- **Explicit**: `app.add_module(PluginsModule.configure())` (optionally with a
  custom `state_path`).

Discovery, filtering, and instantiation run through the single shared
`discover_providers()` primitive, and the engine enforces descriptor
`requires`/`conflicts` via `validate_plan` — unmet dependencies and enabled
conflicts are excluded with a logged warning, never fatal, and boot is never
blocked.

## Operating notes

- **State file**: `.lexigram/plugins.json` in the working directory by default.
  Override with the `LEXIGRAM_PLUGINS_STATE_PATH` env var.
- **Schema**: versioned (`"version": 1`), `"disabled": [...]` holds entry-point
  names. Legacy unversioned files load fine; unsupported or non-integer schema
  versions are backed up as `.corrupt-<timestamp>` and fail open.
- **Toggle semantics**: `update_disabled(mutator)` runs load–mutate–save inside
  one `flock`/atomic-replace critical section — concurrent admin sessions in
  different processes cannot lose updates. Prefer `update_disabled` over
  separate `load_disabled` + `save_disabled` calls.
- **Failure behavior**: a corrupt state file is preserved as
  `.corrupt-<timestamp>` and reading fails open to an empty set so plugin state
  never blocks boot. Persistence failures raise `PluginStateError`; the admin
  surface converts that into a flash notice + audit entry, never a 500.
- **File integrity**: `plugins.json` is concurrency-safe (`flock` + atomic
  replace) but intentionally not tamper-evident — no HMAC, by design. Write
  access to the state file already implies full filesystem trust, and its
  `disabled` entries are only membership-tested against discovered entry
  points, so the file cannot inject code.
- **Per-page GET (admin)**: the read-only listing at `/admin/plugins` has no
  per-page permission — the global `AdminAuthorizationMiddleware` gates every
  non-public request, the page exposes only entry-point metadata plus the
  disabled set, and only `POST /toggle` requires superadmin /
  `admin.settings.edit` (Sec-2026-08-16-L5, accepted posture).

## Container note

Plugin discovery reads `importlib.metadata` entry points from the packages
installed in *that* process's Python environment. Each service image must
declare the plugin wheels it needs; a plugin discovered in one container is
not visible to another unless it is installed there too. Fleet-wide
enable/disable can share one state file via a mounted
`LEXIGRAM_PLUGINS_STATE_PATH`.