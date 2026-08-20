# AUDIT_DOC_CLAIMS.md — Lexigram Documentation Claims Audit

> **Source**: Every `LEX_*` env var and `ProviderPriority.*` mention in every
> package `docs/*.md` file (prose + python blocks), resolved against the
> installed framework. Env vars must map to a real `*Config` field> (`LEX_<SECTION>__<KEY>` / `LEX_<PACKAGE>__<KEY>`) or be read directly by
> framework code.

## Summary

- Env vars verified: 804
- Priorities verified: 26
- Unresolved claims: 3

## Unresolved Claims

| Doc | Claim | Reason |
|-----|-------|--------|
| `experimental/apps/lexigram-admin/docs/CONFIGURATION.md` | `LEX_ADMIN__AUDIT__REDACTION_FIELD_DENYLIST` | env var: no config section/key path matches this variable |
| `experimental/apps/lexigram-admin/docs/CONFIGURATION.md` | `LEX_ADMIN__AUDIT__REDACTION_PATTERNS` | env var: no config section/key path matches this variable |
| `packages/lexigram-auth/docs/CONFIGURATION.md` | `LEX_AUTH__TOKEN__ALLOW_UNVERIFIED_DEV` | env var: no config section/key path matches this variable |
