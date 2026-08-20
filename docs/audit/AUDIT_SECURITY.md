# AUDIT_SECURITY.md — Lexigram Framework Security Audit

> **Source**: Live command evidence (pip-audit, ruff bandit rules), framework security rules, and the audit tracker (`docs/AUDIT_TRACKER.md`).

---

## Summary

- Verdict: **WARN** — static analysis findings remain (low-signal noise only)
- Dependency scan: clean (0 vulnerable package(s))
- SAST (ruff `S` rules): 1 finding(s) (0 unverified, 1 verified low-risk, 0 low-signal noise)
- Framework security rules: 0 finding(s)
- Tracker areas: 0 total, 0 done

## Dependency Scan

- Command: `uv run pip-audit --timeout 60`
- Exit code: `0`
- Duration: `67383 ms`
- Vulnerable packages: 0
- Summary: `No known vulnerabilities found`

```text
Name            Skip Reason
--------------- ---------------------------------------------------------------------------------
lexigram-ai-mcp Dependency not found on PyPI and could not be audited: lexigram-ai-mcp (0.1.3008)
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
No known vulnerabilities found
```

## Static Analysis (ruff bandit rules)

- Exit code: `1`

### Findings (unverified)

| File | Line | Rule | Message |
|------|------|------|---------|
| `(none)` | 0 | `-` | No unverified bandit findings. |

### Verified Low-Risk Families (reviewed 2026-08-21; all closed — see notes below)

- Count: 1

| File | Line | Rule | Message |
|------|------|------|---------|
| `demos/llm-experiment/harness.py` | 272 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |

### Low-Signal Rules (S101 asserts, S105/S106 hardcoded strings)

- Count: 0


### Verification Notes

All 305 verified low-risk findings were closed on 2026-08-19 by deep re-verification of every site:

- **S608** (SQL injection, 221 sites): every site re-verified individually. Nine genuine issues fixed: `index_many` index sanitization on the Postgres/MySQL backends, identifier validation at construction for `PostgresFTSQuery`/`MySQLFTSQuery` (table and columns), `Column()` quoting for `batch_processor` record keys, and a collection-name allowlist in `BaseVectorCollection` (prevents quoted-identifier breakout in pgvector SQL). All remaining sites are `# noqa: S608`-annotated with per-site justification: config-only identifiers, allowlisted sanitizers (`_sanitize_index_name`, `_quote_identifier`, `_FIELD_NAME_RE`, `_safe_filter_key`), fixed condition strings, or parameterized values.
- **S110** (except-pass, 41 sites): intentional non-fatal fallbacks; every site annotated with its justification.
- **S311** (pseudo-random, 16 sites): retry/TTL jitter, backoff, sampling, and mock vectors — no security context; annotated.
- **S603** (subprocess, 10 sites): nine operator CLI tooling sites annotated (argv lists, no shell); one genuine fix — `lexigram-cli` MCP self-invocation switched from `sys.argv[0]` to `sys.executable -m lexigram.cli.runtime.main` (argv[0] independence).
- **S607/S104/S704/S701** (17 sites): static PATH tools invoked by the operator, `0.0.0.0` dev-server config defaults, trusted framework HTML composition, and trusted CLI scaffold templates — all annotated with per-site justification.

## Framework Security Rules

| File | Line | Rule ID | Severity | Message |
|------|------|---------|----------|---------|
| `(none)` | 0 | `-` | `-` | No framework security-rule findings. |

## Audit Tracker Status

`docs/AUDIT_TRACKER.md` not found; tracker status unavailable.

## Verified-Clean Surfaces

_(none recorded in the tracker)_

## Open Risk Table

| # | Area | Severity mix |
|---|------|--------------|
| - | (none) | - |

