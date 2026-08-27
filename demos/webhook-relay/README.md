# Webhook Relay Demo

Teaches Lexigram webhook pattern — HMAC signing, payload validation,
and relay routing.

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | Configuration — webhook relay settings |
| 2 | `src/webhookrelay/app.py` | Composition root — module wiring |
| 3 | `src/webhookrelay/di/provider.py` | Provider lifecycle — register, boot, shutdown |
| 4 | `src/webhookrelay/signer.py` | HMAC signing implementation |
| 5 | `src/webhookrelay/services/` | Webhook validation and relay patterns |
| 6 | `tests/` | Real composition root, no mocks |

## Quick start

```bash
cd demos/webhook-relay
uv run python -m webhookrelay
```

## Run tests

```bash
cd demos/webhook-relay
uv run pytest tests/ -v
```
