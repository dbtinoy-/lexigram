# Medium Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the medium/low findings that don't require cross-cutting redesign: JWT audience/type discipline, staging secret validation, tenancy redirect+cookie, SQL identifier validation, codegen name containment.

**Spec:** `.superpowers/specs/spec-security-remediation.md` (findings 10–13, 15; backlog notes for 16–19)

## Global Constraints

Same as security-criticals plan. JWT task is explicitly **non-breaking**: no verification behavior changes for existing deployments; only creation gains `aud`.

---

### Task 1: JWT — mint `aud`, keep verification config-gated

**Files:**
- Modify: `packages/lexigram-auth/src/lexigram/auth/authn/_jwt_creation.py:72-85`
- Test: `packages/lexigram-auth/tests/unit/auth/test_jwt_aud.py` (create)

- [ ] **Step 1: Failing test** — created access+refresh tokens contain `aud` claim equal to configured `required_audience` when set, else `"lexigram"` default:

```python
def test_created_tokens_carry_audience(jwt_manager):
    token = jwt_manager.create_access_token(user)
    claims = decode_without_verify(token)
    assert claims["aud"] == getattr(jwt_manager, "_required_audience", None) or "lexigram"
```

- [ ] **Step 2: Implement** in `_create_claims`: add `claims["aud"] = self._required_audience or "lexigram"`. No decode-side change in this task.
- [ ] **Step 3:** package auth unit suite green; commit `-m "🔒 security(auth): mint aud claim on issued tokens"`.

---

### Task 2: Staging validates insecure secrets

**Files:** `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:365-372`

- [ ] Replace env gate with `if self.environment in {"production", "staging"}:` around the insecure-secret check; extend message to name both environments.
- [ ] Failing-first test in existing config validator test module asserting staging + default secret raises the CRITICAL configuration error.
- Commit `-m "🔒 security(admin): enforce secret hygiene in staging"`.

---

### Task 3: Tenancy switch redirect + cookie hardening

**Files:** `experimental/apps/lexigram-admin/src/lexigram/admin/controllers/tenancy.py:78-85`

- [ ] Replace `referer` fallback with `_safe_next_url(referer)` imported from `controllers.auth.core` (falls back to `/admin/`).
- [ ] Add `secure=self._config.tenancy.cookie_secure if hasattr(...) else True` — read from tenancy config, defaulting True; add `cookie_secure: bool = True` field if absent.
- [ ] Tests: forged referer (`https://evil.example`) lands on `/admin/`; same-origin referer preserved; cookie flags asserted via response headers.
- Commit `-m "🔒 security(admin): validate tenancy redirect target and secure switch cookie"`.

---

### Task 4: Identifier validation at interpolation sites

**Files:**
- `packages/lexigram-vector/src/lexigram/vector/backends/pgvector/backend.py:89-109`
- `packages/lexigram-sql/src/lexigram/sql/providers/transaction_manager.py:117-135` (+ caller passing names)
- `packages/lexigram-sql/src/lexigram/sql/unit_of_work/simple.py:535-564`
- `packages/lexigram-sql/src/lexigram/sql/providers/postgres_provider.py:78`

**Shared helper:** reuse contracts identifier regex (`lexigram-contracts/data/identifiers.py`) — add `validate_identifier(name) -> str` raising on mismatch if not already exported.

- [ ] Per site: failing test first (name `x"; DROP TABLE t; --` / `sp_; DROP` raises ValueError before SQL built), then call the helper at each entry point (pgvector create/drop index+table args; savepoint `name` after prefixing; CREATE DATABASE target).
- [ ] Commit `-m "🔒 security(sql): validate identifiers at raw-DDL boundaries"` (vector fix may ride along or split as its own commit under vector scope).

---

### Task 5: Codegen name containment

**Files:** `core/lexigram/src/lexigram/codegen/base.py:132-136` (`_to_snake_case`), `base.py:47-67` (`write_file`)

- [ ] Failing tests: `generate(name="../../evil")` and `name="/abs"` raise `ValueError`; generated path always inside output_dir.
- [ ] Implement: reject post-normalization names containing `/`, `\`, or `..` segments; in `write_file`, assert `resolved.is_relative_to(Path(output_dir).resolve())`.
- [ ] Sweep generator sinks once (web/cli generators listed in spec) — they inherit the base guard.
- Commit `-m "🔒 security(codegen): contain generated-file paths to output dir"`.

---

### Backlog (no tasks here)

16 ai-llm client SSRF gate · 17 uploads `base_dir` required-by-default · 18 Slack host pinning + no-follow · 19 SandboxedEnvironment for prompt rendering · skills exec() sandbox review.
