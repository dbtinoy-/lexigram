# 44 — CSP enforcement flip: guided promotion workflow (R48)

**Date:** 2026-09-03 · **Status:** shipped · **Roadmap:** doc 14 §3 /
doc 30 §2.6 follow-up ("enforcement flip") · **Branch:** `arena/01a05b98-lexigram`

## 1. Problem

The CSP v2 machinery is complete — strict candidate in Report-Only
(doc 30), violations tab (doc 31), settings-editable keys with a 30 s
TTL on the middleware (docs 32/33) — but the migration's *destination*
is missing: there is no way to actually **flip the candidate policy to
enforcement**. An operator who has driven violations to zero must know
(a) that `admin_ui.admin.security.csp` is the magic settings key,
(b) how to copy the candidate policy into it verbatim, and (c) that
enforcing the strict policy on the stock UI breaks every Alpine
expression (B14: the vendored standard build needs `'unsafe-eval'`;
doc 14 measured 11 inline script blocks needing `'unsafe-inline'`).
Nothing warns them. The flip is a hand-edit with a footgun attached.

## 2. Design

### 2.1 Pure policy analysis (`services/security/promotion.py`)

- `parse_directives(policy) -> dict[str, list[str]]` — tolerant
  split-on-`;` parser.
- `ui_compat_blockers(policy) -> list[str]` — deterministic,
  code-level knowledge from doc 14: flags a candidate whose
  `script-src` lacks `'unsafe-eval'` (standard Alpine compiles every
  directive via the Function constructor) or `'unsafe-inline'`
  (inline registrations + `hx-on`), or whose `style-src` lacks
  `'unsafe-inline'`. Empty list ⇒ candidate is compatible with the
  stock UI. A directive that is *absent* falls back to `default-src`
  fetch semantics — the checker resolves that fallback for script/style.

### 2.2 Enforcement card on the CSP tab

Rendered after the policy cards: current enforced source (compile-time
default vs settings override), the candidate + monitoring status,
readiness signals (violation totals from the in-memory store, with the
honest caveat that the store resets on restart), and the compat
blockers listed in plain language. Two actions:

- **Promote** (`POST /admin/security/csp/promote`): writes the current
  candidate policy to `admin.security.csp` and sets
  `csp_report_only=off` (report-only of the now-enforced policy is
  pure noise). Guardrails, in order: settings store wired → report-only
  monitoring actually on → candidate differs from the enforced policy
  → **if blockers exist or violations were recorded, an explicit
  `acknowledge` checkbox is required**, with the flash naming exactly
  what was not acknowledged. Ack-gating rather than refusing outright
  keeps the path open for deployments that migrated their front-end
  (Alpine CSP build) — flexible long-term, safe by default.
- **Roll back** (`POST /admin/security/csp/rollback`): only offered
  while an override exists; clears `admin.security.csp` (empty string
  — the middleware's `if csp else DEFAULT_CSP` makes that revert to
  the compile-time default) and restores `csp_report_only=""` (strict
  candidate monitoring resumes). The escape hatch is one click because
  a bad promote takes the admin UI down *for the operator too* —
  rollback must not require knowing settings keys.

Both: superadmin guard, CSRF, `SETTINGS_UPDATED` audit events with
`source=csp_tab`, `action=csp_promote|csp_rollback`, policy length +
ack flag in metadata (not the full policy — metadata stays small).
Redirect back to the CSP tab with a flash either way. Thanks to the
R37 TTL the flip is live within ≤30 s, no restart.

### 2.3 Out of scope

- The inline-code migration itself (doc 14 §3 — standalone project,
  needs real browsers).
- Editing policies on this page (settings panel remains the editor).
- Persistent violation storage.

## 3. Implementation order

1. `promotion.py` helpers + tests.
2. Enforcement card + promote/rollback handlers + tests.
3. Live verify: promote DEFAULT-compatible candidate & strict-with-ack;
   header flip within TTL via `curl -I`; rollback restores.
4. Doc §4 + README row + commit/push (no merge).

## 4. Verification

- **Unit:** 11 tests in `tests/unit/services/test_csp_promotion.py`
  (parser: split/whitespace/duplicate-keeps-first/lowercase/None-safe;
  blockers: `DEFAULT_CSP` always flip-safe (B14 regression),
  `STRICT_CSP` flags all three, `default-src` fallback governs scripts,
  no-restriction ⇒ no blockers, nonce/hash sources satisfy the inline
  checks) + 16 in
  `test_security_controller.py::TestCspEnforcementFlip` (card states:
  monitoring off / strict-with-3-warnings-and-ack / already-enforced /
  override-offers-rollback / violation counts; promote: no store,
  monitoring off, already enforced, strict-without-ack blocked naming
  "3 known UI-compatibility issue(s)", strict-with-ack writes both keys
  + audit metadata `{action, acknowledged, blockers, violations}`,
  compatible candidate needs no ack, recorded violation forces ack,
  CSRF rejection; rollback: clears both keys + audit, no store; both
  routes 403-gated). File total 61; full suite **5784 passed**. Ruff +
  mypy clean; no route collision for `/csp/promote|rollback`.
- **Live (playground, fresh restart):** CSP tab renders the
  Enforcement card ("compile-time default", 3 ⚠ warnings, ack
  checkbox). Promote without ack → flash "Promotion needs explicit
  acknowledgement: 3 known UI-compatibility issue(s)". With ack →
  `tenant_configs` rows `admin.security.csp = STRICT_CSP`,
  `csp_report_only = "off"`; **35 s later the response header is the
  strict policy and `Content-Security-Policy-Report-Only` is gone** —
  no restart. Card now shows "settings override" + Roll back. Rollback
  → both keys `""`; 35 s later the default enforced header is back and
  the Report-Only header re-appears. Audit trail:
  `settings_updated {action: csp_promote, policy_length: 195,
  acknowledged: true, blockers: 3, violations: 0}` and
  `{action: csp_rollback}`.

