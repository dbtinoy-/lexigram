# Prompt Lab — prompt authoring & deterministic A/B

> Module name: `prompt_lab` — run with `PYTHONPATH=demos/prompt-lab/src uv run python -m prompt_lab`

Iterate on a support-reply prompt like a scientist: render any revision,
inspect history, roll back, and score variants through the real
evaluation harness — zero LLM, byte-stable every run.

## Lexigram concepts used

| Concept | Where in this demo | Your app |
|---------|-------------------|----------|
| Composition root | `app.py` | Replace controllers/providers list |
| Module pattern | `PromptModule`, `WebModule` | Add your own modules |
| Provider lifecycle | `di/provider.py` | Replace with your registrations |
| Result<T,E> pattern | `controllers/api.py` | Return Result from handlers |
| Registry dispatch | `repository/responders.py` | Keyed strategy selection |
| Constructor injection | Controllers, services | Declare deps as typed params |
| Versioned store | `services/versioning.py` | Config/templates under version control |

## What it shows

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| Declared-variable templates | `repository/templates.py` | `ChatPromptTemplate` with `PromptVariable` |
| Version control for prompts | `services/versioning.py` | `VersionedPromptStore` push/history/rollback |
| Deterministic A/B scoring | `services/ab_runner.py` | `EvaluationHarness` + `CriteriaEvaluator` |
| Registry dispatch | `repository/responders.py` | `lexigram.primitives.Registry` |
| Result-returning handlers | `controllers/api.py` | `Result[T, E]` → auto HTTP status mapping |

## Run it

```bash
cd demos/prompt-lab
PYTHONPATH=src uv run python -m prompt_lab
```

Open http://127.0.0.1:8085. Render previews at any revision, run **A/B**,
then **Rollback** v2 and see its score drop back to v1's baseline.

Override the port without touching yaml: `LEX_WEB__SERVER__PORT=9000`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/templates` | List all variants with their active revision number |
| POST | `/api/render` | Render one variant at an optional revision with supplied vars |
| GET | `/api/history/{variant}` | Revision history for one variant — active revision is flagged |
| POST | `/api/rollback` | Roll one variant back by N revisions; return the new active rev |
| POST | `/api/ab` | Score both variants over the seeded cases (byte-stable) |

## Layout — read it in this order

Start at the composition root and follow the wiring outward.
Each file has teaching comments explaining the Lexigram convention it follows.

| # | File | Lesson |
|---|------|--------|
| 1 | `src/prompt_lab/app.py` | ⭐ Composition root: modules → providers |
| 2 | `src/prompt_lab/main.py` | Lifecycle: `Application.boot(...)` context manager |
| 3 | `src/prompt_lab/di/provider.py` | `register()` (bind) vs `boot()` (initialise); DI patterns |
| 4 | `src/prompt_lab/services/versioning.py` | Versioned prompt store façade |
| 5 | `src/prompt_lab/services/ab_runner.py` | Render → respond → evaluate → compare |
| 6 | `src/prompt_lab/controllers/api.py` | Result-returning handlers → auto HTTP status mapping |
| 7 | `src/prompt_lab/repository/templates.py` | Prompt template construction with variables |
| 8 | `src/prompt_lab/ui/pages.py` | Page controller: serve HTML/assets only, no logic |

```
demos/prompt-lab/
├── src/prompt_lab/
│   ├── app.py                 # ⭐ composition root (start here)
│   ├── main.py                # entry point / lifecycle
│   ├── config.py              # configuration binding
│   ├── di/
│   │   └── provider.py        # DI wiring + boot() assembly
│   ├── controllers/api.py     # JSON API: templates/render/history/rollback/ab
│   ├── repository/            # templates, cases, responders
│   ├── services/
│   │   ├── versioning.py      # VersionedPromptStore façade
│   │   └── ab_runner.py       # deterministic A/B scorer
│   └── ui/                    # pages controller + views/ + static/
├── application.yaml           # web section (LEX_* overrides win)
└── tests/                     # e2e API flow + service tests
```

## Tests

```bash
uv run pytest demos/prompt-lab/tests -q
```

Covers: template rendering at any revision, history/rollback round-trips,
deterministic A/B scoring (v2 always wins), and static asset serving.
