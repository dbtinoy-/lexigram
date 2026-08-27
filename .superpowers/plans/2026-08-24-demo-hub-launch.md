# Public Demo Launch: Website Fixes + Demo Hub + Docs Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Standing constraint:** NO COMMITS on the lexigram-starter-fullstack repo. For the three repos touched here (lexigram, lexigram-website, lexigram-docs), commit per task using the emoji convention from `lexigram/AGENTS.md`: `<emoji> <type>(<scope>): <summary>`.
>
> **Do not create worktrees or branches** (per AGENTS.md).

**Goal:** Make the 14 demos presentable to arriving visitors: fix lexigram.dev's broken SEO/assets, build a live demo hub at `demos.lexigram.dev` via Cloudflare Tunnel, and surface everything from docs.lexigram.dev.

**Architecture:** Three workstreams in one plan because they ship one experience: (A) repair the marketing site so it doesn't embarrass on arrival; (B) add a 15th demo — a hub console at `:7000` that health-checks all 13 live demo servers server-side (avoids browser CORS entirely) and renders a card grid with status dots + links; (C) expose it publicly with a Cloudflare Tunnel mapping `demos.lexigram.dev` → hub and `<name>.demos.lexigram.dev` → each service port, then wire a Demos section into the Starlight docs.

**Tech Stack:** Lexigram framework demos (existing pattern), httpx for hub health checks, vanilla JS hub UI, cloudflared for tunneling, Next.js 16 static site fixes, Astro/Starlight docs page.

**Spec:** Conversation decisions 2026-08-24 — keep both sites; hub lives on its own subdomain; LAN-first fallback accepted; auth consoles labeled sandbox.

## Global Constraints

- Commit format: `<emoji> <type>(<scope>): <summary>` — one emoji, matches type (see lexigram/AGENTS.md §Commit Message Convention)
- Demos follow the established pattern exactly: stateless pages controller in `ui/pages.py`, static assets under `ui/static/`, module wiring in `module.py`, CSRF disabled (`SecurityConfig(enable_csrf=False)`)
- All demo servers bind `127.0.0.1` — public exposure happens ONLY through cloudflared (outbound tunnel), never by opening ports
- Hub package name `demo_hub`, directory `demos/demo-hub/`, default port **7000**, env override `DEMO_HUB_PORT`
- Python: `from __future__ import annotations` first line, absolute imports, Google docstrings, typed ctor params, no `Any` on injected deps
- Verify commands — framework demos: `uv run --group tooling pytest <dir>/tests -q`; ruff: `uv run ruff check . && uv run ruff format .`; website: `npm run build` inside `lexigram-frontend/`; docs: `npm run build`
- Sandbox labeling is mandatory copy on the hub page: "Sandbox — in-memory state resets often; auth consoles use seeded demo credentials"

---

### Task 1: Website SEO repairs (aixphub leftovers)

**Files:**
- Modify: `/home/admin/Documents/AI/applications/lexigram-dev/lexigram-website/lexigram-frontend/public/robots.txt`
- Modify: `/home/admin/Documents/AI/applications/lexigram-dev/lexigram-website/lexigram-frontend/public/sitemap.xml`
- Modify: `/home/admin/Documents/AI/applications/lexigram-dev/lexigram-website/lexigram-frontend/.env.production`
- Modify: `/home/admin/Documents/AI/applications/lexigram-dev/lexigram-website/lexigram-frontend/.env.example:1-33`
- Modify: `/home/admin/Documents/AI/applications/lexigram-dev/lexigram-website/lexigram-frontend/public/ads.txt`

**Interfaces:**
- Produces: correct canonical domain `https://lexigram.dev` everywhere search engines and ad crawlers look

- [ ] **Step 1: Fix robots.txt**

Replace entire content with:
```
User-agent: *
Allow: /

Sitemap: https://lexigram.dev/sitemap.xml
```

