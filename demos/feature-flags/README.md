# Feature Flags — Release Control Lab

A focused, browser-first example of **Lexigram FeatureFlagsModule**. It uses
one domain module plus `WebModule`, no external services, and deterministic
in-memory state.

## What to try

1. Evaluate the same user twice and see deterministic percentage and variant
   decisions.
2. Switch `free` / `pro` to exercise a user-attribute rule.
3. Force a flag on or off, then clear the override.
4. Inspect the package-owned override audit trail and clear the TTL cache.

## Lexigram surface

- `FeatureFlagsModule.configure()` and DI-injected `FlagManager`
- `FlagContext` with user IDs and attributes
- percentage rollout, variant assignment, and user-attribute evaluation
- runtime overrides, TTL caching, cache invalidation, and audit history
- `WebModule` controllers with a standalone server entry point

## Run

```bash
cd demos/feature-flags
PYTHONPATH=src uv run python -m release_control
```

The hub embeds this console at `/demos/feature-flags/`.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/flags` | Evaluate all flags for a user context |
| POST | `/api/flags/evaluate` | Evaluate one flag |
| POST | `/api/flags/override` | Force a runtime value |
| POST | `/api/flags/override/clear` | Return to provider control |
| POST | `/api/flags/cache/clear` | Flush manager TTL results |
| GET | `/api/flags/audit` | Inspect override history |
