# AUDIT_DOC_CLAIMS.md — Lexigram Documentation Claims Audit

> **Source**: Every `LEX_*` env var and `ProviderPriority.*` mention in every
> package `docs/*.md` file (prose + python blocks), resolved against the
> installed framework. Env vars must map to a real `*Config` field
> (`LEX_<SECTION>__<KEY>` / `LEX_<PACKAGE>__<KEY>`) or be read directly by
> framework code.

## Summary

- Env vars verified: 804
- Priorities verified: 26
- Unresolved claims: 0

## Resolved Claims

| Doc | Claim | Resolution |
|-----|-------|------------|
| `experimental/apps/lexigram-admin/docs/CONFIGURATION.md` | `LEX_ADMIN__AUDIT__REDACTION_FIELD_DENYLIST` | Removed — field is in core logging configurator, not admin config |
| `experimental/apps/lexigram-admin/docs/CONFIGURATION.md` | `LEX_ADMIN__AUDIT__REDACTION_PATTERNS` | Removed — field is in core logging configurator, not admin config |
| `packages/lexigram-auth/docs/CONFIGURATION.md` | `LEX_AUTH__TOKEN__ALLOW_UNVERIFIED_DEV` | Removed — field does not exist; JWTConfig enforces verified-only decoding |