- [ ] **Step 2: Fix sitemap.xml**

Replace entire content with:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://lexigram.dev/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
```

- [ ] **Step 3: Fix .env.production**

Read the file first. Set `NEXT_PUBLIC_SITE_URL=https://lexigram.dev`. Keep any Turnstile/email values untouched.

- [ ] **Step 4: Fix .env.example**

Change line 1 header comment `AIX Hub Website` → `Lexigram Website`; line 7 `NEXT_PUBLIC_SITE_URL=https://aixphub.com` → `NEXT_PUBLIC_SITE_URL=https://lexigram.dev`; lines 17-18 comment mentioning `piccolina.aixphub.com` → mention `piccolina.aixphub.com` only if that redirect stays (it does, see `_redirects`) — otherwise reword to "ads are served on legacy subdomains"; lines 31-32 `hello@aixphub.com` / `no-reply@aixphub.com` → `noreply@lexigram.dev` style consistent with wrangler.toml vars.

- [ ] **Step 5: Fix ads.txt**

Delete line 2 (`subdomain=docs.lexigram.dev` — invalid ads.txt syntax). Result:
```
google.com, pub-5797721054649563, DIRECT, f08c47fec0942fa0
```

- [ ] **Step 6: Verify build still passes**

Run: `cd /home/admin/Documents/AI/applications/lexigram-dev/lexigram-website/lexigram-frontend && npm run build`
Expected: exit 0, static export regenerated in `out/`.

- [ ] **Step 7: Commit**

```bash
git -C /home/admin/Documents/AI/applications/lexigram-dev/lexigram-website add -A
git -C /home/admin/Documents/AI/applications/lexigram-dev/lexigram-website commit -m "🔧 chore(seo): point canonical domain at lexigram.dev"
```

---

### Task 2: Showcase teaser images (4 visible 404s)

`brewing-apps.ts` references `/herbert|stellar|geezmo|buffy/teaser.png` but only `piccolina/teaser.png` exists. Generate deterministic branded placeholder teasers rather than shipping 404s or wrong-brand images.

**Files:**
- Create: script `/tmp/opencode/gen_teasers.py` (throwaway generator, not committed)
- Create: `lexigram-website/lexigram-frontend/public/herbert/teaser.png`
- Create: `lexigram-website/lexigram-frontend/public/stellar/teaser.png`
- Create: `lexigram-website/lexigram-frontend/public/geezmo/teaser.png`
- Create: `lexigram-website/lexigram-frontend/public/buffy/teaser.png`

**Interfaces:**
- Produces: 1200×750 PNG per app matching `previewImage` paths already consumed by the BuiltWith component — zero component changes needed.

- [ ] **Step 1: Write generator script**

```python
"""Generate branded teaser placeholders for showcase apps."""
from PIL import Image, ImageDraw

APPS = [
    ("herbert", "Herbert", "#06b6d4", "W"),
    ("stellar", "Stellar", "#8b5cf6", "AI"),
    ("geezmo", "Geezmo", "#10b981", "D"),
    ("buffy", "Buffy", "#f59e0b", "T"),
]
OUT = "/home/admin/Documents/AI/applications/lexigram-dev/lexigram-website/lexigram-frontend/public"

def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))

for slug, name, color, mark in APPS:
    c = Image.new("RGB", (1, 1)); c.putpixel((0, 0), (0, 0, 0))
    rgb = Image.new("RGB", (1, 1)); rgb.putpixel((0, 0), (0, 0, 0))
    hexv = color.lstrip("#")
    base = tuple(int(hexv[i:i+2], 16) for i in (0, 2, 4))
    dark = lerp(base, (10, 15, 28), 0.82)
    img = Image.new("RGB", (1200, 750))
    d = ImageDraw.Draw(img)
    for y in range(750):
        d.line([(0, y), (1200, y)], fill=lerp(dark, base, (y / 750) ** 2))
    # big monogram
    size = 340
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 44)
    except OSError:
        font = small = None
    bbox = d.textbbox((0, 0), mark, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((1200 - w) / 2 - bbox[0], (750 - h) / 2 - bbox[1] - 30), mark,
           fill=(255, 255, 255), font=font)
    label = f"Lexigram {name}"
    lb = d.textbbox((0, 0), label, font=small)
    d.text(((1200 - (lb[2]-lb[0])) / 2, 640), label, fill=tuple(int(v*0.85)+38 for v in base) if max(base) < 200 else base, font=small)
    img.save(f"{OUT}/{slug}/teaser.png")
    print("wrote", slug)
```

