---
title: lexigram-cli Troubleshooting
description: Common CLI errors, their causes, and how to fix them
---

## `lexigram` Command Not Found

**Cause:** The package is not installed or the virtual environment is not activated.

**Solution:**
```bash
uv add lexigram-cli
# or run via uv without installing:
uv run lexigram --help
```

## `ConfigNotFoundError` — Configuration File Not Found

**Exception:** `lexigram.cli.ConfigNotFoundError`

**Cause:** A CLI command that needs project context (`run`, `dev`, `db`, `inspect`, `gen`) was run outside a project directory.

**Solution:**
```bash
# Create an application.yaml in the current directory
lexigram init

# Or run from the project root
cd my-project
```

## `ProviderNotInstalledError` — Provider Not Installed

**Exception:** `lexigram.cli.ProviderNotInstalledError`

**Cause:** A command requires a package that is not installed (e.g., `lexigram-sql` for `db` commands).

**Solution:**
```bash
uv add lexigram-sql    # for database commands
uv add lexigram-web    # for web-related generators
```

## Generator Not Found

**Cause:** The generator's contributing package is not installed.

**Solution:**
```bash
uv add lexigram-web    # or the relevant package
lexigram gen list      # verify it appears
```

## Entry Point Not Detected

**Cause:** `lexigram run` or `lexigram dev` could not find `create_app()` in the project.

**Solution:**
```bash
# Specify the entry point explicitly
lexigram run my_app.app:create_app

# Or ensure your app module defines create_app() or 'app' at module level
```

## Server Backend Not Available

**Cause:** The preferred server backend (Granian, Uvicorn) is not installed.

**Solution:**
```bash
uv add uvicorn
# or
uv add granian
```

The CLI auto-detects available backends and falls back gracefully.

## CLI config TOML parse error

```
Error: Failed to parse config file at ~/.config/lexigram/config.toml
```

**Cause:** The TOML config file contains syntax errors — missing quotes, invalid tables, or trailing commas.

**Fix:** Validate the TOML file:

```bash
uv run python -c "import tomllib; tomllib.load(open('~/.config/lexigram/config.toml', 'rb'))"
```

The default config is created by `ConfigManager.save()` and should be valid. If the file is corrupted, delete it and let the CLI recreate it:

```bash
rm ~/.config/lexigram/config.toml
```

## Generator fails with package import error

```
Error: Generator 'web-api' failed: No module named 'lexigram-web'
```

**Cause:** The generator's contributing package (`lexigram-web`, etc.) is not installed. Generators are discovered via entry points and may declare optional dependencies.

**Fix:** Install the required package:

```bash
uv add lexigram-web
lexigram gen list  # verify it appears
```

## Server backend detection fails

```
Warning: No ASGI server backend found. Install uvicorn or granian.
```

**Cause:** Neither `uvicorn` nor `granian` is installed in the current environment. `lexigram run` and `lexigram dev` require an ASGI server to serve the application.

**Fix:** Install a server backend:

```bash
uv add uvicorn
# or for better performance:
uv add granian
```

The CLI prefers Granian when available and falls back to Uvicorn.

## Output shows raw ANSI color codes

**Symptom:** Terminal output contains literal escape sequences like `[32m` instead of colored text.

**Cause:** The terminal does not support ANSI color codes (pipe/redirect, CI output, or `NO_COLOR` environment). The CLI detects terminal capabilities but may not disable color when output is piped.

**Fix:** Disable colors explicitly:

```bash
lexigram --no-color <command>
# or
LEX_CLI__COLOR=false lexigram <command>
```

For scripted output, use `--json` for machine-readable results:

```bash
lexigram system info --json
```
