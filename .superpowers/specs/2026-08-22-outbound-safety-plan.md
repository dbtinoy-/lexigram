# Outbound Request Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the shared HTTPClient's SSRF gate redirect-proof, validate persisted gateway upstream URLs, and settle (or consciously accept) the DNS-rebinding residual.

**Architecture:** HTTPClient disables automatic redirects and follows hops itself, re-running `_assert_url_safe` per hop (pattern proven in webhook sender + ai-mcp web_fetch). Gateway admin actions validate candidate `upstream_base_url` through the same primitive at create/update before persistence. DNS pinning is documented as accepted-residual unless a follow-up requests a custom connector.

**Tech Stack:** aiohttp redirect semantics; existing `lexigram.contracts.security.url_safety.is_safe_url_for_request`.

**Spec:** `.superpowers/specs/spec-security-remediation.md` (findings 4, 8, 9)

## Global Constraints

Same as security-criticals plan (uv, narrow runs, ruff/mypy gates, emoji pathspec commits, regression tests in-commit).

---

### Task 1: Redirect-proof SSRF gate in HTTPClient

**Files:**
- Modify: `packages/lexigram-http/src/lexigram/http/client/http_client.py` (`request()` around lines 255-300)
- Test: `packages/lexigram-http/tests/unit/test_redirect_ssrf.py` (create)

**Interfaces:**
- Consumes: `_assert_url_safe(url)`; session request kwargs.
- Produces: contract — final response is either from a URL that passed `_assert_url_safe`, or an `HTTPSecurityError`-family exception; caller-visible API unchanged except new optional kwarg `max_redirects: int = 5` honored when caller did not pass `allow_redirects`.

- [ ] **Step 1: Failing tests**

Use aiohttp test-server style already present in this package's tests; three cases:
1. Public URL 302 → private IP target ⇒ raises safety error, no second request executed.
2. Public → public hop chain (2 hops) ⇒ returns final body.
3. Caller passes explicit `allow_redirects=False` ⇒ single request, no following.

Sketch:

```python
@pytest.mark.asyncio
async def test_redirect_to_private_blocked(client_factory, redirect_server):
    ...
    with pytest.raises(UnresolvableDependencyError):  # or package's safety error
        await client.get(redirect_server.public_url)
```

Mirror existing test fixtures in `packages/lexigram-http/tests/unit/` rather than inventing harnesses.

- [ ] **Step 2: Red-run**

Expected: case 1 currently FOLLOWS to private and returns 200 → assertion error.

- [ ] **Step 3: Implement**

In `request()` after building `_kwargs`: if caller omitted `allow_redirects`, force False and loop:

```python
        follows_left = max_redirects
        while True:
            await self._assert_url_safe(_url)
            _kwargs["allow_redirects"] = False
            resp_ctx = self._pool._session.request(_method, _url, **_kwargs)
            ...existing execution/circuit handling...
            if resp.status in (301, 302, 303, 307, 308) and follows_left:
                location = resp.headers.get("Location", "")
                if not location:
                    break
                _url = str(resp.url.join(location))
                follows_left -= 1
                # drain+release resp per aiohttp contract, then continue loop
                continue
            break
```

Preserve interceptor/request-context behavior for each hop (rebuild headers per hop as today). Keep circuit-breaker accounting on the original logical call.

- [ ] **Step 4: Package suite green** (`uv run pytest tests -q --no-cov -p no:cacheprovider -m "not integration"` in packages/lexigram-http) + mypy on src.

- [ ] **Step 5: Commit** `-m "🔒 security(http): re-validate SSRF policy across redirect hops"`

---

### Task 2: Validate gateway upstream URLs at admin mutation time

**Files:**
- Modify: `experimental/ai/lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/admin/actions.py:148-187`
- Test: `tests/unit/admin/test_upstream_validation.py` (create; mirror existing admin action test layout)

**Contract:** channel create/update rejects non-`https` scheme and hosts failing `is_safe_url_for_request`; operator allowlist hook `RelayGatewayConfig.upstream_host_allowlist: tuple[str, ...] = ()` (non-empty restricts to listed hosts).

- [ ] **Steps:** failing tests first (http:// scheme rejected; private host rejected; allowlist mismatch rejected; https public accepted); implement via small `_validate_upstream(url, cfg)` helper called before persistence; run package unit suite; commit `-m "🔒 security(relay-gateway): validate persisted upstream URLs"`.

---

### Task 3: DNS-rebinding residual — decision record

- [ ] Add `docs/reference/SECURITY_NOTES.md` section documenting the TOCTOU window (`url_safety.py` resolve-at-check), affected consumers, and the accepted mitigation posture (private-network egress restrictions at deployment layer). No code change without a follow-up decision on pinning connector.

Commit: `-m "📝 docs(security): record DNS-rebinding residual and mitigations"`
