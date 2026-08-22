# API Keys Console Demo

Demonstrates **machine authentication** from lexigram-auth: manage API keys
in a browser (issue with scopes, list, revoke), then call a protected JSON
endpoint with the `X-API-Key` header. Raw keys are shown exactly once; only
hashes persist. Fully offline.

## What it shows

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| Key issuance (scopes, prefix, raw-once) | `controllers/api.py` | `APIKeyManager.create_key(user_id, name, scopes)` |
| Machine authentication | `controllers/api.py` | `X-API-Key` header → `APIKeyManager.validate_key(raw)` |
| Revocation | `controllers/api.py` | `revoke_key(key_id)` — revoked keys immediately 401 |
| Cookie-vs-key auth side by side | `controllers/api.py` | management pages need a session; `/api/me` needs a key |
| Repository adapter | `keys_repository.py` | `APIKeyRepositoryProtocol` implemented in-memory |

## Run it

```bash
uv run python -m apikey_console
```

Open http://127.0.0.1:8084 and log in as `admin@keys.demo` /
`Demo-Password-1`. Create a key with scopes, then call the machine endpoint:

```bash
curl -H "X-API-Key: <raw-key>" http://127.0.0.1:8084/api/me
```

## Notes

- Every command boots a fresh in-memory world: users and keys reset per
  process.
- `APIKEYS_PORT` overrides the port (default 8084).

## Layout

```
demos/auth-apikeys/
├── src/apikey_console/
│   ├── controllers/api.py     # login/logout, keys CRUD, /api/me (X-API-Key)
│   ├── controllers/pages.py   # static file-serving routes
│   ├── ui/                    # views/*.html + static/app.js, keys.js, style.css
│   ├── keys_repository.py     # dict-backed APIKeyRepositoryProtocol
│   ├── session_repository.py  # dict-backed SessionRepositoryProtocol
│   ├── di/provider.py         # seeds demo user, wires manager + backend
│   ├── module.py              # ApiKeysModule (imports AuthModule + WebModule)
│   └── main.py                # uvicorn boot (:8084, APIKEYS_PORT)
└── tests/test_apikeys.py      # end-to-end issue/authenticate/revoke flows
```

## Tests

```bash
uv run pytest demos/auth-apikeys/tests -q
```

Covers: raw key shown exactly once, valid-key machine identity, missing/
garbage/revoked keys all 401, anonymous management blocked (401), and key
listing scoped to the session user.
