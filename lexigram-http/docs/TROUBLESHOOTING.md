---
title: lexigram-http Troubleshooting
description: Common errors, causes, and fixes
---

## Connection refused

```python
HTTPConnectionError: Cannot connect to host api.example.com:443
```

**Cause:** The remote host is unreachable or refused the connection.  
**Fix:** Verify the URL and network connectivity. Check if the remote service is running. If using a proxy, verify `proxy` config and `trust_env` setting.

## Timeout

```python
HTTPTimeoutError: Request timed out after 30.0s
```

**Cause:** The connection or response took longer than the configured timeout.  
**Fix:** Increase `pool.timeout` in config, or optimise the remote endpoint. Check for slow DNS resolution — reduce `pool.ttl_dns_cache` if DNS records change frequently.

## Circuit breaker open

```python
HTTPCircuitOpenError: Circuit breaker is open
```

**Cause:** Too many requests to a backend have failed; the circuit breaker is preventing further requests.  
**Fix:** Wait for the circuit breaker to half-open, or check the health of the downstream service. Requires `lexigram-resilience` to be registered.

## Retries exhausted

```python
HTTPRetryExhaustedError: All 3 retry attempts exhausted
```

**Cause:** All retry attempts to a backend failed.  
**Fix:** Check the downstream service health. Consider increasing `max_retries` or `max_delay` in the retry policy, but prefer fixing the backend.

## Interceptor failure

```python
HTTPInterceptorError: Request interceptor failed
```

**Cause:** An interceptor raised an exception during request or response processing.  
**Fix:** Check the interceptor implementation. Ensure interceptors are pure transformations that don't make network calls.

## Client resolves before boot

```python
RuntimeError: HTTPProvider has not been booted.
```

**Cause:** `HTTPClient` was resolved from the container before the provider's `boot()` method ran.  
**Fix:** Ensure `app.start()` is called before resolving the client. Don't resolve services during `register()`.

## SSL certificate verification failure

```python
HTTPConnectionError: Cannot connect to host api.example.com:443 ssl:True [SSLCertVerificationError]
```

**Cause:** The remote server's SSL certificate is self-signed, expired, or doesn't match the hostname. The client verifies certificates by default.

**Fix:** For development against internal services with self-signed certs, disable verification in config:

```python
from lexigram.http.config import HTTPClientConfig

config = HTTPClientConfig()
config.pool.verify_ssl = False  # development only
```

Or set the `SSL_CERT_FILE` environment variable to a custom CA bundle:

```bash
export SSL_CERT_FILE=/path/to/custom-ca-bundle.crt
```

## Proxy authentication required

```python
HTTPStatusError: HTTP 407: Proxy Authentication Required
```

**Cause:** The configured proxy requires authentication, but no credentials were provided in the proxy URL.

**Fix:** Include credentials in the proxy URL:

```yaml
http:
  proxy: "http://user:password@proxy.example.com:8080"
```

If using environment proxies (`trust_env: true`), set `HTTP_PROXY` and `HTTPS_PROXY` with credentials:

```bash
export HTTPS_PROXY="http://user:password@proxy.example.com:8080"
```

## Connection pool exhausted

```python
HTTPConnectionError: Cannot connect to host — connection pool exhausted
```

**Cause:** All connections in the pool are in use and the `max_connections` limit (default: 10) was reached. New requests queue up and eventually time out.

**Fix:** Increase pool capacity or optimize connection usage:

```yaml
http:
  pool:
    max_connections: 50
    max_connections_per_host: 20
    max_keepalive_connections: 10
    timeout: 60.0
```

For long-lived requests, ensure the client is reused (not recreated per request):

```python
# Reuse the same client instance
client = await container.resolve(HTTPClient)
```

## Cookie jar not persisting across requests

**Symptom:** Cookies set by one request are not sent with subsequent requests to the same domain.

**Cause:** `cookie_jar` is disabled in config, or the client is being recreated between requests.

**Fix:** Enable the cookie jar:

```yaml
http:
  cookie_jar: true
```

And ensure you're using the same `HTTPClient` instance for all requests in a session. Each new client creates an empty cookie jar.
