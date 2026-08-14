---
title: lexigram-cli Configuration
description: CLIConfig options, environment variables, and YAML setup
---

## Overview

`CLIConfig` extends `BaseConfig` from `lexigram.config` with a `config_section = "cli"`. It reads from the `[cli]` section of `application.yaml` or environment variables prefixed with `LEX_CLI__`.

```python
from lexigram.cli import CLIConfig

# From YAML (reads [cli] section)
config = CLIConfig.from_yaml("application.yaml")

# Defaults
config = CLIConfig()
```

## Options

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `default_template` | `str` | `"web-api"` | `LEX_CLI__DEFAULT_TEMPLATE` | Project template used by `lexigram new project` |
| `default_database` | `str` | `"postgres"` | `LEX_CLI__DEFAULT_DATABASE` | Default database driver for scaffolding |
| `color` | `bool` | `True` | `LEX_CLI__COLOR` | Enable coloured terminal output |
| `verbose` | `bool` | `False` | `LEX_CLI__VERBOSE` | Print verbose/debug output |

## YAML Example

```yaml
# application.yaml
cli:
  default_template: "full"
  default_database: "sqlite"
  color: true
  verbose: false
```

## Environment Variables

```bash
export LEX_CLI__DEFAULT_TEMPLATE=full
export LEX_CLI__DEFAULT_DATABASE=sqlite
export LEX_CLI__COLOR=true
export LEX_CLI__VERBOSE=true
```

Environment variable overrides take precedence over values in `application.yaml`.

## Best Practices

- Use `application.yaml` for project-wide defaults checked into version control
- Use environment variables for CI/CD and per-deployment overrides
- Set `LEX_CLI__VERBOSE=true` during troubleshooting for detailed output
