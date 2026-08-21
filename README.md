# lexigram

*the async python backend where the glue is already written.*

[![PyPI version](https://img.shields.io/pypi/v/lexigram?color=%2334D058&label=pypi%20package)](https://pypi.org/project/lexigram/)
[![Python versions](https://img.shields.io/pypi/pyversions/lexigram?color=%2334D058)](https://pypi.org/project/lexigram/)
[![License](https://img.shields.io/pypi/l/lexigram?color=%2334D058)](https://github.com/dbtinoy-/lexigram/blob/main/LICENSE)
[![CI](https://github.com/dbtinoy-/lexigram/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/dbtinoy-/lexigram/actions/workflows/ci.yml)
[![Dependabot](https://img.shields.io/badge/dependabot-enabled-025e8c?logo=dependabot)](https://github.com/dbtinoy-/lexigram/security/dependabot)
[![Release](https://img.shields.io/github/v/release/dbtinoy-/lexigram?color=%2334D058)](https://github.com/dbtinoy-/lexigram/releases)

Stop assembling. Start building.

![Lexigram demo](core/lexigram/docs/gifs/hero/lexigram-hero.gif)

Every backend starts the same way: you wire up SQL, cache, auth, queues, events, middleware — before you write a single line of real code. Lexigram gives you a ready-to-use foundation: the core services are already connected and bootable. You define providers, modules, and controllers. One container boots them all — web, SQL, cache, auth, queues, events, plus the full AI and multimedia families — in one call. Swap Redis for in-memory, Postgres for SQLite, or OpenAI for Ollama with a single config line. No init scripts or config plumbing — just IoC, DI, and contracts, resolved automatically at boot. Just a working base for your logic to run on — and room to implement whatever comes next.

- **One-call startup.** Providers, modules, controllers — assembled and booted in the right order, automatically.
- **Swappable everything.** Redis ↔ in-memory, Postgres ↔ SQLite, OpenAI ↔ Ollama — same contract, one config line.
- **Async end to end.** Container, modules, controllers — concurrency-safe by design.
- **Contracts, not dependencies.** Every package talks through protocols, so implementations change without breaking anything.

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

### from this repository (fresh clone)

```bash
git clone https://github.com/dbtinoy-/lexigram.git
cd lexigram

# reproducible install (lockfile is committed — uv sync --locked fails
# on drift between uv.lock and pyproject.toml)
uv sync --group tooling --group qa --group security --locked

# environment reference — copy and adjust (every variable is optional;
# unset values fall back to framework defaults)
cp .env.example .env

# run the default suite — this is the offline gate: it requires ZERO
# external services. no postgres, no redis, no docker compose needed,
# even on a fresh clone
uv run pytest -m "not integration"

# optional: only the separate integration suite exercises live services
# (postgres on :5432, redis on :6379) — nothing else is required
docker compose up -d
uv run pytest -m integration
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

→ [Your First App](docs/getting-started/first-app.md) — the full walkthrough with DI, controllers, and `Result` types

→ [Demos](demos/README.md) — 🛡️ resilience patterns, 📦 CQRS & event sourcing, 📡 realtime SSE dashboards, 🧪 reproducible LLM experiments — four runnable apps gated like the framework

## what's in the box

this repo ships the main ecosystem — the core, the backend, the contracts:

- **`lexigram`** — the core, the container, the boot lifecycle
- **`lexigram-web`** — async routing and controllers
- **`lexigram-sql`** — sqlalchemy, already wired
- **`lexigram-cache`** — redis and in-memory, one contract
- **`lexigram-vector`** / **`lexigram-graph`** — storage for the ai layer
- plus auth, events, queue, tasks, http, resilience, storage, search, notification, monitor, webhook, tenancy, features, audit, graphql, nosql, workflow, and testing

the AI family — agents, llms, rag, memory, skills, mcp, session, workers, observability, feedback, and the guard / governance / evaluation / prompt / relay suite — lives in [experimental/ai](./experimental/ai/). multimedia (tts, music, image, video, beat, interpolate, upscale) lives in [experimental/multimedia](./experimental/multimedia/). same modules, same container, same rules.

```text
HOOK    agents · llms · rag · mcp · memory
CORE    web · sql · cache · auth · queue · events
DATA    vector · graph · search · nosql · storage
EDGE    http · webhook · notification
FLOW    tasks · workflow · resilience
OPS     monitor · audit · secrets · tenancy
MEDIA   tts · music · video · image
TRUST   di · contracts · modules · async
```

the full list — including notification, queue, events, auth, observability, and more — lives in the [docs ecosystem](https://docs.lexigram.dev/ecosystem/).

## early on purpose

Lexigram is in 0.1 — which means you can still change it. APIs may shift before 1.0, so pin your versions, and tell us what feels wrong. Shaping a framework is more fun when it's still soft.

→ [github.com/dbtinoy-/lexigram/issues](https://github.com/dbtinoy-/lexigram/issues)

## why it grows with you

- **contracts.** every package talks through protocols, so swapping the implementation never ripples.
- **providers.** lifecycle and wiring live in one place, so boot order is explicit and tests are trivial.
- **async, end to end.** the container, the modules, the controllers — concurrency-safe by construction.

## ci — what runs on every push/pr

`.github/workflows/ci.yml` runs four jobs (the badge at the top shows the
latest `main` run); each job has a local one-liner:

| job | runs in CI | locally |
| --- | --- | --- |
| `quality` | format, lint, tier boundary, mypy (core), per-package tests | `uv run ruff format --check . && uv run ruff check . && uv run mypy core/lexigram/src/ && uv run pytest -m "not integration" --no-cov` |
| `coverage` | aggregate tests with a 70% floor | `uv run pytest -m "not integration and not slow" --cov --cov-fail-under=70` |
| `example` | demos gate (pytest-bearing demo suites + compile checks) | `make check-demos` |
| `audit` | `pip-audit` known-vulnerability check | `uv run pip-audit` |

> Every `-m "not integration"` run — per-package or aggregate — executes
> fully offline: zero postgres/redis/docker required. Only the separate
> `Integration scenarios` CI job starts the backing services (via
> `tests/docker-compose.yml`, the same `docker compose up -d` flow).

## audit

- [Tests](docs/audit/AUDIT_TESTS.md) — live test evidence and coverage per package
- [Quality](docs/audit/AUDIT_QUALITY.md) — mypy and ruff quality gates
- [Security](docs/audit/AUDIT_SECURITY.md) — static security analysis

## reference

- [Env vars](docs/reference/REF_ENV_VARS.md) — every `LEX_*` environment variable
- [Error codes](docs/reference/REF_ERROR_CODES.md) — error codes and their meanings
- [Dependency tree](docs/reference/DEPENDENCY_TREE.md) — full locked workspace
  dependency graph; regenerate with `uv tree --locked > docs/reference/DEPENDENCY_TREE.md`
- the workspace root intentionally declares **zero dependencies** — it is a
  virtual manifest (`[tool.uv.workspace]` only, not a published distribution);
  each package's real dependency surface lives in its own `pyproject.toml`,
  surfaced in full in the locked tree above with pin hygiene enforced by
  `dev/check_dep_pins.py` (ci). audits reading "0 direct deps at root" are
  seeing this by design, not an undercount.

## roadmap

#### current status (0.1.x — Alpha)
- Alpha; public APIs may change before 1.0
- ~50 open-source packages (MIT)
- Test suite runs in local CI across packages

#### short term (Q2 2026)
- [x] Extended AI capabilities — AI subsystem packages (agents, guard, memory, rag, …) - in testing
- [x] Reactive state and event wiring — streams, subjects, operators, retry, end-event signaling (`docs/reference/REF_REACTIVE.md`)
- [ ] Additional backend support

#### medium term (Q3-Q4 2026)
- [ ] Advanced monitoring
- [x] Enhanced security — audit remediation partially implemented (security lanes in progress)
- [x] Production-grade Admin dashboard — `lexigram-admin` in active development
- [x] Full-stack starter template — in progress
- [ ] Distributed tracing
- [ ] Performance optimizations
- [x] Reach 80% Unit Tests overall coverage (now 75% in progress)
- [ ] Reach 80% test coverage overall (unit + integration; integration-only baseline ~35% — in progress)

#### long term (2027)
- [ ] Enterprise features
- [ ] Enhanced observability
- [ ] Community expansion (if approved)

#### → see [MILESTONE.md](./MILESTONE.md) 

## interesting subsystems and packages

- CLI → [experimental/apps/lexigram-cli](./experimental/apps/lexigram-cli/)
- Admin → [experimental/apps/lexigram-admin](./experimental/apps/lexigram-admin/)
- UI → [experimental/apps/lexigram-ui](./experimental/apps/lexigram-ui/)
- AI subsystems → [experimental/ai](./experimental/ai/)
- Multimedia subsystems → [experimental/multimedia](./experimental/multimedia/)

## pointers

- full docs → [docs.lexigram.dev](https://docs.lexigram.dev)
- skills for AI coding agents → [lexigram-skills](https://github.com/dbtinoy-/lexigram-framework-skills)
- contributing → [CONTRIBUTING.md](./CONTRIBUTING.md)
- security → [SECURITY.md](./SECURITY.md)
- license → [LICENSE](./LICENSE)

---

*made for people who like building things and keeping them buildable.*