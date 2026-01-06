# lexigram-cli

Command-line interface for the Lexigram Framework.

---

## Overview

The `lexigram` CLI provides project scaffolding, code generation, development tooling, and administrative commands for every stage of the application lifecycle. It uses a contributor-based plugin system so other packages can extend the CLI with new commands and generators.

---


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-cli
# or, as a standalone tool:
uv tool install lexigram-cli
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module

from lexigram.cli import CLIModule
from lexigram.cli.config import CLIConfig

@module(imports=[CLIModule.configure(CLIConfig())])
class AppModule(Module):
    pass

app = Application(modules=[AppModule])
if __name__ == "__main__":
    app.run()
```

Or use the CLI directly:

```bash
# Create a new web API project
lexigram new project my-api --template web-api

# Scaffold a new extension package
lexigram new package my-feature

# Generate a controller
lexigram gen controller UserController --resource User

# Add the database package to an existing project
lexigram add database --driver postgres

# Start the dev server with hot-reload
lexigram dev start
```

## Configuration

> **Zero-config usage:** Call `CLIModule.configure()` with no arguments to use all defaults.

### Option 1 — YAML file

```yaml
# application.yaml
cli:
  default_template: "web-api"
  default_database: "postgres"
  color: true
  verbose: false
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_CLI__DEFAULT_TEMPLATE=web-api
export LEX_CLI__COLOR=true
export LEX_CLI__VERBOSE=false
```

### Option 3 — Python

```python
from lexigram.cli.config import CLIConfig
from lexigram.cli import CLIModule

config = CLIConfig.from_env_profile()
CLIModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `default_template` | `"web-api"` | `LEX_CLI__DEFAULT_TEMPLATE` | Template used by `lexigram new` |
| `default_database` | `"postgres"` | `LEX_CLI__DEFAULT_DATABASE` | Database driver used by scaffolding |
| `color` | `true` | `LEX_CLI__COLOR` | Enable coloured terminal output |
| `verbose` | `false` | `LEX_CLI__VERBOSE` | Print verbose/debug output |

## Key Features

- **Project scaffolding** — `web-api`, `api`, and `full` templates
- **Package generation** — scaffold new `lexigram-*` extension packages
- **Code generators** — 32+ generators (controller, service, model, provider, event, etc.)
- **Contributor system** — extensible plugin architecture for new commands
- **Shell completion** — bash, zsh, and fish completion scripts

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/cli/config.py` | `CLIConfig` configuration dataclass |
| `src/lexigram/cli/module.py` | CLI module assembly |
| `src/lexigram/cli/commands/` | All CLI command implementations |
| `src/lexigram/cli/generators/` | Code generation logic |
| `src/lexigram/cli/registry/` | Registry subsystems |
| `src/lexigram/cli/contributors/` | Plugin contributor system |