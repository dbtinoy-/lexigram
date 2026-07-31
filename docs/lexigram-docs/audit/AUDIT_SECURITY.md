# AUDIT_SECURITY.md — Lexigram Framework Security Audit

> **Source**: Live command evidence (pip-audit, ruff bandit rules), framework security rules, and the audit tracker (`docs/AUDIT_TRACKER.md`).

---

## Summary

- Verdict: **WARN** — static analysis found issues to review
- Dependency scan: clean (0 vulnerable package(s))
- SAST (ruff `S` rules): 0 finding(s) (0 unverified, 0 verified low-risk, 0 low-signal noise)
- Framework security rules: 1 finding(s)
- Tracker areas: 99 total, 99 done

## Dependency Scan

- Command: `uv run pip-audit --timeout 60`
- Exit code: `0`
- Duration: `33654 ms`
- Vulnerable packages: 0
- Summary: `No known vulnerabilities found`

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
No known vulnerabilities found
```

## Static Analysis (ruff bandit rules)

- Exit code: `0`

### Findings (unverified)

| File | Line | Rule | Message |
|------|------|------|---------|
| `(none)` | 0 | `-` | No unverified bandit findings. |

### Verified Low-Risk Families (reviewed 2026-08-19; all closed — see notes below)

- Count: 0

All previously verified low-risk findings are closed: each site is
either `# noqa`-annotated with a per-site justification or hardened
in code. See Verification Notes.


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
| `lexigram-auth/src/lexigram/auth/authn/_jwt_lifecycle.py` | 214 | `sec-jwt-verification-disabled` | `important` | lexigram-auth/src/lexigram/auth/authn/_jwt_lifecycle.py disables JWT signature verification via options (explicit dev-only opt-in gate). |

## Audit Tracker Status

- Total areas: 99
- Done: 99
- Open: 0

## Verified-Clean Surfaces

- `lexigram-testing`'s fakes — reviewed and confirmed clean; no findings.
- `lexigram-ai-evaluation` — confirmed no LLM-as-judge or prompt-injection surface exists in this package (a plausible-sounding risk that turned out not to apply here).
- `lexigram-queue`'s Kafka/SQS/Azure Service Bus/GCP Pub/Sub backends — all implement proper `max_in_flight`-based backpressure with per-message task isolation (contrast §72/§73, which are specific to the in-memory default and Redis backend).
- `lexigram-workflow`'s dynamic-code-execution and checkpoint-deserialization surfaces — reviewed, clean (contrast §79, which is a narrower SQL-interpolation issue in one query method, not a deserialization/eval risk).
- Fernet encryption usage and JSON-only serialization — confirmed consistent and correct across all 9 packages swept this round.
- Dependency hygiene (2026-08-18): `python-jose`/`ecdsa` removed from the tree (CVE-2024-23342 Minerva timing attack, no upstream fix; pip-audit clean after removal). Only runtime call site was the diagnostic `get_unverified_header()` in `lexigram-admin/.../guards.py` — replaced with a stdlib base64url header decode; auth test token minting switched to `pyjwt` (already a dependency).

## Open Risk Table

| # | Area | Severity mix |
|---|------|--------------|
| - | (none) | - |

