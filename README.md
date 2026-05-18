# lexigram

*async-first DI/IoC framework for python — one container, no glue code.*

[![PyPI version](https://img.shields.io/pypi/v/lexigram?color=%2334D058&label=pypi%20package)](https://pypi.org/project/lexigram/)
[![Python versions](https://img.shields.io/pypi/pyversions/lexigram?color=%2334D058)](https://pypi.org/project/lexigram/)
[![License](https://img.shields.io/pypi/l/lexigram?color=%2334D058)](https://github.com/dbtinoy-/lexigram/blob/main/LICENSE)

![Lexigram demo](lexigram/docs/gifs/hero/lexigram-hero.gif)

hey — wanna ship a real app this weekend?

Lexigram is a python framework built around one idea: everything you need is already wired together. Modules register providers, providers bind contracts, and the container resolves the rest — so web, sql, cache, auth, queues, events, and the whole async backend plug in without glue code, without 200-line config files. It's async-native end to end, and every package talks through contracts, so swapping an implementation never ripples. Pick a few packages, boot the application, ship the thing.

- **wired, not glued.** providers, modules, controllers — one container, one boot call.
- **async, end to end.** the container, the modules, the controllers — concurrency-safe by construction.
- **contracts everywhere.** every package talks through protocols, so swapping an implementation never ripples.
- **swappable backends.** in-memory, redis, sqlite, postgres — the same contract, a config change away.

→ full docs at [docs.lexigram.dev](https://docs.lexigram.dev)

## install

```bash
uv add lexigram
pip install lexigram
# want the AI layer too? `uv add "lexigram[ai]"`
```

```text
HOOK    agents · llms · rag · mcp · memory
CORE    web · sql · cache · auth · queue · events
TRUST   di · contracts · modules · async
```

## 60 seconds, end to end

```python
import asyncio

from lexigram import Application
from lexigram.web import Controller, get, WebModule


class HelloController(Controller):
    @get("/hello")
    async def hello(self, name: str = "world") -> dict:
        return {"message": f"hello, {name}"}


async def main():
    async with Application.boot(modules=[
        WebModule.configure(controllers=[HelloController], port=8000),
    ]):
        await asyncio.Event().wait()


asyncio.run(main())
```

→ http://localhost:8000/hello?name=lexigram

what just happened?

- `Application.boot` assembled the web module into one container and started it.
- `WebModule.configure(...)` registered the controller — no router setup, no middleware boilerplate.
- `HelloController` is a plain typed class; `/hello` maps query params to arguments.

## what's in the box

this repo ships the main ecosystem — the core, the backend, the contracts:

- **`lexigram`** — the core, the container, the boot lifecycle
- **`lexigram-web`** — async routing and controllers
- **`lexigram-sql`** — sqlalchemy, already wired
- **`lexigram-cache`** — redis and in-memory, one contract
- **`lexigram-vector`** / **`lexigram-graph`** — storage for the ai layer
- plus auth, events, queue, tasks, http, resilience, storage, search, notification, monitor, webhook, tenancy, features, audit, graphql, nosql, workflow, and testing

the AI family — agents, llms, rag, memory, skills, mcp, session, workers, observability, feedback, and the guard / governance / evaluation / prompt / relay suite — lives in [lexigram-ai-experimental](https://github.com/dbtinoy-/lexigram-ai-experimental). multimedia (tts, music, image, video, beat, interpolate, upscale) lives in [lexigram-multimedia-experimental](https://github.com/dbtinoy-/lexigram-multimedia-experimental). same modules, same container, same rules — their own repos and cadence.

the full list — including notification, queue, events, auth, observability, and more — lives in the [docs ecosystem](https://docs.lexigram.dev/ecosystem/).

## early on purpose

Lexigram is in 0.1 — which means you can still change it. APIs may shift before 1.0, so pin your versions, and tell us what feels wrong. Shaping a framework is more fun when it's still soft.

→ [github.com/dbtinoy-/lexigram/issues](https://github.com/dbtinoy-/lexigram/issues)

## why it grows with you

- **contracts.** every package talks through protocols, so swapping the implementation never ripples.
- **providers.** lifecycle and wiring live in one place, so boot order is explicit and tests are trivial.
- **async, end to end.** the container, the modules, the controllers — concurrency-safe by construction.

## pointers

- full docs → [docs.lexigram.dev](https://docs.lexigram.dev)
- skills for AI coding agents → [lexigram-skills](https://github.com/dbtinoy-/lexigram-framework-skills)
- contributing → [CONTRIBUTING.md](./CONTRIBUTING.md)
- security → [SECURITY.md](./SECURITY.md)
- license → [LICENSE](./LICENSE)

## interesting packages
- AI subsystems (experimental) → [lexigram-ai-experimental](https://github.com/dbtinoy-/lexigram-ai-experimental)
- multimedia subsystems (experimental) → [lexigram-multimedia-experimental](https://github.com/dbtinoy-/lexigram-multimedia-experimental)


---

*made for people who like building things and keeping them buildable.*