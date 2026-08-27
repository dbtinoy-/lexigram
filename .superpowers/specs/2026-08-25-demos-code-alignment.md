# Spec: Demos Code Alignment — the canonical Demo Blueprint

> Status: **binding pattern** for every existing demo and every future demo
> (Wave 2 specs/plans inherit it). This document is the single source of truth;
> per-demo plans only reference it.

## 1. Audit findings (2025-08-25, whole fleet)

| Concern | Status | Evidence |
|---|---|---|
| YAML configuration | ✗ absent | no `application.yaml` anywhere; ports/security/knobs hardcoded in `module.py` + env vars |
| CLI narration | ✗ `print()` | 6 × `main.py` (rates 22 calls, orders, rag-docs, monitor, feedback-loop, repro runner) |
| Ambient capabilities | partial | auth demos use `clock/identity/hashing`; `orders/domain.py`, `rates/simulated_upstream.py` reach for stdlib directly |
| Provider hygiene | ✓ | `health_check` on all 16 providers |
| Result pattern | ✓ mostly | 20 files; sweep for blind `unwrap()` during rollout |
| Logging | ✓ mostly | `get_logger` in 25 files; remaining stragglers fixed with print removal |
| ProblemDetail errors | partial | 10 files; standardize RFC-9457 on every non-2xx API path |
| Duplication | ✗ | `ui/pages.py` structurally cloned ×N; `conftest.py` bootstrap cloned ×14 |
| Type gate | ✗ | demos excluded from `make type`; several would fail |
| Docs/OpenAPI | unverified | confirm `/docs` openapi availability per demo during rollout |

## 2. The Demo Blueprint (directory contract)

```
demos/<slug>/
├── README.md              # run (serve/demo/embedded), API table, tour script
├── application.yaml       # ALL runtime knobs — see §3
├── conftest.py            # two lines: bootstrap + shared fixtures import
├── src/<pkg>/
│   ├── module.py          # configure(): imports WebModule; NO literal ServerConfig/port
│   ├── config.py          # DemoConfig dataclass bound from yaml `demo:` section
│   ├── controllers/{api,pages}.py
│   ├── services/          # domain logic; Result[T,E]; typed ctor injection
│   ├── repositories/
│   └── di/provider.py     # register()/boot()/shutdown() + health_check
└── tests/                 # pytest; fakes at contract boundaries only
```

## 3. YAML-first configuration

One `application.yaml` per demo; profiles for variants; nothing hardcoded in
Python except structural defaults:

```yaml
# demos/resilient-rates/application.yaml
web:
  server: { host: 127.0.0.1, port: 7073 }
  security:
    csrf: { enabled: false }

demo:
  upstream_scenario: healthy
  cache_ttl_seconds: 60
  quotes: { base: EUR, quote: USD }
```

Rules:
- `web:` is consumed by the framework's own `config_key = "web"` injection —
  `module.configure()` stops constructing `ServerConfig/WebConfig` literals
  entirely (env override `DEMO_HUB_PORT`-style keys remain supported via the
  framework env layer, documented per demo).
- `demo:` binds to a frozen `DemoConfig` dataclass via
  `lexigram.config.base.from_yaml(..., section="demo")` (exact idiom pinned in
  Task A-recon); provider registers it as singleton; services receive it
  injected — never read yaml themselves.
- Seeded determinism knobs (seeds, scenario names, quota numbers) live here so
  walkthroughs are re-producible without code edits.

## 4. Code standards applied to demos (from AGENTS.md)

- **No `print()`**: CLI walkthroughs narrate through `get_logger`
  structured events (`logger.info("act.completed", act=2, title=...)`);
  human-readable console rendering is the logger console renderer's job.
- **Ambient capabilities**: wall-clock via `lexigram.primitives.clock`,
  ids via `identity.generate_for(...)`, digests via hashing ambient.
  *Documented exception:* deterministic scripted randomness keeps
  `random.Random(seed)` — determinism IS the feature; annotate with a
  `# deterministic-by-design` comment.
- **Errors**: every non-2xx returns RFC-9457 `ProblemDetail`; domain failures
  are `Result[_, SpecificError]`; infrastructure faults raise.
- **Controllers** stay stateless thin adapters; **providers** contain no
  business logic; **services** own behaviour behind contracts.
- **500-line limit**, absolute imports, `__init__.py` exports-only — already
  enforced by repo gates, now also expected in demos.

## 5. Testing standard

- Contract-boundary fakes (no mocks of internals); async tests via
  `pytest.mark.asyncio`.
- Shared bootstrap promoted into `lexigram-testing`
  (`lexigram.testing.demo.install_demo_src(__file__)`) replacing 14 cloned
  `conftest.py` bodies.
- Each demo gains: happy-path service test, one failure-path Result test,
  ASGI round-trip for its API, yaml-binding test (defaults + override).
- New gate: `make type-demos` (mypy per demo src) wired into
  `make check-demos`.

## 6. Acceptance checklist (per demo)

- [ ] `application.yaml` present; module has zero literal host/port/security
- [ ] `DemoConfig` binding test exists
- [ ] zero `print(` in `src/` (grep-gated)
- [ ] ambient clock/identity used where wall-time/ids appear (or annotated
      deterministic exception)
- [ ] all error paths return ProblemDetail / Result
- [ ] mypy passes (`make type-demos`)
- [ ] conftest uses shared bootstrap
- [ ] README matches blueprint skeleton
