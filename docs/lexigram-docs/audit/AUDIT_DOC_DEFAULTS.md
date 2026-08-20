# AUDIT_DOC_DEFAULTS.md — Lexigram Documentation Default Claims Audit

> **Source**: Every default-value claim in every package `docs/*.md` file
> (config-table `Default` columns, inline `(default: X)`, prose `defaults to`)
> resolved against the framework's config classes. Claims whose key is
> ambiguous, whose value is not a comparable literal, or whose field has
> no static default are counted unverifiable — never flagged.

## Summary

- Default claims verified: 335
- Unverifiable claims (skipped): 831
- Mismatched claims: 0

No mismatched default claims detected.
