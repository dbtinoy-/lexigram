# LOC Debt Register

The 500-LOC cap is now effectively enforced repo-wide.

- **Residents:** exactly one, and it is exempt by policy:
  `core/lexigram-contracts/src/lexigram/contracts/__init__.py`
  (§8 public-root facade — exports only).
- **History:** three remediation waves (2026-08-25) decomposed 87 of the
  original 141 residents; per-file rationales for those decompositions
  live in git history (commits tagged `♻️ refactor: LOC wave-*`).
- **Rules:** new violations fail CI; entries whose files drop under the
  limit become stale and must be removed in the same change.
