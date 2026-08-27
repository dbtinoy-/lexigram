# Demo Spec — `prompt-lab` (iterate I: prompt authoring & A/B, web UI)

**Date:** 2026-08-22
**Status:** Draft for review
**Showcases:** `lexigram-ai-prompt` (templates, registry, versioning) + `lexigram-ai-evaluation` (deterministic scoring harness).
**Portfolio position:** Fourth AI demo — first half of the "iterate on quality" story.
**Structure rationale:** Flat house Pattern-2 package. UI present ⇒ auth-web pattern verbatim: `ui/pages.py` co-located with `views/`+`static/`.

---

## 1. Scenario

A team iterates on a support-reply prompt. Variant **v1** is a terse
instruction template; variant **v2** adds empathy instructions and few-shot
examples. The lab renders either variant at any revision, inspects version
history, rolls back, and runs an **A/B evaluation** scoring both variants
over a seeded case set — byte-stable every run.

No LLM: each variant maps to a scripted responder emitting a fixed
completion style (registry dispatch). The demo's point is the prompt
tooling + scoring pipeline.

## 2. Layout

```
demos/prompt-lab/
├── conftest.py                        # sys.path shim (src/) + app/client fixtures
├── README.md
└── src/prompt_lab/
    ├── __init__.py
    ├── main.py                        # python -m prompt lab (see env below)
    ├── module.py                      # @module (see wiring)
    ├── di/provider.py                 # internal provider
    ├── controllers/
    │   ├── __init__.py
    │   └── api.py                     # JSON logic only
    └── ui/                            # auth-web pattern: assets beside static routes
        ├── __init__.py                # docstring only
        ├── pages.py                   # single static-serving controller
        ├── views/
        │   └── lab.html            # variant/rev picker · preview · history · A/B
        └── static/
            ├── app.js
            └── style.css

Port default 8085 via `PROMPT_LAB_PORT`.

## 3. Module wiring

```python
@module()
class PromptLabModule(Module):
    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        return DynamicModule(
            module=cls,
            imports=[
                PromptModule.configure(),   # defaults; templates render themselves
                WebModule.configure(
                    controllers=[LabApiController, LabPageController],
                    web_config=_web_config(port),
                ),
            ],
            providers=[LabProvider],
            exports=[ABRunner],
        )
```

`LabProvider.register()` binds templates + responder registry singletons;
`boot()` resolves nothing external — constructs `VersionedPromptStore(max_versions=5)`
and `EvaluationHarness(pass_threshold=0.8)` directly (pure offline classes)
and assembles `ABRunner`.

**Sample contract (verified):** the evaluation harness duck-types samples —
`sample.output if hasattr(sample, "output") else ""`
(harness/runner.py:49). Contracts' `EvaluationSample` lacks an `output`
field ⇒ `ab_runner.py` defines a local frozen dataclass mirroring
`EvaluationSample` plus `output: str`; the harness consumes it untouched.
No direct-evaluator fallback needed.

## 4. Components

| Component | Implementation |
|---|---|
| `templates.py` | v1: `ChatPromptTemplate("support-v1", system=…, user="…{issue}…{tone}…", variables=[PromptVariable(name="issue"), PromptVariable(name="tone")])` — **every `{var}` must be declared** or `validate()` raises `PromptValidationError` (chat.py:76-98). v2: same + 3 few-shot examples (`InMemoryExampleSelector`). `validate()` exercised at registration |
| `responders.py` | dict registry `variant_key → Callable[[str], str]` — v1 clipped style, v2 warmer style referencing the customer's issue |
| `cases.py` | 4 seeded scenarios (billing, shipping, bug, feature request); references chosen so v2 outscores v1 deterministically (criterion `contains: happy to help` passes only on v2) |
| `ab_runner.py` | Per variant: build dataset of local ScoredSamples (input=rendered prompt, output=responder(prompt), reference=expected traits) → `harness.run(dataset, CriteriaEvaluator(...))` → compare average scores |
| `versioning.py` | Pushes v2 twice (minor wording change = rev 3) so history/rollback show real revisions; `rollback(steps=1)` semantics |
| `api.py` | `GET /api/templates` → names/versions; `POST /api/render {variant, rev?, vars}` → rendered messages (400 unknown variable); `GET /api/history/{variant}`; `POST /api/rollback {variant, steps?}`; `POST /api/ab` → per-case rows + totals + winner |

## 5. Tests

- `test_templates.py` — variable extraction, validation failures,
  rendered structure equality.
- `test_versioning.py` — push ordering, `get_version`, rollback steps,
  `list_versions` shape, max_versions eviction.
- `test_ab_runner.py` — deterministic scores across runs; v2 > v1 on the
  seeded set; post-rollback scores tie back to v1;
  `RunReport.metadata.pass_rate`.
- `test_pages.py` / `test_api.py` — page markers (variant buttons, ids
  preview/history/ab-table), static types; endpoints e2e incl. unknown
  variant ⇒ 404, unknown render variable ⇒ 400.

## 6. Integration

Makefile:114-115 append entries; demos/README.md section (:8085).

## 7. Acceptance criteria

- [ ] Server boots offline at :8085; lab usable.
- [ ] A/B results byte-stable across invocations.
- [ ] `make check-demos` green; ruff/format clean; files <500 LOC;
      changes confined to `demos/**` + `Makefile`.
- [ ] Own commit(s) including tests.

## 8. Gotchas

- `PromptModule` exports only `PromptTemplateProtocol`; do not assume
  richer registry bindings — construct `VersionedPromptStore` directly
  (per §3).
- Template `name` is the registry key; variants need distinct names even
  as revisions of one prompt.
- Keep datasets literal — the package has no dataset loader.
- Rendering errors are typed (`PromptRenderError`,
  `PromptValidationError`) — surface as 400 with reason, never swallowed.
