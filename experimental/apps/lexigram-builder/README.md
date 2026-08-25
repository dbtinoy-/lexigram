# lexigram-builder

Visual node-canvas application builder: drag framework-shaped nodes onto a
canvas, wire typed edges, and generate a **real standalone Lexigram
project** (one-way codegen; the canvas graph is the source of truth).

Part of the Lexigraph Framework monorepo (`experimental/apps/`). Design and
plan live in `.superpowers/specs/2026-08-25-lexigram-builder-design.md`.

## Status

v1 scaffold — CRUD API vertical. Palette: `AppSettings`, `Entity`, `Route`.

## Run (server only, so far)

```bash
uv sync
uv run pytest experimental/apps/lexigram-builder/tests -m "not integration"
```

Server entry point arrives with Task 5; the canvas UI with Task 7.
