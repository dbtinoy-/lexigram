# Audit Generators

Audit generators are implemented as modules under `dev/audit/generators/` and executed through the unified CLI.

## Commands

```bash
uv run python -m dev.cli audit list
uv run python -m dev.cli audit run rules
uv run python -m dev.cli audit run env_vars
uv run python -m dev.cli audit run all
uv run python -m dev.cli audit validate
```

## Available Generators

- `env_vars`
- `overview`
- `integrations`
- `protocols`
- `security`
- `quality`
- `rules`
- `tests`
- `index`

## Evidence Notes

- `quality` uses live `ruff check` and `mypy` results as report evidence.
- `tests` uses live `pytest` runs plus parsed failing-example snippets as report evidence.
- `rules` captures Lexigram-specific architectural misalignments, including import-boundary violations and package-coverage gaps.

## Validation Note

`uv run python -m dev.cli audit validate` currently exits non-zero because the rules audit reports critical violations above the strict threshold of `0`.

## Clean Break Policy

No legacy wrapper commands are supported in this directory. Update callers to `scripts.cli`.
