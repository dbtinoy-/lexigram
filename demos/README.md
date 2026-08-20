# Demos

In-repo demo applications built on the Lexigram framework. Each demo runs
against the editable framework packages in this repository and is gated for
reviewers the same way the framework is:

- **Format + lint** — covered by the root `ruff format --check .` / `ruff check .`
  gates (per-file ignores for demo-specific rules are configured in the root
  `pyproject.toml`).
- **Tests** — `demos/event-driven-orders` and `demos/realtime-monitor` run
  their suites in the workspace env (`make test-demos`).
- **Type check** — the script-only `demos/llm-experiment` is compile-gated.
- `make check-demos` runs the pytest-bearing demo suites + compile checks, and
  is part of `make ci`; GitHub Actions gates all demos in the "Demos gate" job.