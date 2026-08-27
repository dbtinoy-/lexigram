# Spec: `auth-apikeys` — API-key issuance + machine-auth demo

> **Date:** 2026-08-22 | **Scope:** `demos/auth-apikeys/` (new), gates | **Status:** direction given (auth family); design below
> **Family:** fourth of the `auth-<facet>` demos

## Purpose

Teach **machine authentication**: browser-managed API keys (issue with
scopes/expiry, list, revoke) and key-authenticated machine access to a
protected JSON API via the `X-API-Key` header. Raw keys are shown exactly
once; only hashes persist. Fully offline.

## Framework surfaces taught (all verified)

- `APIKeyManager.create_key(user_id, name, scopes, expires_days, prefix)`
  → `(raw_key, APIKey)` — raw returned once, SHA-256 hash stored,
  display prefix kept for identification
- `APIKeyManager.validate_key(raw_key)` / `revoke_key(key_id)` /
  `list_keys(user_id)`
- `APIKeyAuthenticator.authenticate(request_context)` — extracts the key
  from headers and resolves the owning user
- Scope mapping: `authz/scopes.py` `OAuthScope`/`ScopeManager`
  (`read ⊂ write ⊂ delete ⊂ admin` ladder)
- Session-cookie UI auth (as in auth-web) guarding the management pages;
  `X-API-Key` guarding the machine endpoint — two auth mechanisms side by side

## Pages & routes

| Route | Methods | Auth | Behavior |
|---|---|---|---|
| `/login`, `/logout` | GET/POST, POST | — | Same cookie mechanics as family |
| `/keys` | GET | cookie | Key table: name, prefix, scopes, expiry, revoked flag; create form (name, scope checkboxes read/write/admin, expiry days) |
| `/keys/create` | POST | cookie | Issues key; renders raw key once with copyable block + warning; then redirects back to table |
| `/keys/{id}/revoke` | POST | cookie | Revokes; table shows revoked state |
| `/api/me` | GET | `X-API-Key` | Machine endpoint: 200 `{user_id, name, scopes}` when valid+unrevoked+unexpired; 401 with framework error body otherwise |
| `/` | GET | — | Redirects to `/keys` or `/login` |

Serves on `127.0.0.1:8084` (`APIKEYS_PORT`). README documents curl usage:
`curl -H "X-API-Key: sk_live_..." http://127.0.0.1:PORT/api/me`.

## Architecture

Family shape: `src/apikey_console/`, `controllers/keys.py`,
`controllers/api.py`, one shared `SessionCookieBackend`, provider seeds a
demo user, `module.py` importing `AuthModule.configure`, server-rendered
pages. The machine endpoint resolves keys through `APIKeyManager.validate_key`
and enforces scope (`read`) via `ScopeManager.get_scope_permissions` before
answering — an explicit teaching moment for scope-to-permission mapping.

Non-goals: no OAuth2 flows (reserved), no rate limiting, no persistence.

## Global constraints

Identical to auth-web spec. Additionally: raw keys rendered exactly once and
never logged; hashes never rendered.

## Required tests

1. Create key ⇒ table shows prefix + scopes; raw key appears exactly once in the create response.
2. `/api/me` with valid raw key returns owner identity + scopes.
3. Revoked key ⇒ 401 on `/api/me`.
4. Expired key (created with `expires_days=-1`, i.e. already past expiry — note `0` means non-expiring in the framework) ⇒ 401.
5. Missing/garbage header ⇒ 401 with error body.
6. Scope enforcement: admin-scope key passes; a key created with empty scopes is denied scoped actions.
7. Management pages require cookie session (redirect anonymous).
8. Offline determinism.

## Acceptance criteria

- [ ] Browser-demoable management flow + working curl example
- [ ] `make check-demos` green incl. new suite + compile check
- [ ] Gates same-change; demos/README family table gains `auth-apikeys`