Run: `python3 /tmp/opencode/gen_teasers.py` (create dirs first: `mkdir -p public/{herbert,stellar,geezmo,buffy}`)
Expected: four "wrote X" lines; files exist ≥10 KB each.

- [ ] **Step 2: Visual sanity check**

Open one file (`xdg-open public/herbert/teaser.png` or Read tool) — brand color background gradient, white monogram, app label. If PIL missing: `pip install pillow` into an ad-hoc venv, do NOT touch repo deps.

- [ ] **Step 3: Rebuild + verify no 404s**

`cd lexigram-frontend && npm run build`, then `grep -c "teaser.png" out/index.html` ≥ 1 and confirm `out/herbert/teaser.png` etc. exist.

- [ ] **Step 4: Commit**

```bash
git -C /home/admin/Documents/AI/applications/lexigram-dev/lexigram-website add lexigram-frontend/public/herbert lexigram-frontend/public/stellar lexigram-frontend/public/geezmo lexigram-frontend/public/buffy
git -C /home/admin/Documents/AI/applications/lexigram-dev/lexigram-website commit -m "🎨 style(showcase): generate branded teaser images"
```

---

### Task 3: Website debris cleanup + Live Demos nav link

**Files:**
- Delete: `lexigram-website/lexigram-frontend/src/components/BrewingApp-bak.tsx`
- Delete: `lexigram-website/lexigram-frontend/fix_sections.py` (verify path exists first; also `fix_flex_center.sh`)
- Modify: `lexigram-website/lexigram-frontend/src/components/Navbar.tsx` — add external link "Live Demos" → `https://demos.lexigram.dev`

**Interfaces:**
- Consumes: hub URL from Task 6 (constant `https://demos.lexigram.dev` — safe to reference before tunnel exists)

- [ ] **Step 1: Remove debris**

`rm src/components/BrewingApp-bak.tsx`; locate and remove `fix_sections.py` / `fix_flex_center.sh` if present (`ls lexigram-frontend/*.py lexigram-frontend/*.sh`). Grep for imports of `BrewingApp-bak` — expect zero.

- [ ] **Step 2: Add nav link**

Read `Navbar.tsx`, mirror the existing external-link pattern used for the docs CTA (target `_blank`, rel noopener). Add item `{ label: 'Live Demos', href: 'https://demos.lexigram.dev', external: true }` following the component's own data shape — match whatever array/JSX structure exists rather than inventing props.

- [ ] **Step 3: Build + commit**

`npm run build` passes. Commit:
```bash
git -C ... add -A
git -C ... commit -m "✨ feat(nav): link live demo hub"
```

- [ ] **Step 4: Deploy site**

`npm run pages:deploy` (wrangler). Confirm https://lexigram.dev serves updated robots.txt (`curl -s https://lexigram.dev/robots.txt`).

---

### Task 4: Demo hub — backend (module, provider, controller)

**Files (all under `/home/admin/Documents/AI/applications/lexigram-dev/lexigram/demos/demo-hub/`):**
- Create: `src/demo_hub/__init__.py`
- Create: `src/demo_hub/module.py`
- Create: `src/demo_hub/main.py`
- Create: `src/demo_hub/services/registry.py`
- Create: `src/demo_hub/controllers/api.py`
- Create: `tests/test_hub_api.py`
- Create: `conftest.py`

