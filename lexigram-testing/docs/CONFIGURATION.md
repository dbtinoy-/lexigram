---
title: lexigram-testing Configuration
description: TestingConfig options, environment variables, and YAML setup
---

## Overview

`TestingConfig` extends `BaseConfig` from `lexigram.config` with environment prefix `LEX_TESTING__`. It controls test environment behavior.

```python
from lexigram.testing.config import TestingConfig

# Defaults
config = TestingConfig()

# From YAML
config = TestingConfig.from_yaml("application.yaml")
```

## Options

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_TESTING__ENABLED` | Whether testing module is enabled |
| `db_reuse` | `bool` | `True` | `LEX_TESTING__DB_REUSE` | Reuse test databases between tests |
| `mock_external_services` | `bool` | `True` | `LEX_TESTING__MOCK_EXTERNAL_SERVICES` | Mock external service calls |
| `cleanup_temp_files` | `bool` | `True` | `LEX_TESTING__CLEANUP_TEMP_FILES` | Clean up temporary files after tests |

## YAML Example

```yaml
# application.yaml
testing:
  enabled: true
  db_reuse: true
  mock_external_services: false
  cleanup_temp_files: false
```

## Environment Variables

```bash
export LEX_TESTING__ENABLED=true
export LEX_TESTING__DB_REUSE=false
export LEX_TESTING__MOCK_EXTERNAL_SERVICES=false
```

## Best Practices

- Use `mock_external_services: false` in integration test environments where real services are available
- Disable `cleanup_temp_files` during debugging to inspect generated artifacts
- Override via environment variables in CI without modifying `application.yaml`
