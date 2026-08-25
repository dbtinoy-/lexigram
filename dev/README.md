# dev/ — Repository Tooling

Developer-facing tooling that is **not** part of any published package.
Everything here runs via `uv run` from the repo root.

```
dev/
├── cli.py                 # python -m dev.cli …  (audit dispatcher)
├── checks/                # CI quality gates — one module per gate, each with main()
│   └── _data/             #   baselines/snapshots owned by specific gates
├── generators/            # deterministic artifact emitters (catalogs, examples)
│   └── env_vars_catalog/  #   support package for env_example
├── ops/                   # operational scripts (publishing)
│   └── publish_pypi.py
├── core/                  # shared infrastructure used by checks/generators/audit
│   ├── bootstrap.py       #   REPO_ROOT + import shim for standalone runs
│   ├── package_inventory.py  #   workspace member discovery (single source of truth)
│   ├── command_runner.py, context.py, evidence.py, models.py, registry.py
│   └── rules_catalog/, rule_engine.py, validation.py   # audit rules subsystem
└── audit/                 # report framework + per-report generators → docs/audit/
    ├── base.py, index.py, registry.py, non_config_env_sources.py
    └── generators/        #   overview, tests, security, quality, docs_*, …
```

## CI quality gates (`checks/`)

| Gate | Purpose |
|------|---------|
| `checks/tier_boundary.py` | Fails when a stable-tier package depends on an `experimental/` one |
| `checks/dep_pins.py` | Dependency pin policy; baseline: `_data/dep_pins_baseline.json` |
| `checks/stub_shadows.py` | Fails when a class attribute resolves to a `NotImplementedError` stub shadowing a real implementation later in its MRO. Run after any mixin/base refactor |
| `checks/protocol_surface.py` | Fails when a `lexigram.contracts` runtime_checkable Protocol gains/loses public members. After an intentional protocol change run with `--update`, review `checks/_data/protocol_surface.json`, commit both together |
| `checks/env_example.py` | env.example coverage vs referenced variables (completeness target: `.env.full.example`) |
| `checks/env_binding.py` | Empirically verifies every documented `LEX_*` variable binds through its config family's real `from_yaml()` |
| `checks/loc_limit.py` | 500-LOC ratchet; baseline: `_data/loc_limit_baseline.txt` |
| `checks/version.py` | Per-package version scheme (§3.6): within an active series only the build segment moves (`0.1.5001 → 0.1.5002`) |
| `checks/config_fields.py` | Config field catalog consistency |
| `checks/tree_guard.py` | Workspace tree hygiene |

## Conventions

- **Standalone runnable:** every `checks/*` module has `main()` and works both as
  `uv run python dev/checks/<name>.py` and as `from dev.checks.<name> import …`.
- **Import bootstrap:** standalone execution inserts the repo root on `sys.path`
  before any `dev.*` import — use `dev.core.bootstrap` for the canonical root.
- **Adding a workspace package:** add its `src/` to `[tool.mypy] mypy_path`,
  then run `uv run python dev/generators/vscode_settings.py`.
- **Data lives with its gate:** baselines/snapshots belong in `checks/_data/`,
  never loose in `dev/`.