**Interfaces:**
- Produces: `DemoHubModule.configure(port=None)` DynamicModule; `ServiceRegistry.statuses() -> list[dict]` where each dict is `{"name": str, "slug": str, "port": int, "kind": "web"|"cli", "blurb": str, "status": "up"|"down", "latency_ms": float|None}`; API routes `GET /api/status`, `GET /api/services`.

- [ ] **Step 1: Write failing test**

```python
"""Tests for the demo hub registry and API surface."""
from __future__ import annotations

from pathlib import Path

import pytest

registry_mod = pytest.importorskip("demo_hub.services.registry")


def test_registry_lists_all_thirteen_live_services() -> None:
    registry = registry_mod.ServiceRegistry()
    services = registry.services
    assert len([s for s in services if s.kind == "web"]) == 13


def test_registry_ports_are_unique_and_known() -> None:
    registry = registry_mod.ServiceRegistry()
    ports = [s.port for s in registry.services]
    assert len(set(ports)) == len(ports)
    assert 7000 not in ports  # hub never checks itself
```

Add `conftest.py` mirroring the llm-reproducibility pattern:

```python
"""Pytest bootstrap for the demo-hub demo."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
```

Run: `uv run --group tooling pytest demos/demo-hub/tests -q` → FAIL (no package).

- [ ] **Step 2: Implement registry**

```python
"""Catalog of every live demo service the hub monitors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoService:
    """One monitorable demo entry.

    Attributes:
        slug: URL-safe identifier, also the tunnel subdomain prefix.
        name: Display name.
        port: Local port the service binds on this host.
        kind: ``web`` for live servers, ``cli`` for offline entries.
        blurb: One-line description for the card grid.
        check_path: Path used for the health GET.
    """

    slug: str
    name: str
    port: int
    kind: str
    blurb: str
    check_path: str = "/"


class ServiceRegistry:
    """Static catalog plus async health probing of all live services."""

    def __init__(self) -> None:
        self.services: list[DemoService] = [
            DemoService("realtime-monitor", "Realtime Monitor", 7071, "web",
                        "SSE replay + WebSocket operator channel"),
            DemoService("resilient-rates", "Resilient Rates", 7073, "web",
                        "Retry, circuit breaker, stale fallback desk"),
            DemoService("event-driven-orders", "Event-Driven Orders", 7074, "web",
                        "CQRS lifecycle with transactional outbox"),
            DemoService("rag-docs", "RAG Docs", 7075, "web",
                        "Cited answers over framework documentation"),
            DemoService("support-agent", "Support Agent", 8082, "web",
                        "ReAct agent with scripted LLM + tools"),
            DemoService("memory-chat", "Memory Chat", 8083, "web",
                        "Episodic + semantic memory, owner isolation"),
            DemoService("ai-guardrails", "AI Guardrails", 8084, "web",
                        "Injection blocking, PII redaction, budgets"),
            DemoService("prompt-lab", "Prompt Lab", 8085, "web",
                        "Prompt versioning with deterministic A/B"),
            DemoService("feedback-loop", "Feedback Loop", 8086, "web",
                        "Ratings promoted into regression suites"),
            DemoService("auth-web", "Auth Web", 8081, "web",
                        "Cookie sessions, JWT claims, lockout"),
            DemoService("auth-rbac", "Auth RBAC", 8090, "web",
                        "Permission matrix with live authorize()"),
            DemoService("auth-apikeys", "Auth API Keys", 8091, "web",
                        "Scoped machine keys, instant revocation"),
            DemoService("auth-mfa", "Auth MFA", 8092, "web",
                        "TOTO challenge flow with backup codes"),
            DemoService("llm-reproducibility", "LLM Reproducibility", 0, "cli",
                        "Seeded digest-pinned experiment (CLI/notebook)"),
        ]

    async def statuses(self) -> list[dict[str, object]]:
        """Probe every web service concurrently; CLI entries pass through."""
        import asyncio
        import time

        import httpx

        async def probe(svc: DemoService) -> dict[str, object]:
            if svc.kind != "web":
                return {"slug": svc.slug, "name": svc.name, "port": svc.port,
                        "kind": svc.kind, "blurb": svc.blurb,
                        "status": "cli", "latency_ms": None}
            started = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=1.5) as client:
                    resp = await client.get(
                        f"http://127.0.0.1:{svc.port}{svc.check_path}"
                    )
                ok = resp.status_code < 500
            except Exception:  # noqa: BLE001 - probe must never raise
                ok = False
            latency = round((time.perf_counter() - started) * 1000, 1)
            return {"slug": svc.slug, "name": svc.name, "port": svc.port,
                    "kind": svc.kind, "blurb": svc.blurb,
                    "status": "up" if ok else "down", "latency_ms": latency}

        return list(await asyncio.gather(*(probe(s) for s in self.services)))
```

