# Lexigram Scripts

Unified tooling entrypoint for framework audits and script automation.

## Run

From repo root:

```bash
uv run python -m dev.cli audit list
uv run python -m dev.cli audit run env_vars
uv run python -m dev.cli audit run rules
uv run python -m dev.cli audit run all
uv run python -m dev.cli audit validate
```

## Architecture

- `dev/cli.py`: single command surface
- `dev/core/`: shared runtime utilities (context, registry, models, validation)
- `dev/audit/generators/`: modular audit generators
- `dev/catalogs/`: standalone catalog generators (error codes, env vars, CLI commands)

No backward-compat script wrappers are maintained. Callers must use `dev.cli` directly.

## Makefile

Audit targets call the same CLI:

- `make audit-overview`
- `make audit-integrations`
- `make audit-protocols`
- `make audit-security`
- `make audit-quality`
- `make audit-rules`
- `make audit-tests`
- `make audit-docs-links`
- `make scripts-audit`
- `make scripts-audit-index`
- `make scripts-audit-validate`
- `make scripts-audit-rules`
- `make audit-files`

Quality and test audits are evidence-backed:

- `AUDIT_QUALITY.md` records live `ruff check` and `mypy` command evidence.
- `AUDIT_TESTS.md` records live `pytest` execution evidence plus parsed examples.
- `AUDIT_RULES.md` records Lexigram architecture misalignments found by the rules scan.
- `AUDIT_DOC_LINKS.md` records dead internal links inside `docs/lexigram-docs/` (missing targets, missing anchors, `/packages/` routes without a `docs/` folder). The `docs-links` audit fails when any dead link is found, so `make audit-package` catches link rot before merge.
- `AUDIT_SECURITY.md` records live `pip-audit` (dependency) and `ruff check --select S` (SAST) evidence, framework security-rule findings, and open audit-tracker areas parsed from `docs/AUDIT_TRACKER.md`.

## Testing

```bash
uv run pytest tests/scripts tests/test_env_audit_non_config_sources.py -v --no-cov
uv run ruff check scripts tests/scripts
```
