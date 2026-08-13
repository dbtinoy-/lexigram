---
title: lexigram-features Configuration
description: Every configuration key for the feature-flag subsystem
---

Config section: `features`  
Env prefix: `LEX_FEATURES__`  
Config model: `FeatureFlagsConfig`

## FeatureFlagsConfig

| Key | Type | Default | Env var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_FEATURES__ENABLED` | Enable the features subsystem |
| `cache_ttl` | `int` | `300` | `LEX_FEATURES__CACHE_TTL` | Cache TTL for flag evaluations (seconds; 0 = disabled) |
| `default_enabled` | `bool` | `False` | `LEX_FEATURES__DEFAULT_ENABLED` | Default when flag not found |
| `flag_env_prefix` | `str` | `"LEX_FLAG_"` | `LEX_FEATURES__FLAG_ENV_PREFIX` | Env prefix for `EnvProvider` |
| `initial_flags` | `dict[str, bool]` | `{}` | `LEX_FEATURES__INITIAL_FLAGS` | Seed flags for `LocalProvider` |

## Example YAML

```yaml
features:
  enabled: true
  cache_ttl: 60
  default_enabled: false
  flag_env_prefix: LEX_FLAG_
  initial_flags:
    new_checkout: true
    dark_mode: false
    experimental_search: true
```

Env var override form:

```bash
export LEX_FEATURES__CACHE_TTL=0
export LEX_FEATURES__INITIAL_FLAGS='{"new_checkout":true}'
```

## Environment variable flags

When using `EnvProvider`, flags are read from environment variables with the configured prefix:

```bash
export LEX_FLAG_NEW_CHECKOUT=true
export LEX_FLAG_DARK_MODE=false
```
