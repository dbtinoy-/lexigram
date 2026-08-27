# Plan: Demo config.py → BaseConfig convention sweep

## Goal
Every demo `config.py` follows the framework package convention (exemplar:
`lexigram-cache/config/top_level.py`): `BaseConfig` subclass with declared
`config_section`, `Field` metadata, so configs **self-bind** via
`XConfig.from_yaml(APP_YAML)` — no explicit `get_section()` in app/main.

## Per-demo steps (identical × 12)
1. Rewrite `<pkg>/config.py`: `@dataclass(init=False) class XConfig(BaseConfig)`
   with `config_section = "demo"` (web/auth sections already declare their own);
   keep `APP_YAML`, add `load_lex_config()`; drop any bind_* helpers.
2. `app.py::create_app`: `config or XConfig.from_yaml(APP_YAML)`; sections via
   `WebConfig.from_yaml(APP_YAML)`, `AuthConfig.from_yaml(APP_YAML)` (+ coerce),
   `XConfig.from_yaml(APP_YAML)` — inline like starter.
3. `main.py`: same load-once flow for host/port.
4. Tests: update `test_config.py` to `from_yaml` style + LEX_ env override.
5. Gates: pytest demo · ruff · compileall · live smoke.

## Order
rates → realtime-monitor → auth-apikeys → auth-mfa → auth-rbac → auth-web →
event-driven-orders → rag-docs → support-agent → memory-chat → ai-guardrails →
prompt-lab → feedback-loop → demo-hub (web-only).

## Risks / notes
- Auth demos keep `_coerce_auth_config` (shallow-dict token fix).
- `demo:` section stays minimal — no dead knobs (workflow-hygiene rule).
- mypy on ML demos runs with `--follow-imports=silent --ignore-missing-imports`
  (transformers stub crash documented earlier).
- Commit per demo after its gates pass.

Status: NOT STARTED.
