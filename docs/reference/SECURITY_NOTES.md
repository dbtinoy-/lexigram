# Security Notes — Accepted Residual Risks

Living record of security decisions where a hardening option was evaluated
and consciously deferred, with the mitigation posture that makes the
deferral acceptable. Review on any architecture change to the named
components.

---

## DNS rebinding in `is_safe_url_for_request` (2026-08-22)

**Primitive:** `lexigram-contracts/security/url_safety.py::is_safe_url_for_request`
resolves the hostname at *check* time via `getaddrinfo` and rejects when any
resolved address is private/reserved. The actual connection is made later by
aiohttp/httpx, which re-resolves DNS independently — an attacker controlling
DNS with a short TTL can answer the check with a public IP and the connect
with `127.0.0.1`/RFC1918.

**Affected consumers:**

- `packages/lexigram-http` `HTTPClient._assert_url_safe` (all outbound calls;
  redirect hops re-validated as of this change)
- `packages/lexigram-webhook` subscription/delivery URLs
- relay-gateway channel upstreams (boundary-IP literal check only; see
  `_validate_upstream_url`)

**Why deferred:** full mitigation requires pinning the validated IP at the
connection layer (custom aiohttp connector overriding `resolve()`), which
touches every consumer's transport setup and interacts with proxies, TLS SNI,
and connection pooling.

**Accepted mitigations:**

1. Deployment-level egress policy: services making outbound calls run with
   network rules that block RFC1918/link-local/metadata endpoints anyway.
2. Webhook senders disable automatic redirects and re-validate per hop.
3. Cloud-metadata exposure is bounded by IMDSv2-style hop limits where
   available on the host.

**Trigger for revisit:** any feature that lets *non-operator* users supply
URLs fetched server-side, or removal of deployment egress restrictions.
At that point implement a pinning connector
(`aiohttp.TCPConnector(resolver=PinningResolver)` that caches the checked
addresses) in `lexigram-http` and route all consumers through it.
