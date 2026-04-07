---
title: lexigram-graphql Troubleshooting
description: Common errors, causes, and fixes
---

## Query too deep

```python
QueryTooDeepError: Query exceeds maximum depth
```

**Cause:** The query's nesting depth exceeds `DepthLimitConfig.max_depth` (default: 10).  
**Fix:** Increase `max_depth` in config, or restructure the query to be shallower.

## Query too complex

```python
QueryTooComplexError: Query exceeds complexity limit
```

**Cause:** The complexity score exceeds `ComplexityConfig.max_complexity` (default: 1000).  
**Fix:** Increase `max_complexity`, or reduce the number of fields / list sizes in the query.

## Rate limited

```python
RateLimitError: Rate limit exceeded
```

**Cause:** More than `rate_limit.requests_per_minute` requests.  
**Fix:** Increase the limit in `RateLimitConfig`, or implement client-side throttling.

## Authentication required

```python
AuthenticationError: Authentication required
```

**Cause:** No authenticated user in the execution context.  
**Fix:** Wire `lexigram-auth` to authenticate requests before they reach the GraphQL controller. Add `@strawberry.field(permission_classes=[IsAuthenticated])` to protected fields.

## Executor not available

```python
RuntimeError: GraphQLExecutorProtocol not initialised.
```

**Cause:** `GraphQLProvider.boot()` hasn't been called — the executor is `None`.  
**Fix:** Ensure `app.start()` or `Application.boot()` is called before resolving the executor.

## Schema diff shows unexpected breaking changes

```text
WARNING  graphql.schema_diff.breaking_removal type_name=OldType
```

**Cause:** The running schema removed a type that exists in the baseline SDL file.  
**Fix:** Restore the removed type or update the baseline SDL to reflect the intentional change.

## Resolver raises `ResolverError`

```python
ResolverError: Field 'user' raised an error: 'NoneType' object has no attribute 'id'
```

**Cause:** A resolver returned `None` or raised an unhandled exception during execution. The error propagates as a `ResolverError` with the internal exception as context.

**Fix:** Ensure resolvers handle `None` returns gracefully:

```python
@strawberry.field
async def user(self, id: str) -> User | None:
    result = await self.user_service.find(id)
    if result.is_err():
        return None  # field resolves to null instead of crashing
    return result.unwrap()
```

Use `ErrorConfig(mask_errors=True)` in production to prevent leaking internal details to clients.

## Invalid input rejected by `InputGraphQLError`

```python
InputGraphQLError: Variable '$email' got invalid value 'not-an-email'
```

**Cause:** The client sent input that doesn't match the expected GraphQL type — wrong enum value, invalid number format, or type mismatch.

**Fix:** Validate client input on the frontend before sending. The error message includes the expected type and the actual value:

```json
{
  "errors": [{"message": "Variable '$email' got invalid value...", "extensions": {"code": "BAD_USER_INPUT"}}]
}
```

## `GraphQLTimeoutError` when executing complex queries

```python
GraphQLTimeoutError: Execution timed out after 30.0s
```

**Cause:** A resolver performed a slow I/O operation (database query, external API call) that exceeded the execution timeout.

**Fix:** Increase the timeout or optimize the slow resolver:

```yaml
graphql:
  execution:
    timeout: 60.0
```

For long-running operations, consider using `@strawberry.field` with a subscription pattern or returning a job ID for polling.

## Subscription disconnects unexpectedly

**Symptom:** WebSocket subscription drops after a few minutes with no error in the application logs.

**Cause:** The subscription's `keepalive_interval` is too long, causing proxies or load balancers to time out the idle connection. Or `connection_timeout` was exceeded during the initial WebSocket handshake.

**Fix:** Increase keepalive frequency and tune timeouts:

```yaml
graphql:
  subscriptions:
    keepalive_interval: 15  # seconds (default: 30)
    connection_timeout: 120  # seconds (default: 60)
```

Also verify that your reverse proxy (nginx, Cloudflare) is configured for long-lived WebSocket connections.
