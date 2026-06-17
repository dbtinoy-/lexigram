# lexigram-plugins

Entry-point plugin discovery and boot-time enable/disable state for the Lexigram
Framework.

## Operating notes

- **State file**: `.lexigram/plugins.json` in the working directory by default.
  Override with the `LEXIGRAM_PLUGINS_STATE_PATH` env var.
- **Schema**: versioned (`"version": 1`), `"disabled": [...]` holds entry-point
  names. Legacy unversioned files load fine.
- **Toggle semantics**: `update_disabled(mutator)` runs load–mutate–save inside
  one `flock`/atomic-replace critical section — concurrent admin sessions in
  different processes cannot lose updates. Prefer `update_disabled` over
  separate `load_disabled` + `save_disabled` calls.
- **Failure behavior**: a corrupt state file is preserved as
  `.corrupt-<timestamp>` and reading fails open to an empty set so plugin state
  never blocks boot. Persistence failures raise `PluginStateError`; the admin
  surface converts that into a flash notice + audit entry, never a 500.
- **Boot integration**: `discover_providers(disabled=state.load_disabled())`
  skips disabled entry points; `validate_plan` surfaces unknown-disabled names
  and unmet dependencies as non-fatal issues.