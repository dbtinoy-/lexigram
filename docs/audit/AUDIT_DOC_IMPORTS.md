# AUDIT_DOC_IMPORTS.md — Lexigram Documentation Import Audit

> **Source**: Every `lexigram.*` `from`/`import` statement in the python
> blocks of every package `docs/*.md` file, resolved against the installed
> framework with `importlib`. An import fails when its module cannot be
> imported or when an imported name is missing from that module.

## Summary

- Imports verified: 1529
- Unresolved imports: 0

No unresolved `lexigram.*` imports detected.
