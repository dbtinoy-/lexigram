# lexigram

*the async python backend where the glue is already written.*

[![PyPI version](https://img.shields.io/pypi/v/lexigram?color=%2334D058&label=pypi%20package)](https://pypi.org/project/lexigram/)
[![Python versions](https://img.shields.io/pypi/pyversions/lexigram?color=%2334D058)](https://pypi.org/project/lexigram/)
[![License](https://img.shields.io/pypi/l/lexigram?color=%2334D058)](https://github.com/dbtinoy-/lexigram/blob/main/LICENSE)

hey — wanna ship a real app this weekend?

![Lexigram demo](lexigram/docs/gifs/hero/lexigram-hero.gif)

glue code is the boring 30% of every backend — the session factory, the middleware order, the retry wiring, the dozen init functions that have to boot in exactly the right order. lexigram is the async-first framework that already wrote that part: modules register providers, providers bind contracts, and one container resolves and boots web, sql, cache, auth, queues, events — and the whole ai and multimedia families — in a single call. no glue code, no 200-line config files, and nothing is bolted on: swap redis for in-memory, postgres for sqlite, or openai for ollama with a config line, not a refactor.

- **the glue, already written.** providers, modules, controllers — one container, one boot call, instead of a hundred lines of init.
- **swap without ripples.** redis ↔ in-memory, postgres ↔ sqlite, openai ↔ ollama — one contract, a config line away.
- **async, end to end.** the container, the modules, the controllers — concurrency-safe by construction.
- **contracts everywhere.** every package talks through protocols, so swapping an implementation never ripples.

→ full docs at [docs.lexigram.dev](https://docs.lexigram.dev)

## install

```bash
uv add "lexigram[web]"   # core + web + server (what the example below uses)
pip install "lexigram[web]"

# want the AI layer too?   `uv add "lexigram[ai,web]"`   # agents, llms, rag, memory, ...
# want the Data layer too? `uv add "lexigram[db]"`   # nosql + storage + search, same container
#   nosql:    `DocumentQueryBuilder` — typed document queries, multiple backends
#   storage:  `BlobStoreProtocol` — local, memory, s3, azure, gcs (one contract)
#   search:   `SearchEngine` — federated and hybrid search across backends
#   resolved like anything else — constructor-injected by contract, no glue code
# ... and many more packages available
```

```text
HOOK    agents · llms · rag · mcp · memory
CORE    web · sql · cache · auth · queue · events
TRUST   di · contracts · modules · async
```

## 60 seconds, end to end

```python
from lexigram import Application
from lexigram.web import Controller, get, WebModule
from lexigram.web.server import run_server


class HelloController(Controller):
    @get("/hello")
    async def hello(self, name: str = "world") -> dict:
        return {"message": f"hello, {name}"}


app = Application()
app.add_modules([WebModule.configure(controllers=[HelloController])])

run_server(app, port=8000)
```

→ http://localhost:8000/hello?name=lexigram

#### also available by default
- → http://localhost:8000/health
- → http://localhost:8000/docs (Swagger UI)
- → http://localhost:8000/redoc (Redoc)


#### what just happened?

- `Application()` + `add_modules(...)` assembled the web module — the app boots lazily when the server starts.
- `WebModule.configure(...)` registered the controller — no router setup, no middleware boilerplate.
- `HelloController` is a plain typed class; `/hello` maps query params to arguments.
- `run_server(...)` serves it with uvicorn — `/health`, `/docs`, and `/redoc` come along for free.

→ [Your First App](docs/lexigram-docs/getting-started/first-app.md) — the full walkthrough with DI, controllers, and `Result` types

## what's in the box

this repo ships the main ecosystem — the core, the backend, the contracts:

- **`lexigram`** — the core, the container, the boot lifecycle
- **`lexigram-web`** — async routing and controllers
- **`lexigram-sql`** — sqlalchemy, already wired
- **`lexigram-cache`** — redis and in-memory, one contract
- **`lexigram-vector`** / **`lexigram-graph`** — storage for the ai layer
- plus auth, events, queue, tasks, http, resilience, storage, search, notification, monitor, webhook, tenancy, features, audit, graphql, nosql, workflow, and testing

the AI family — agents, llms, rag, memory, skills, mcp, session, workers, observability, feedback, and the guard / governance / evaluation / prompt / relay suite — lives in [lexigram-ai](https://github.com/dbtinoy-/lexigram-ai-experimental). multimedia (tts, music, image, video, beat, interpolate, upscale) lives in [lexigram-multimedia](https://github.com/dbtinoy-/lexigram-multimedia-experimental). same modules, same container, same rules — their own repos and cadence.

the full list — including notification, queue, events, auth, observability, and more — lives in the [docs ecosystem](https://docs.lexigram.dev/ecosystem/).

## early on purpose

Lexigram is in 0.1 — which means you can still change it. APIs may shift before 1.0, so pin your versions, and tell us what feels wrong. Shaping a framework is more fun when it's still soft.

→ [github.com/dbtinoy-/lexigram/issues](https://github.com/dbtinoy-/lexigram/issues)

## why it grows with you

- **contracts.** every package talks through protocols, so swapping the implementation never ripples.
- **providers.** lifecycle and wiring live in one place, so boot order is explicit and tests are trivial.
- **async, end to end.** the container, the modules, the controllers — concurrency-safe by construction.

## audit

- [Tests](docs/lexigram-docs/audit/AUDIT_TESTS.md) — live test evidence and coverage per package
- [Quality](docs/lexigram-docs/audit/AUDIT_QUALITY.md) — mypy and ruff quality gates
- [Security](docs/lexigram-docs/audit/AUDIT_SECURITY.md) — static security analysis

## reference

- [Env vars](docs/lexigram-docs/reference/REF_ENV_VARS.md) — every `LEX_*` environment variable
- [Error codes](docs/lexigram-docs/reference/REF_ERROR_CODES.md) — error codes and their meanings

## roadmap

#### current status (0.1.x — Alpha)
- Alpha; public APIs may change before 1.0
- ~50 open-source packages (MIT)
- Test suite runs in local CI across packages

#### short term (Q2 2026)
- [x] Extended AI capabilities — AI subsystem packages (agents, guard, memory, rag, …) - in testing
- [x] Reactive state and event wiring - in testing
- [ ] Additional backend support

#### medium term (Q3-Q4 2026)
- [ ] Advanced monitoring
- [x] Enhanced security — audit remediation partially implemented (security lanes in progress)
- [x] Production-grade Admin dashboard — `lexigram-admin` in active development
- [x] Full-stack starter template — in progress
- [ ] Distributed tracing
- [ ] Performance optimizations
- [x] Reach 80% Unit Tests overall coverage (now 75% in progress)
- [ ] Reach 80% Integration Tests overall coverage (integration-only baseline measured 34% for lexigram-admin; gate = per-package integration-only ≥ floor, root aggregate ≥80% — in progress)

#### long term (2027)
- [ ] Enterprise features
- [ ] Enhanced observability
- [ ] Community expansion (if approved)

#### → see [MILESTONE.md](./MILESTONE.md) 

## interesting subsystems and packages

- CLI → [lexigram-cli](https://github.com/dbtinoy-/lexigram-cli-experimental)
- Admin → [lexigram-admin](https://github.com/dbtinoy-/lexigram-admin-experimental)
- UI → [lexigram-ui](https://github.com/dbtinoy-/lexigram-ui-experimental)
- AI subsystems → [lexigram-ai](https://github.com/dbtinoy-/lexigram-ai-experimental)
- Multimedia subsystems → [lexigram-multimedia](https://github.com/dbtinoy-/lexigram-multimedia-experimental)

## pointers

- full docs → [docs.lexigram.dev](https://docs.lexigram.dev)
- skills for AI coding agents → [lexigram-skills](https://github.com/dbtinoy-/lexigram-framework-skills)
- contributing → [CONTRIBUTING.md](./CONTRIBUTING.md)
- security → [SECURITY.md](./SECURITY.md)
- license → [LICENSE](./LICENSE)

---

*made for people who like building things and keeping them buildable.*