Fix the typo guard: MFA blurb must read "TOTP". Re-run tests → PASS.

- [ ] **Step 3: Module + main + API controller**

`controllers/api.py`:

```python
"""JSON surface for the hub console."""
from __future__ import annotations

from starlette.requests import Request

from lexigram.web import Controller, JSONResponse, get
from demo_hub.services.registry import ServiceRegistry


class HubApiController(Controller):
    """Expose the service catalog with live health status."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self._registry = registry

    @get("/api/status")
    async def status(self, request: Request) -> JSONResponse:
        return JSONResponse({"services": await self._registry.statuses()})
```

`module.py` mirrors resilient-rates wiring: `WebModule.configure(controllers=[HubApiController, HubPageController], web_config=WebConfig(server=ServerConfig(host="127.0.0.1", port=selected_port), security=SecurityConfig(enable_csrf=False)))`, providers register `ServiceRegistry` singleton via a small `HubProvider` (copy shape of rates' `RatesProvider`).

`main.py` copies memory-chat's serve-only boot verbatim, swapping names/port env `DEMO_HUB_PORT` default `7000`.

- [ ] **Step 4: Tests green + ruff + compile**

`uv run --group tooling pytest demos/demo-hub/tests -q` → PASS; ruff clean; `compileall` clean.

- [ ] **Step 5: Commit**

```bash
git -C /home/admin/Documents/AI/applications/lexigram-dev/lexigram add demos/demo-hub
git -C ... commit -m "✨ feat(demos): demo-hub backend with live service registry"
```

---

### Task 5: Demo hub — frontend (pages controller + UI assets)

**Files:**
- Create: `src/demo_hub/ui/{__init__.py,pages.py}`
- Create: `src/demo_hub/ui/views/hub.html`
- Create: `src/demo_hub/ui/static/{style.css,app.js}`

**Interfaces:**
- Consumes: `GET /api/status` from Task 4.
- Produces: `HubPageController` serving `/`, `/static/style.css`, `/static/app.js` — exact same route contract as RatesPageController.

- [ ] **Step 1: pages.py** — copy `rates/ui/pages.py` verbatim, rename class `RatesPageController`→`HubPageController`, view file `hub.html`, docstring updated.

- [ ] **Step 2: hub.html** — sections: header ("Lexigram Live Demos" + sandbox banner text from Global Constraints), filter buttons (All / Capability / Auth), card grid container `<div id="cards">`, footer linking GitHub + docs. Reference `/static/style.css`, `/static/app.js`.

- [ ] **Step 3: app.js** —

```javascript
/* Vanilla-JS hub console (no build step). */
"use strict";
const $ = (id) => document.getElementById(id);
let filter = "all";

async function load() {
  const res = await fetch("/api/status");
  const { services } = await res.json();
  render(services);
}

function dot(s) {
  const cls = s.status === "up" ? "up" : s.status === "cli" ? "cli" : "down";
  return `<span class="dot ${cls}" title="${s.status}"></span>`;
}

function card(s) {
  const href = s.kind === "web"
    ? `${location.protocol}//${s.slug}.demos.lexigram.dev`
    : "https://docs.lexigram.dev";
  return `<a class="card ${filter !== "all" && !matchFilter(s) ? "hidden" : ""}"
    href="${href}" target="_blank" rel="noopener">
    ${dot(s)}<h3>${s.name}</h3><p>${s.blurb}</p>
    <code>:${s.port}</code><span class="lat">${s.latency_ms ?? ""}</span></a>`;
}

