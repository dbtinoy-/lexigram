---
title: lexigram-features Troubleshooting
description: Common errors, causes, and fixes
---

## Flag not found

```python
FlagNotFoundError: Feature flag not found: 'my_flag'
```

**Cause:** The flag key does not exist in any registered provider.  
**Fix:** Check that the flag is defined in `initial_flags` or added via `provider.add_flag()`. Verify the provider chain resolves the key.

## Flag evaluation returns wrong value

**Cause:** Stale cache.  
**Fix:** Call `manager.clear_cache()` or `manager.clear_cache_for("flag_name")`. Set `cache_ttl: 0` during development.

## Feature gated path not working

```python
FeatureFlagDisabledError: Feature flag is disabled: 'premium_feature'
```

**Cause:** `@require_flag` raised because the flag is disabled.  
**Fix:** Enable the flag via `manager.enable("premium_feature")` or set it in `initial_flags`.

## Provider error during evaluation

```python
[logged] flag_provider_error flag=my_flag error=...
```

**Cause:** An exception was raised by a flag provider during evaluation.  
**Fix:** Check the provider implementation. The `FlagManager` falls back to `default_enabled` when a provider errors — verify that's the desired behaviour.

## Runtime override not taking effect

**Cause:** The flag is cached with the previous value.  
**Fix:** Call `manager.clear_cache_for(name)` after `manager.enable()` / `manager.disable()`. Or set `cache_ttl` to a lower value.

## Event bus not emitting FlagChangeEvent

**Cause:** No `EventBusProtocol` registered in the container.  
**Fix:** Install and register `lexigram-events`. The feature-flag module works without it — events are a silent no-op when absent.

## FlagEvaluationError raised from provider

**Symptom:** `FlagEvaluationError` is raised (not just logged) when evaluating a flag.

**Cause:** A flag provider raised an unhandled exception during evaluation. The `FlagManager` normally catches provider errors and falls back to `default_enabled`, but if the provider's `get()` method raises a non-`Exception` base type (like `KeyboardInterrupt` or `asyncio.CancelledError`), the error propagates.

**Solution:** Wrap provider logic in try/except to ensure all expected exceptions are caught:

```python
class SafeProvider(AbstractFlagProvider):
    async def get(self, flag_key: str, context: FlagContext | None = None) -> bool | None:
        try:
            return await self._backend.fetch(flag_key)
        except (ConnectionError, TimeoutError, KeyError) as e:
            logger.warning("flag_provider_error", flag=flag_key, error=str(e))
            return None
```

## Environment variable flag prefix mismatch

**Symptom:** Flags set via environment variables (e.g. `LEX_FEATURES__MY_FLAG=true`) are not picked up by `EnvProvider`.

**Cause:** `EnvProvider` uses `flag_env_prefix` (default: `LEX_FEATURE_FLAGS__`) to build environment variable keys. If your variables use a different prefix like `LEX_FEATURES__`, the provider won't find them.

**Solution:** Either align the env vars with the default prefix or override it in config:

```yaml
features:
  flag_env_prefix: "LEX_FEATURES__"
```

```bash
export LEX_FEATURES__MY_FLAG=true
```

## Initial flags not seeded from config

**Symptom:** Flags defined in `initial_flags` config are not available at runtime.

**Cause:** `initial_flags` is a seed for the `LocalProvider` (in-memory provider). If no `LocalProvider` is in the provider chain (e.g. only a remote provider like Redis is configured), the initial flags dict is ignored.

**Solution:** Add `LocalProvider` as the first (fallback) provider in the chain:

```python
manager = FlagManager.with_defaults()
manager.add_provider(LocalProvider(initial_flags={"my_flag": True}))
manager.add_provider(RedisFlagProvider(redis_url="..."))
```

## Flag default value not used when provider returns None

**Symptom:** `manager.is_enabled("unknown_flag")` returns `False` even though `default_enabled` is `True`.

**Cause:** The provider chain returned `None` for the flag key, and the `FlagManager` only applies `default_enabled` when *all* providers return `None`. If even one provider raises an exception, the fallback may be `False` depending on your configuration.

**Solution:** Verify `default_enabled: true` in config and ensure no provider is raising unhandled exceptions. Check which providers are in the chain:

```python
print(manager.providers)  # inspect the chain
result = await manager._evaluate("unknown_flag")
```
