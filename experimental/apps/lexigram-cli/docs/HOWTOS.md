---
title: lexigram-cli How-Tos
description: Task-oriented recipes for the Lexigram CLI
---

## Scaffold a Full-Stack Project

```bash
lexigram new project my-app --template full -d ./workspace
cd ./workspace/my-app
ls src/my_app/
```

The `full` template includes `application.yaml`, `app.py`, modules structure, tests, and `pyproject.toml`.

## Create a New Extension Package

```bash
lexigram new package my-feature -d ./extensions
cd ./extensions/lexigram-my-feature
uv sync
uv run pytest
```

Scaffolds `lexigram-my-feature/` with `pyproject.toml`, `src/lexigram/my_feature/`, `di/provider.py`, and a unit test scaffold.

## List All Available Generators

```bash
lexigram gen list
```

Generators are contributed by installed packages. Each entry shows the generator name and description.

## Generate a Model, Service, and Controller

```bash
lexigram gen model Product
lexigram gen service ProductService
lexigram gen repository ProductRepository
lexigram gen controller ProductController
```

Generated files are placed in the project's `src/` tree, following framework conventions.

## Run Database Migrations

```bash
lexigram db init          # create initial migration
lexigram db migrate -m "add email field"
lexigram db upgrade       # apply pending
lexigram db rollback      # revert last
lexigram db status        # check state
lexigram db list          # show history
```

Requires `lexigram-sql` to be installed in the project.

## Inspect the Runtime

```bash
lexigram inspect providers    # list DI providers
lexigram inspect routes       # show HTTP routes
lexigram inspect health       # run health checks
lexigram inspect container    # show container bindings
```

## Start an Interactive Shell

```bash
lexigram shell                # REPL with app context
lexigram shell --ipython      # use IPython if available
lexigram shell --no-app       # plain Python REPL
```

The context-loaded shell provides `app`, `container`, `config`, `db`, `cache`, and `events`.

## Run Project Checks as a Pre-Commit Gate

```bash
lexigram test                 # run pytest
lexigram lint                 # run ruff
lexigram project typecheck    # run mypy
lexigram project run-all      # all checks
```

## Notes

- Use `--json` flag on any command for machine-readable output
- Generators create files relative to the project root; run from the project directory
- Migration files are timestamped and stored in the project's migrations directory
- The dev server and run command auto-discover `create_app()`; use `module:attr` syntax to override
