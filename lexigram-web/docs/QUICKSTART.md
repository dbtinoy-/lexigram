---
title: lexigram-web Quickstart
description: Install, configure, and run a Lexigram web API in under 5 minutes.
---

:::note
Lexigram is **alpha (0.1.x)** — public APIs may change before 1.0.
:::

## Install

```bash
uv add lexigram-web
```

`lexigram` (core) and `lexigram-contracts` are pulled in automatically.

---

## Minimal Web API

A single-file prototype with the quickstart `app`:

```python
# main.py
from lexigram.web import app, get, singleton


@singleton
class Greeter:
    def hello(self, name: str) -> str:
        return f"Hello, {name}"


@get("/hello/{name}")
async def hello(name: str, greeter: Greeter) -> dict:
    return {"message": greeter.hello(name)}
```

Run with any ASGI server:

```bash
uv run uvicorn main:app
# → http://localhost:8000/hello/world
```

The `app` object is a standard ASGI application. OpenAPI docs are auto-generated at `/docs` (Swagger UI) and `/redoc`.

---

## Production Pattern

Use `Application` + `WebProvider` for explicit control:

```python
# app.py
from lexigram import Application
from lexigram.web import WebProvider


def create_app() -> Application:
    app = Application(name="my-api")
    app.add_provider(WebProvider())
    return app
```

```bash
uv run uvicorn app:create_app --factory
```

---

## Next Steps

- [Your First App](../../docs/lexigram-docs/getting-started/first-app.md) — the full walkthrough with DI, controllers, and `Result` types
- [Guide](./GUIDE.md) — mental model, workflows, best practices
- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Configuration](./CONFIGURATION.md) — every config key
