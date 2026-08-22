# MFA Console Demo

Demonstrates **multi-factor authentication** from lexigram-auth through a
real browser flow: password login issues a *pending* challenge for
MFA-enabled users, a 6-digit TOTP code (or single-use backup code) upgrades
it to a full session, and enrollment/disable live on the profile page.

Fully offline: the seeded `mfa@mfa.demo` account is enrolled at boot, and
tests compute RFC 6238 codes directly from the framework's
`generate_totp_code`.

## What it shows

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| Pending challenge flow | `controllers/api.py` | pre-auth session row + `MFAManager.verify_totp(user_id, code)` |
| Enrollment (secret + provisioning URI + backup codes) | `controllers/api.py` | `MFAManager.enable_totp(user_id, issuer)` — codes shown once |
| Disable with password re-check | `controllers/api.py` | `authenticate_user` re-verification + `disable_totp` |
| Attempt capping | `controllers/api.py` | 3 wrong codes revoke the pending session back to `/login` |
| Cookie sessions | `session_repository.py`, `di/provider.py` | `SessionCookieBackend` + `SessionRepositoryProtocol` adapter |

## Run it

```bash
PYTHONPATH=demos/auth-mfa/src uv run python -m mfa_console
```

Open http://127.0.0.1:8083.

- Log in as `mfa@mfa.demo` / `Demo-Password-1` → redirected to `/challenge`.
  The current code is computable from the boot-enrolled secret (tests do
  exactly this); in a browser use your authenticator after enrolling.
- Or log in as `plain@mfa.demo` → straight to `/profile`; enroll TOTP there,
  confirm with a code on next login.

## Notes

- `AuthConfig.users`/`AuthConfig.roles` are inert today — users are seeded in
  the provider's `boot()`, and enrollment happens at boot for `mfa@`.
- Backup codes are stored as SHA-256 digests and consumed on first use.
- `MFA_PORT` overrides the port (default 8083).

## Layout

```
demos/auth-mfa/
├── src/mfa_console/
│   ├── controllers/api.py     # login/challenge/me/status/enroll/disable
│   ├── ui/pages.py            # static file-serving routes
│   ├── ui/views/*.html        # login, challenge, profile
│   ├── ui/static/*            # app.js, mfa.js, style.css
│   ├── session_repository.py  # dict-backed SessionRepositoryProtocol
│   ├── di/provider.py         # seeds users, boot-enrolls mfa persona
│   ├── module.py              # MfaModule (imports AuthModule + WebModule)
│   └── main.py                # uvicorn boot (:8083, MFA_PORT)
└── tests/test_mfa_flows.py    # end-to-end challenge/enroll/disable flows
```

## Tests

```bash
uv run pytest demos/auth-mfa/tests -q
```

Covers: plain-user bypass, pending-challenge issuance, code upgrade to full
session, attempt capping, enroll material shape (`otpauth://totp/` URI +
≥8 backup codes), backup-code single-use semantics, and disable-with-password.
