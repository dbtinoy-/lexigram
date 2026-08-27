# Superpowers Specs — Repository Hardening Program

Generated 2026-08-22 from the bug-hunt + recommendation-validation sessions.
Each spec below addresses a **class** of defect actually found in this repo,
not a hypothetical. Every spec has a matching implementation plan in this
directory (`2026-08-22-*.md`) written with the superpowers:writing-plans skill.

| # | Spec | Defect class (real incidents) | Plan |
|---|------|-------------------------------|------|
| 1 | [regression-gates](spec-regression-gates.md) | Stub-shadow MRO bug in auth controller; relay-gateway `/health` route shadowing; unresolvable `AuthController` DI at mount time | `2026-08-22-regression-gates-plan.md` |
| 2 | [protocol-conformance](spec-protocol-conformance.md) | `TaskProviderProtocol` grew methods; runtime-checkable stubs silently stale | `2026-08-22-protocol-conformance-plan.md` |
| 3 | [workflow-hygiene](spec-workflow-hygiene.md) | Concurrent-lane working-tree wipe; dead config knobs (`default_seed`); unpinned dependency drift (typer 0.27 API removal) | `2026-08-22-workflow-hygiene-plan.md` |
| 4 | [security-remediation](spec-security-remediation.md) | Full-repo security audit: CSRF fail-open, mass-assignment, client-controlled tenant identity, SSRF via redirects, log-redaction gaps, Sentry scrubbing, SecretStr sweep, JWT aud, identifier interpolation, codegen traversal | Phase plans: `2026-08-22-security-criticals-plan.md`, `2026-08-22-outbound-safety-plan.md`, `2026-08-22-secrets-logging-plan.md`, `2026-08-22-medium-hardening-plan.md` |

## Non-goals (validated as already-satisfied or rejected)

- **Integration gating**: ci.yml already runs the scenario suite on every push
  (job `integration`, line 144). No work needed.
- **AUDIT_EXPERIMENTS.md / demos/eval-reproduce**: rejected — duplicates
  `docs/ai/EVALUATION.md`, `docs/ai/EXPERIMENT_REPRODUCIBILITY.md`, and the
  gated llm-experiment demo.
- **Multimedia optional-extra split** (torch/gradio override block): deferred —
  requires a lockfile design spike before any pyproject change. Tracked as a
  follow-up, intentionally not planned here.

## Execution

Run each plan independently via subagent-driven development or executing-plans.
Plans are ordered: regression gates first (highest defect yield), then protocol
conformance, then workflow hygiene.
