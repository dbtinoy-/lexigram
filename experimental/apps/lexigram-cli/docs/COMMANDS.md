---
title: lexigram-cli Commands
description: Complete command reference for `lexigram` CLI — every command with arguments, flags, and examples.
---

> **Alpha (0.1.x)** — MIT licensed. Commands and flags may change before 1.0.

## Overview

The `lexigram` CLI is the primary developer tool for scaffolding, running, and managing Lexigram projects. Commands are organised into categories.

## Built-in commands

### `lexigram new`

Scaffold a new project or package.

```
lexigram new project <name> [--template web-api] [--structure structured] [--directory .]
lexigram new module <name> [--directory .]
lexigram new package <name> [--output-dir packages/]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--template`, `-t` | `web-api` | Project template (`minimal`, `api`, `web-api`, `graphql`, `worker`, `full`, `fullstack`) |
| `--structure`, `-s` | `structured` | Project structure (`minimal` single-package, `structured` component packages, `modular` bounded contexts) |
| `--directory`, `-d` | `.` | Output directory |

**Examples:**

```bash
lexigram new project my-api --template web-api --structure structured
lexigram new project my-app --template api --structure minimal
lexigram new project my-platform --template full --structure modular
```

`lexigram new module <name>` adds a bounded context to a modular project
(`src/<app>/modules/<name>/` with a `@module` boundary, `protocols.py`,
`provider.py` and `services.py`, registered in `modules/__init__.py`).

`lexigram gen <generator> <name> --module <feature>` writes module-local
components into the matching bounded context; cross-cutting generators
(`errors`, `filters`, `health`, `schema`, ...) write into `shared/`.

### `lexigram run`

Smart runner — auto-detects `create_app()` factory and starts the ASGI server.

```
lexigram run [target] [--host 0.0.0.0] [--port 8000] [--server uvicorn]
```

| Flag | Default | Description |
|------|---------|-------------|
| `target` | Auto-detected | `module:attr` factory path |
| `--host`, `-h` | `0.0.0.0` | Bind address |
| `--port`, `-p` | `8000` | Port |
| `--server` | Auto-detected | Server backend (`uvicorn`, `hypercorn`, `granian`) |

**Example:** `lexigram run my_app.app:create_app --port 8080`

### `lexigram dev`

Development server with hot reload.

```
lexigram dev [--entry src/main.py] [--host 127.0.0.1] [--port 8000] [--reload] [--env development]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--entry` | Auto-detected | Entry point file |
| `--reload/--no-reload` | `True` | Hot reload on file changes |
| `--env` | `development` | Environment profile |

**Example:** `lexigram dev --entry app.py --port 9000 --no-reload`

### `lexigram db`

Database management commands.

```
lexigram db init [--reset] [--seed]
lexigram db migrate [--name <migration>] [--auto]
lexigram db seed [--file seeds.py]
lexigram db shell
```

### `lexigram gen`

Code generation commands.

```
lexigram gen provider <name> [--output src/providers/]
lexigram gen module <name> [--output src/modules/]
lexigram gen migration [--auto-detect]
```

### `lexigram inspect`

Inspect runtime state of a running application or configuration.

```
lexigram inspect providers [--json]
lexigram inspect config [--section <section>]
lexigram inspect routes
lexigram inspect health
```

| Flag | Description |
|------|-------------|
| `--json` | Output as JSON |
| `--section` | Filter config to a specific section |

### `lexigram shell`

Open an interactive Python REPL with the Lexigram application loaded.

```
lexigram shell [target]
```

### `lexigram init`

Initialize Lexigram in an existing project.

```
lexigram init [--force]
```

Creates `application.yaml`, project scaffold, and optional `pyproject.toml` updates.

### `lexigram add`

Add a provider or extension to the project.

```
lexigram add <package> [--version <version>]
lexigram add provider <name>
```

### `lexigram config`

Configuration management.

```
lexigram config view [--section <section>]
lexigram config validate [--file application.yaml]
```

### `lexigram contrib`

Discover and inspect installed contributors (plugins).

```
lexigram contrib list [--json]
lexigram contrib info <name>
```

| Flag | Description |
|------|-------------|
| `--json` | Machine-readable output |

### `lexigram project`

Project management utilities.

```
lexigram project test [path] [--coverage] [--verbose] [--runner pytest]
lexigram project lint [path] [--fix] [--check]
lexigram project routes
```

### `lexigram system`

System information and diagnostics.

```
lexigram system info
lexigram system diagnostics
lexigram system check
```

### `lexigram version`

Show framework and package versions.

```
lexigram version [--all]
```

| Flag | Description |
|------|-------------|
| `--all` | List versions of all installed Lexigram packages |

### `lexigram list`

List all available commands.

```
lexigram list [--group <group>] [--json]
```

| Flag | Description |
|------|-------------|
| `--group`, `-g` | Filter by category |
| `--json` | Machine-readable output |

### `lexigram completion`

Generate shell completion script.

```
lexigram completion --shell <bash|zsh|fish|powershell>
```

Install with: `eval "$(lexigram completion --shell bash)"`

### `lexigram test`

Run project tests (delegates to `lexigram project test`).

```
lexigram test [path] [--coverage] [--verbose]
```

### `lexigram lint`

Run project linting (delegates to `lexigram project lint`).

```
lexigram lint [path] [--fix]
```

### `lexigram events`

Event schema management.

```
lexigram events schema validate
lexigram events schema migrate
```

## Plugin/contributor commands

Packages can register commands via the `lexigram.cli.commands` entry point. Contributor commands appear under their own category in `lexigram list`. Register in `pyproject.toml`:

```toml
[project.entry-points."lexigram.cli.commands"]
my_contrib = "my_package.cli:app"
```

## See also

- `CLIModule` — DI integration for CLI commands
- `CommandRegistry` — programmatic command registration
- `ContributorRuntime` — plugin discovery at runtime
- `PUBLIC_PACKAGE_CLI_MATRIX.md` — per-package command ownership
