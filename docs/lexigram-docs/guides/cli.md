---
title: "The lexigram CLI"
description: "Scaffold projects, run servers, manage migrations, and inspect your app from one command."
---

`lexigram-cli` ships the `lexigram` command — the day-to-day driver for every Lexigram project. It scaffolds new apps, runs the development server, drives database migrations, manages configuration, and exposes a plugin surface that lets installed extensions contribute their own subcommands.

For the full command reference, see the [`lexigram-cli` package docs](/packages/lexigram-cli/).

---

## 1. Install & Verify

```bash
pip install lexigram-cli       # or: uv add lexigram-cli
lexigram --version             # → lexigram <version>
lexigram --help                # full command list
```

The CLI is also pulled in transitively by most projects, so `uv sync` from a generated project is usually enough.

Global flags work on every subcommand:

| Flag | Effect |
| --- | --- |
| `--json` | machine-readable output where supported |
| `--quiet`, `-q` | suppress non-essential output |
| `--debug` | print tracebacks on error |
| `--no-color` | disable ANSI colour |
| `--config`, `-c` | path to `application.yaml` |

---

## 2. Scaffolding a New Project

`lexigram new project` renders a project template from `lexigram-cli/templates/project/`:

```bash
lexigram new project my-app                          # default template: web-api
lexigram new project my-app --template api           # JSON API only
lexigram new project my-app --template full          # web + db + auth + cache
lexigram new project my-app --interactive            # prompt for template/db/auth
```

| Flag | Default | Notes |
| --- | --- | --- |
| `--template`, `-t` | `web-api` | one of `api`, `web-api`, `full` |
| `--directory`, `-d` | `.` | parent directory for the new project |
| `--interactive`, `-i` | `false` | prompts for template, database (`sqlite`/`postgres`/`none`), and auth (`none`/`jwt`) |

To scaffold a reusable extension package instead of an application:

```bash
lexigram new package my-feature        # → lexigram-my-feature/ with src/ + provider stub
```

`lexigram init` writes a minimal `application.yaml` into an *existing* directory — useful when adopting Lexigram in a project that already has a `pyproject.toml`:

```bash
lexigram init --full          # full config (web/db/auth/cache/monitor sections)
lexigram init --minimal       # just project + logging (default)
lexigram init --force         # overwrite an existing application.yaml
```

See [Project Structure](/getting-started/project-structure/) for what the templates lay down.

---

## 3. Running Locally

Two commands launch your app — pick by intent:

```bash
lexigram run                  # production-shaped: --host 127.0.0.1, --reload on
lexigram dev                  # development server, --reload on, LEX_ENV=development
```

Both auto-detect your entry point (`src/main.py`, `create_app`, etc.) using `discover_entry_point` and pick the best available server backend (prefers `granian` → `uvicorn`, falls back to `hypercorn`).

`lexigram run` flags:

| Flag | Default | Notes |
| --- | --- | --- |
| `target` (positional) | auto-detected | `module:attr`, e.g. `my_app.app:create_app` |
| `--host`, `-h` | `127.0.0.1` | bind address |
| `--port`, `-p` | `8000` | bind port |
| `--reload/--no-reload` | `true` | hot reload |
| `--workers`, `-w` | `1` | worker processes |
| `--profile` | none | sets `LEX_PROFILE` for the run |
| `--server` | auto | `uvicorn`, `granian`, or `hypercorn` |
| `--mcp-port` | none | also serve MCP (SSE) on this port |

`lexigram dev` accepts `--entry`, `--host`, `--port`, `--reload/--no-reload`, `--env`, `--server`. For production, use `lexigram dev start` (binds `0.0.0.0`, no reload, takes `--workers`) or invoke an ASGI server directly — see [Deployment](/guides/deployment/).

:::note
The reloader watches `.py` files. Changes to `application.yaml` require a manual restart.
:::

---

## 4. Database Migrations

`lexigram db` wraps `lexigram-sql`'s migration runner. The most common flow:

