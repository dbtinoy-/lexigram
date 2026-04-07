# Lexigram Scripts

Unified tooling entrypoint for framework audits and script automation.

## Run

From repo root:

```bash
uv run python -m scripts.cli audit list
uv run python -m scripts.cli audit run env_vars
uv run python -m scripts.cli audit run rules
uv run python -m scripts.cli audit run all
uv run python -m scripts.cli audit validate
```

## Architecture

- `scripts/cli.py`: single command surface
- `scripts/core/`: shared runtime utilities (context, registry, models, validation)
- `scripts/audit/generators/`: modular audit generators
- `scripts/catalogs/`: standalone catalog generators (error codes, env vars, CLI commands)

No backward-compat script wrappers are maintained. Callers must use `scripts.cli` directly.

## Makefile

Audit targets call the same CLI:

- `make audit-overview`
- `make audit-integrations`
- `make audit-protocols`
- `make audit-security`
- `make audit-quality`
- `make audit-rules`
- `make audit-tests`
- `make scripts-audit`
- `make scripts-audit-index`
- `make scripts-audit-validate`
- `make scripts-audit-rules`
- `make audit-files`

Quality and test audits are evidence-backed:

- `AUDIT_QUALITY.md` records live `ruff check` and `mypy` command evidence.
- `AUDIT_TESTS.md` records live `pytest` execution evidence plus parsed examples.
- `AUDIT_RULES.md` records Lexigram architecture misalignments found by the rules scan.

## Testing

```bash
uv run pytest tests/scripts tests/test_env_audit_non_config_sources.py -v --no-cov
uv run ruff check scripts tests/scripts
```