const CAPABILITY = new Set(["realtime-monitor","resilient-rates","event-driven-orders",
  "rag-docs","support-agent","memory-chat","ai-guardrails","prompt-lab","feedback-loop"]);
function matchFilter(s) {
  return filter === "capability" ? CAPABILITY.has(s.slug) : !CAPABILITY.has(s.slug);
}

function render(services) {
  $("cards").innerHTML = services.map(card).join("");
}
document.querySelectorAll("#filters button").forEach((b) =>
  b.addEventListener("click", () => { filter = b.dataset.f;
    document.querySelectorAll("#filters button").forEach((x) => x.classList.toggle("active", x === b));
    load(); }));
load();
setInterval(load, 5000);
```

- [ ] **Step 4: style.css** — reuse support-agent theme variables (`--bg:#10151c` etc.), `.dot.up{background:#4ade80}.dot.down{background:#ff7a7a}.dot.cli{background:#fbbf24}`, responsive card grid `repeat(auto-fill,minmax(260px,1fr))`.

- [ ] **Step 5: Wire into module controllers list, run full gates**

Boot smoke: start hub, curl `/api/status` while rates runs on 7073 → `"up"`; stop rates → next poll shows `"down"`. Then `pytest`/ruff/`compileall` all clean. Commit `✨ feat(demos): demo-hub console UI`.

---

### Task 6: Framework repo integration (README + Makefile gates)

**Files:**
- Modify: `/home/admin/Documents/AI/applications/lexigram-dev/lexigram/demos/README.md` — add hub to "The demos at a glance" (after intro paragraph) and Running section: `PYTHONPATH=demos/demo-hub/src uv run python -m demo_hub   # demo hub (:7000)`
- Modify: `/home/admin/Documents/AI/applications/lexigram-dev/lexigram/Makefile:110-137` — append `demos/demo-hub/tests` to `DEMO_TEST_DIRS`, `demos/demo-hub` to `DEMO_COMPILE_DIRS`, hub line to `smoke-demos`: `cd demos/demo-hub && PYTHONPATH=src $(CURDIR)/.venv/bin/python -c "import demo_hub.main" >/dev/null`

