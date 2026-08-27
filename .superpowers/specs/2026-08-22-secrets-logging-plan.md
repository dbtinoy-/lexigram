# Secrets & Logging Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop leaking secrets through logs (redaction matcher), through Sentry (missing scrubber), and through config reprs (SecretStr sweep).

**Architecture:** redaction switches from exact-key equality to token-substring matching over a normalized key; Sentry gains a `before_send` scrubber masking denylisted keys in request/extra payloads; a mechanical sweep converts the enumerated plaintext secret fields to `SecretStr` with pydantic-style coercion (pattern already in `llm/config.py:290-295`).

**Tech Stack:** existing `lexigram.validation.SecretStr`; structlog processors; sentry_sdk.

**Spec:** `.superpowers/specs/spec-security-remediation.md` (findings 5, 6, 14)

## Global Constraints

Same as security-criticals plan. Additionally: redaction changes MUST NOT break existing explicit-denylist unit tests — extend, don't replace semantics.

---

### Task 1: Redaction matches compound/camelCase secret keys

**Files:**
- Modify: `core/lexigram/src/lexigram/logging/redaction.py:78` (match predicate)
- Test: `core/lexigram/tests/unit/test_logging_redaction.py` (extend)

**Interfaces:** unchanged public API; only matching semantics.

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.parametrize("key", [
    "auth_token", "setup_token", "secret_key", "session_secret",
    "dsn", "server_key", "apns_auth_key", "vapid_private_key",
    "apiKey", "clientSecret", "access_token", "private_key",
])
def test_compound_and_camel_keys_redacted(key):
    out = DefaultRedactor().redact({key: "leak", f"nested_{key}": "leak"})
    assert out[key] != "leak"
    assert out[f"nested_{key}"] != "leak"


def test_non_secret_keys_pass_through():
    out = DefaultRedactor().redact({"monkey": 1, "token_count": 5, "keyboard": "x"})
    assert out == {"monkey": 1, "token_count": 5, "keyboard": "x"}
```

Tune the second test to the final matcher semantics: substring tokens are
`("token", "secret", "password", "passwd", "api_key", "apikey", "authorization",
"auth_", "_auth", "private_key", "dsn", "credential")`. If `token_count`
false-positives under naive substring, refine with word-segment rules
(`_token`/`token_` boundaries) and encode the chosen rule in tests.

- [ ] **Step 2: Red-run**, then implement matcher:

```python
_SECRET_TOKENS = ("token", "secret", "password", "passwd", "credential",
                  "api_key", "apikey", "authorization", "dsn")

def _is_sensitive(key: str) -> bool:
    k = key.lower().replace("-", "_")
    return any(t in k for t in _SECRET_TOKENS)
```

Keep the existing explicit denylist as an additional fast path.

- [ ] **Step 3:** core logging suite green (`core/lexigram/tests/unit/test_logging_redaction.py` + sampling/redaction config tests); commit `-m "🔒 security(logging): redact compound secret keys in log events"`.

---

### Task 2: Sentry before_send scrubber

**Files:**
- Modify: `packages/lexigram-monitor/src/lexigram/monitor/error_tracking.py:82-87`
- Test: `packages/lexigram-monitor/tests/unit/test_error_tracking_scrubber.py` (create)

- [ ] **Step 1: Failing test**

```python
def test_init_registers_before_send_scrubber(monkeypatch):
    captured = {}
    def fake_init(**kwargs):
        captured.update(kwargs)
    monkeypatch.setattr("sentry_sdk.init", fake_init)
    setup_error_tracking(MonitorConfig(error_tracking=ErrorTrackingConfig(dsn="https://k@sentry.io/1")))
    scrub = captured.get("before_send")
    assert callable(scrub)
    event = {"request": {"headers": {"Authorization": "Bearer x"}},
             "extra": {"password": "p", "note": "keep"}}
    out = scrub(event, {})
    assert out["request"]["headers"]["Authorization"] == "[redacted]"
    assert out["extra"]["password"] == "[redacted]"
    assert out["extra"]["note"] == "keep"
```

- [ ] **Step 2: Implement** `_scrub_event(event, hint)` walking `request.headers`,
`request.data`, `extra`, and `breadcrumbs` values with Task-1's `_is_sensitive`
(import from lexigram.logging.redaction or duplicate minimal set); register via
`sentry_sdk.init(..., before_send=self._scrub_event)`.

- [ ] **Step 3:** package suite green; commit `-m "🔒 security(monitor): scrub sensitive keys before Sentry submission"`.

---

### Task 3: SecretStr sweep

**Files (exact fields):**
- `packages/lexigram-notification/src/lexigram/notification/config.py`: TwilioDriverConfig.auth_token (:31), FCM server_key (:50), APNs apns_auth_key (:73), VAPID vapid_private_key (:99), SMTP password (:287 or nearest), SendGrid api_key (:310)
- `packages/lexigram-web/src/lexigram/web/security/config.py:307` CSRF `secret_key`
- `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:166` `setup_token`
- `packages/lexigram-monitor/src/lexigram/monitor/config.py:372` ErrorTrackingConfig.dsn (+ unwrap at error_tracking.py:83)

**Contract per field:** type becomes `SecretStr | None` (or required SecretStr where non-optional today); add `@field_validator(..., mode="before") def _coerce(v): return SecretStr(v) if isinstance(v, str) else v`; update every internal reader to `.get_secret_value()`; `to_safe_dict`/repr paths already mask SecretStr.

- [ ] **Steps:** one failing repr-leak test per package first (assert `"s3cr3t" not in repr(cfg)` / safe_dict output), then convert fields+readers package by package (notification → web → admin → monitor), running each package's scoped suite between conversions.
- [ ] **Commit(s):** one per package: `-m "🔒 security(<pkg>): SecretStr for <area> credentials"`.

---

## Self-review notes

- Findings 5→T1, 6→T2, 14→T3. Redaction rule ambiguity (token_count) is called out as a decision encoded in tests rather than left open.
- Sweep touches cross-package consumers of these config readers — grep each field name for `.get_secret_value()` gaps during its sub-step.
