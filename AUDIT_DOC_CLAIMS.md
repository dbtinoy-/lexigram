# AUDIT_DOC_CLAIMS.md — Lexigram Documentation Claims Audit

> **Source**: Every `LEX_*` env var and `ProviderPriority.*` mention in every
> package `docs/*.md` file (prose + python blocks), resolved against the
> installed framework. Env vars must map to a real `*Config` field> (`LEX_<SECTION>__<KEY>` / `LEX_<PACKAGE>__<KEY>`) or be read directly by
> framework code.

## Summary

- Env vars verified: 806
- Priorities verified: 26
- Unresolved claims: 0

No unresolved doc claims detected.
