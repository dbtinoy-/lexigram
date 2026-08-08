# Demos

In-repo demo applications built on the Lexigram framework. Each demo runs
against the editable framework packages in this repository and is gated in CI
with the same checks as the framework (format, lint, mypy, tests), so the
demos double as living integration surfaces.

## fullstack-demo

**shorts-creator** — an end-to-end short-video reel generator: LLM script
generation (hook / message / metaphor / conclusion), Chatterbox TTS narration
with per-line prosody presets, Whisper word timings, mood-keyed stock
background segments, caption + hook overlay rendering, and ffmpeg compose.

```sh
cd fullstack-demo
uv sync --locked
uv run python -m shorts_creator.main    # serve on :8080
# or: uv run uvicorn asgi_app:app --port 8080
```

Verify it like CI does:

```sh
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy
uv run pytest -q -m "not integration"
```

See [`fullstack-demo/README.md`](./fullstack-demo/README.md) for prerequisites
(ffmpeg, stock API keys, the Chatterbox TTS venv) and the architecture notes in
[`fullstack-demo/ARCHITECTURE.md`](./fullstack-demo/ARCHITECTURE.md).