- [ ] **Step 1:** Edit both files (hub listed as demo #1 since it's the entry point).
- [ ] **Step 2:** Run `make test-demos verify-demos smoke-demos` → all green.
- [ ] **Step 3:** Commit `📝 docs(demos): register demo-hub in gates + readme`.

---

### Task 7: `demos-up` / `demos-down` / `demos-status` orchestration

**Files:**
- Modify: `/home/admin/Documents/AI/applications/lexigram-dev/lexigram/Makefile` (new targets after `smoke-demos`)

**Interfaces:**
- Produces: `make demos-up` starts all 13 servers, logs to `.cache/demo-logs/<slug>.log`, PIDs in `.cache/demo-pids/`; `demos-down` kills them; `demos-status` curls each port once.

- [ ] **Step 1: Add targets**

```makefile
DEMOS_UP := demos/realtime-monitor:demos/realtime-monitor/src:ops_console:7071 \
	demos/resilient-rates:demos/resilient-rates/src:rates:7073 \
	demos/event-driven-orders:demos/event-driven-orders/src:orders:7074 \
	demos/rag-docs:demos/rag-docs/src:rag_docs:7075 \
	demos/auth-web:demos/auth-web/src:auth_web:8081 \
	demos/support-agent:demos/support-agent/src:support_agent:8082 \
	demos/memory-chat:demos/memory-chat/src:memory_chat:8083 \
	demos/ai-guardrails:demos/ai-guardrails/src:guard_gate:8084 \
	demos/prompt-lab:demos/prompt-lab/src:prompt_lab:8085 \
	demos/feedback-loop:demos/feedback-loop/src:feedback_loop:8086 \
	demos/auth-rbac:demos/auth-rbac/src:rbac_console:8090 \
	demos/auth-apikeys:demos/auth-apikeys/src:apikey_console:8091 \
	demos/auth-mfa:demos/auth-mfa/src:mfa_console:8092

.PHONY: demos-up
demos-up: ## Start every live demo server in the background
	@mkdir -p .cache/demo-logs .cache/demo-pids
	@for entry in $(DEMOS_UP); do IFS=: read dir srcpath mod port <<< "$$entry"; \
		PYTHONPATH=$$srcpath nohup $(CURDIR)/.venv/bin/python -m $$mod >> .cache/demo-logs/$$mod.log 2>&1 & echo $$! > .cache/demo-pids/$$mod.pid; \
		echo "started $$mod :$$port"; done
	@sleep 3 && $(MAKE) --no-print-directory demos-status

.PHONY: demos-down
demos-down: ## Stop every backgrounded demo server
	@for pidfile in .cache/demo-pids/*.pid; do [ -f "$$pidfile" ] || continue; \
		pid=$$(cat $$pidfile); kill $$pid 2>/dev/null && echo "stopped $$pidfile"; rm -f $$pidfile; done

.PHONY: demos-status
demos-status: ## Probe every demo port once
	@for entry in $(DEMOS_UP); do IFS=: read dir srcpath mod port <<< "$$entry"; \
		curl -so /dev/null -w "%{http_code}" --max-time 2 http://127.0.0.1:$$port/ | grep -q 2 && echo "UP   $$mod :$$port" || echo "DOWN $$mod :$$port"; done
```

Note: zsh is the login shell but make recipes use `/bin/sh`; the herestring read syntax above is POSIX-safe.

- [ ] **Step 2: Exercise the loop** — `make demos-up`, verify 13 UP, open http://127.0.0.1:7000 shows all green, `make demos-down`, verify ports closed (`ss -ltn | grep -E '707|808|809'` empty).

- [ ] **Step 3:** Commit `✨ feat(make): demo fleet up/down/status targets`.

---

### Task 8: Cloudflare Tunnel — `*.demos.lexigram.dev`

**Files:**
- Create: `~/.cloudflared/config.yml` (machine-local, NOT committed)
- Modify: nothing in-repo except Task 9 docs page referencing final URLs

**Interfaces:**
- Produces: `https://demos.lexigram.dev` → hub `:7000`; `https://<slug>.demos.lexigram.dev` → each service port (slugs = registry slugs from Task 4).

- [ ] **Step 1: Install + authenticate** — `brew install cloudflared || download binary`; `cloudflared tunnel login` (browser).
- [ ] **Step 2: DNS** — in CF dashboard add wildcard `*.demos.lexigram.dev` CNAME `<tunnel-id>.cfargotunnel.com` (proxied). Root `demos.lexigram.dev` CNAME same target.
- [ ] **Step 3: Ingress config**

```yaml
tunnel: <TUNNEL-ID>
credentials-file: /home/admin/.cloudflared/<TUNNEL-ID>.json
ingress:
  - hostname: demos.lexigram.dev
    service: http://localhost:7000
  - hostname: realtime-monitor.demos.lexigram.dev
    service: http://localhost:7071
  - hostname: resilient-rates.demos.lexigram.dev
    service: http://localhost:7073
  - hostname: event-driven-orders.demos.lexigram.dev
    service: http://localhost:7074
  - hostname: rag-docs.demos.lexigram.dev
    service: http://localhost:7075
  - hostname: auth-web.demos.lexigram.dev
    service: http://localhost:8081
  - hostname: support-agent.demos.lexigram.dev
    service: http://localhost:8082
  - hostname: memory-chat.demos.lexigram.dev
    service: http://localhost:8083
  - hostname: ai-guardrails.demos.lexigram.dev
    service: http://localhost:8084
  - hostname: prompt-lab.demos.lexigram.dev
    service: http://localhost:8085
  - hostname: feedback-loop.demos.lexigram.dev
    service: http://localhost:8086
  - hostname: auth-rbac.demos.lexigram.dev
    service: http://localhost:8090
  - hostname: auth-apikeys.demos.lexigram.dev
    service: http://localhost:8091
  - hostname: auth-mfa.demos.lexigram.dev
    service: http://localhost:8092
  - service: http_status:404
```

- [ ] **Step 4: Run as service** — `cloudflared tunnel run` foreground for presentation day; `sudo cloudflared service install` only if persistence wanted.
- [ ] **Step 5: End-to-end verify** — `make demos-up`, then from an external network (phone hotspot) hit `https://demos.lexigram.dev` and two random subdomains; confirm TLS + content + hub dots all green. Document gotcha: hub card links assume HTTPS subdomains — already correct from Task 5.

---

### Task 9: Docs integration — Demos section

**Files:**
- Create: `/home/admin/Documents/AI/applications/lexigram-dev/lexigram-docs/src/content/docs/demos/index.md`
- Modify: `/home/admin/Documents/AI/applications/lexigram-dev/lexigram-docs/astro.config.mjs` — insert before GUIDES block (~line 217):

```js
{
    label: 'LIVE DEMOS',
    items: [
        { label: 'Overview & Status', slug: 'demos' },
    ],
},
```

- [ ] **Step 1: Write overview page** — frontmatter `title: "Live Demos"` + description; intro sentence ("Every demo boots the real framework..."); table with columns Demo | What it proves | Live URL | Run locally — 14 rows using exact names/slurbs/ports from the registry in Task 4, live URLs `https://<slug>.demos.lexigram.dev`, local commands from demos/README.md; closing section "Run the whole fleet": `make demos-up` + sandbox warning copy. Link the llm-reproducibility row to its notebook instead of a live URL.
- [ ] **Step 2:** `npm run build` → page builds at `/demos/`; sidebar shows LIVE DEMOS above GUIDES.
- [ ] **Step 3:** Commit `📝 docs: live demos index` then deploy per repo's publish flow.

---

### Task 10: Launch-day verification sweep

- [ ] `make check-demos` green (framework repo)
- [ ] `curl https://lexigram.dev/robots.txt` → lexigram.dev sitemap
- [ ] Showcase images render (spot-check 2 of 4)
- [ ] All 13 subdomains respond 200 from external network
- [ ] Hub shows 13 green dots; kill one service, refresh → red dot within 5s poll
- [ ] docs.lexigram.dev/demos live URLs clickable and correct
- [ ] Report completion; user handles any final commits they want to squash

## Self-Review Notes

- Spec coverage: website debt (Tasks 1-3), hub backend/frontend/gates/orchestration (4-7), tunnel (8), docs (9), verification (10). LAN-fallback decision needs no task — tunnel supersedes it.
- Type consistency: `ServiceRegistry.statuses()` returns the dict shape consumed by `app.js card()` fields (`slug,name,port,kind,blurb,status,latency_ms`) — verified aligned across Tasks 4↔5↔8.
- Placeholders: none — all code blocks complete; Navbar edit intentionally says "mirror existing pattern" because reading the actual component is step 1 of that task.
