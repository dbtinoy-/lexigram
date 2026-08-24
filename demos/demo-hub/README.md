# Demo Hub

One port for the whole fleet. The hub boots every web demo's real Lexigram
`Application` **in-process** and mounts it under `/demos/<slug>/`, then serves
a status console that links to all of them.

No other ports are needed in embedded mode — and every demo still runs
standalone on its documented port (nothing about the demos was changed).

## Run it

```bash
# from the repository root
make demos-up        # start the hub (:7000), wait, then list demo states
make demos-status    # re-probe any time
make demos-down      # stop everything

# or directly
PYTHONPATH=demos/demo-hub/src uv run python -m demo_hub   # :7000 (DEMO_HUB_PORT)
```

Then open <http://127.0.0.1:7000>:

| URL | What |
|-----|------|
| `/` | Hub console — card per demo, green/red status, All/Capability/Auth filters |
| `/api/status` | JSON status for every embedded demo (`up` / `down` / `cli`) |
| `/demos/resilient-rates/` | Each demo lives at `/demos/<slug>/` |

The first boot takes ~15–20 s while all 13 children boot; cards flip to green
as each one becomes ready.

## How embedding works

- `Fleet` imports each demo's own `Module.configure()` factory — the demos'
  code is used exactly as-is.
- Each child is a complete `Application` (own DI container, providers, state).
- `SubsiteMiddleware` makes root-relative frontends work under the mount:
  HTML asset URLs are rewritten server-side, a small injected shim prefixes
  `fetch` / `EventSource` / `WebSocket`, JS navigations such as
  `location.href = "/login"` are rebased, and redirects/cookies stay inside
  each demo's subtree.

Sandbox notice shown on the console applies to every child: in-memory state
resets often; auth consoles use seeded demo credentials only.

## Standalone mode (unchanged)

Any demo still runs alone, e.g.:

```bash
PYTHONPATH=demos/resilient-rates/src uv run python -m rates serve     # :7073
PYTHONPATH=demos/auth-rbac/src uv run python -m rbac_console          # :8090
```

See [the demos README](../README.md) for the full table of standalone ports
and commands. The hub's cards display those standalone ports as reference.

## Tests & gates

```bash
uv run --group tooling pytest demos/demo-hub/tests -q
```

The hub is registered in `make test-demos verify-demos smoke-demos` like every
other demo.
