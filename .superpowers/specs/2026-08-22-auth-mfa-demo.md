# Spec: `auth-mfa` — TOTP enrollment + challenge demo

> **Date:** 2026-08-22 | **Scope:** `demos/auth-mfa/` (new), gates | **Status:** direction given (auth family); design below
> **Family:** third of the `auth-<facet>` demos

## Purpose

Teach **multi-factor authentication** through a real browser flow: TOTP
enrollment (secret + provisioning URI + one-time backup codes), a mandatory
challenge page between password and session, backup-code consumption, and
disable-with-password. Fully offline — no QR service; the `otpauth://` URI
and secret are rendered as copyable text for manual authenticator entry.

## Framework surfaces taught (all verified)

- `MFAManager.enable_totp(user_id, issuer) -> tuple[secret, provisioning_uri, plain_backup_codes]`
  (backup codes stored only as SHA-256 digests)
- `MFAManager.verify_totp(user_id, code) -> bool` — accepts 6-digit TOTP **or**
  single-use backup code (consumed on success)
- `MFAManager.disable_totp(user_id)`
- MFA state lives on `user.profile["mfa"]` via the user store — profile round-tripping shown
- Session gating: login issues a *pre-auth* marker; `SessionManagerImpl.verify_mfa(session_id)` /
  cookie backend complete the session only after challenge success
- Deterministic test codes: tests implement RFC 6238 (stdlib `hmac`/`hashlib`)
  over the enrolled secret — no external authenticator needed in CI

## Pages & flows

| Route | Methods | Behavior |
|---|---|---|
| `/login` | GET, POST | Password step. If the user has MFA enabled ⇒ issue pre-auth session and redirect `/mfa/challenge`; else straight to `/profile` |
| `/mfa/challenge` | GET, POST | Protected by pre-auth session. 6-digit input; wrong code re-renders with error; after 3 failed attempts the pre-auth session is revoked back to `/login`; success upgrades session → `/profile` |
| `/profile` | GET | Shows MFA status; if disabled, link to enrollment; if enabled, shows disable form + remaining backup codes count |
| `/mfa/enroll` | GET, POST | POST generates enrollment: renders provisioning URI as copyable text, the base32 secret for manual entry, and the plain backup codes **once**; requires confirming a first valid code before enabling sticks |
| `/mfa/disable` | POST | Requires current password; calls `disable_totp` |
| `/logout` | POST | As auth-web |

Seeded user `mfa@demo` is enrolled automatically at boot: the provider calls
`MFAManager.enable_totp` during startup (the generated secret lives in the
in-memory store for that process). Tests are deterministic per-process by
reading the secret back from `UserStoreProtocol`
(`user.profile["mfa"]["secret"]`) and computing RFC 6238 codes over it —
no external authenticator, no hardcoded secret.

## Architecture

Same family shape: `src/mfa_console/`, controllers (`login.py`, `mfa.py`),
one shared `SessionCookieBackend`, provider seeds users/roles via
`AuthConfig` and enrolls `mfa@demo` at boot, server-rendered pages, explicit
static route. Serves on `127.0.0.1:8083` (`MFA_PORT`). The RFC 6238 code
generator used by tests lives under `tests/totp.py` (test-owned helper, not
shipped source).

Non-goals: QR image generation (needs a rendering dep), WebAuthn/passkeys,
SMS/email delivery.

## Global constraints

Identical to auth-web spec. Additionally: secrets and backup codes must never
appear in logs; the seeded fixed secret exists only inside config seed code.

## Required tests

1. Enrollment renders URI beginning `otpauth://totp/` and ≥8 plain backup codes exactly once.
2. First valid TOTP confirms enrollment (RFC 6238 helper at fixed time); wrong code does not.
3. Login with MFA-enabled user lands on `/mfa/challenge`, not `/profile`.
4. Valid TOTP upgrades to full session; profile reachable.
5. Backup code works once; second use fails.
6. Disable requires correct password; afterwards login goes straight to profile.
7. Pre-auth session cannot reach `/profile`.
8. Three failed challenge attempts revoke the pre-auth session back to `/login`.

## Acceptance criteria

- [ ] Browser-demoable end to end (manual authenticator or printed seeded code)
- [ ] `make check-demos` green incl. new suite + compile check
- [ ] Gates same-change; demos/README family table gains `auth-mfa`