```bash
lexigram db init migrations              # create migrations/ directory
lexigram db create add_users_table       # new empty migration file
lexigram db upgrade                      # apply pending migrations
lexigram db status                       # show current version + pending
lexigram db history --limit 20           # last N applied migrations
lexigram db downgrade                    # roll back the most recent
lexigram db downgrade 0003_seed          # roll back to a specific version
```

Inspection and maintenance:

```bash
lexigram db inspect                      # list tables + columns
lexigram db inspect --table users        # one table's columns + types
lexigram db shell                        # open psql / mysql / sqlite3 client
lexigram db validate                     # check applied migrations have files
lexigram db reset --force                # drop & re-migrate (SQLite-optimized)
lexigram db backup --output dump.sql
lexigram db restore dump.sql --force
```

Seed scripts in `seeds/*.py` (each exposing a `run(provider)` function) are applied by `lexigram db seed` or as part of `lexigram db reset --seed`.

All `db` commands read `DATABASE_URL` from the environment (default `sqlite:///./dev.db`). When `lexigram-sql` is installed, the runner is resolved through the DI container so connection pooling and observability hooks are active.

See the [Database guide](/guides/database/) for the repository pattern these migrations support.

---

## 5. Inspecting & Diagnosing

```bash
lexigram list                            # all available commands, grouped
lexigram list --group Database
lexigram version --all                   # versions of every installed lexigram-* package
lexigram system info                     # Python version, platform, config path
lexigram system health                   # project + contributor health checks
lexigram system doctor --fix             # diagnostics with auto-fix hints
lexigram system providers                # provider sections in application.yaml
```

Installed extensions register CLI **contributors** — discover them with:

```bash
lexigram contrib list                    # all contributors + their contributions
lexigram contrib inspect sql             # generators/commands/health checks for one
lexigram contrib check                   # verify every contributor loads
```

Code generation routes through contributors as well:

```bash
lexigram gen list                        # all discovered generators
lexigram gen provider MyProvider         # core generator: scaffolds a provider class
```

---

## 6. Configuration

The CLI looks for `application.yaml` in the current directory (and walks up to find one). Override with `--config /path/to/app.yaml`.

Profiles are environment-driven — set `LEX_PROFILE=production` and a matching `application.production.yaml` is overlaid on the base config. Any value can be overridden by a `LEX_`-prefixed env var with `__` for nesting:

```bash
export LEX_PROFILE=staging
export LEX_SQL__BACKEND__URL=postgresql+asyncpg://...
```

Useful config commands:

```bash
lexigram config show                     # current resolved config (secrets masked)
lexigram config show --reveal-secrets    # unmasked
lexigram config validate                 # schema + cross-field validation
lexigram config doctor --env production  # environment-specific diagnostics
lexigram config env                      # ${VAR} references and whether they're set
lexigram config env --missing            # exit 1 if any are unset
lexigram config env-example              # generate .env.example from config
lexigram config diff -c application.production.yaml
lexigram config schema                   # dump the JSON schema
```

See [Configuration](/getting-started/configuration/) and [YAML Configuration](/fundamentals/yaml-configuration/) for the full layering rules.

---

## 7. Adding Providers & Shell Completion

```bash
lexigram add database                    # add lexigram-sql + db: section to YAML
lexigram add auth                        # add lexigram-auth + auth: section
```

The `add` command edits `pyproject.toml` (via `uv add` when available) and patches `application.yaml` with the provider's default config block.

Generate shell completion:

```bash
lexigram completion --shell bash         # also: zsh, fish, powershell
eval "$(lexigram completion --shell zsh)"
```

---

## Next Steps

- [Your First App](/getting-started/first-app/) — the 60-second walkthrough using `lexigram new` and `lexigram run`
- [Database & Persistence](/guides/database/) — the repository pattern these migrations feed
- [Deployment & Infrastructure](/guides/deployment/) — running `lexigram` in production
- [`lexigram-cli` package](/packages/lexigram-cli/) — full flag-by-flag reference and the contributor API
