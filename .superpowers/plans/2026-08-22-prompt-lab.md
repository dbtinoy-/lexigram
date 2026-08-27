# Prompt-Lab Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `demos/prompt-lab/` — an offline, deterministic prompt-authoring lab (render preview, version history, rollback, A/B scoring) with a web console, in the house Pattern-2 flat shape plus a standalone swappable `ui/` frontend.

**Architecture:** Flat package `src/prompt_lab/` — root `@module PromptLabModule` imports `PromptModule.configure()` + `WebModule`; templates/responders/cases are pure registries; `VersionedPromptStore` + `EvaluationHarness` constructed directly (pure offline classes); `ABRunner` renders → responds (scripted) → evaluates → compares; `controllers/api.py` serves JSON; `ui/pages.py` static-only (auth-web co-located pattern).

**Tech Stack:** Python 3.11+, `lexigram-ai-prompt`, `lexigram-ai-evaluation`, `lexigram-web`, httpx ASGI testing, pytest-asyncio, ruff.

**Spec:** `.superpowers/specs/2026-08-22-prompt-lab-design.md` — read it first.

## Global Constraints

- Offline only; byte-stable output.
- **Sample contract (verified):** harness runner duck-types —
  `sample.output if hasattr(sample, "output") else ""` (runner.py:49);
  contracts' `EvaluationSample` has no `output` ⇒ local `ScoredSample`
  frozen dataclass mirroring it plus `output: str`.
- **Template contract (verified):** every `{var}` must be declared via
  `variables=[...]` or `validate()` raises `PromptValidationError`
  (chat.py:76-98). `ChatPromptTemplate(name, system=, user=,
  variables=[...], version="…")`; render via `render(**kwargs)` returning
  message dicts, or `render_as_string(**kwargs)`.
- Absolute imports; Google docstrings; full annotations; files <500 LOC.
- Dual sys-path conftest (src + demo root).
- Commits: emoji conventional format, pathspec commits only; `git status --short` first.
- Scoped runs: `uv run pytest demos/prompt-lab/tests -q`. Port default **8085**, env `PROMPT_LAB_PORT`.

---

### Task 1: Scaffold + templates

**Files:**
- Create: `demos/prompt-lab/conftest.py`, `src/prompt_lab/__init__.py`, `tests/__init__.py`
- Create: `src/prompt_lab/templates.py`
- Test: `tests/test_templates.py`

**Interfaces:**
- Produces: `build_v1() -> ChatPromptTemplate`; `build_v2() -> AbstractPromptTemplate` (few-shot variant); `TEMPLATES: dict[str, Callable[[], AbstractPromptTemplate]]` keyed `"v1"`/`"v2"`; `VARIANT_LABELS = {"v1": "Terse", "v2": "Empathetic"}`.

- [ ] **Step 1:** conftest identical in shape to support-agent/memory-chat
  (dual shim, docstrings) with memory-chat paths swapped to
  `demos/prompt-lab`. Docstring-only `__init__` files for
  `src/prompt_lab` (`"""Prompt authoring lab demo."""`), `ui`,
  `ui/pages`, `tests`.

- [ ] **Step 2: Write the failing test**

```python
"""Tests for template construction and validation."""

from __future__ import annotations

import pytest

from lexigram.ai.prompt.exceptions import PromptValidationError

from prompt_lab.templates import TEMPLATES


class TestTemplates:
    def test_v1_declares_variables_and_renders(self) -> None:
        tpl = TEMPLATES["v1"]()

        assert set(tpl.get_variables()) == {"issue", "tone"}
        rendered = tpl.render(issue="late parcel", tone="neutral")
        text = str(rendered)
        assert "late parcel" in text

    def test_v2_includes_examples(self) -> None:
        tpl = TEMPLATES["v2"]()
        text = str(tpl.render(issue="late parcel", tone="warm"))
        assert "happy to help" in text.lower()

    def test_undeclared_variable_fails_validation(self) -> None:
        from lexigram.ai.prompt.template.chat import ChatPromptTemplate

        bad = ChatPromptTemplate(
            "bad", user="Hello {undeclared}", variables=[],
        )
        with pytest.raises(PromptValidationError):
            bad.validate()

    def test_variant_labels(self) -> None:
        assert set(TEMPLATES) == {"v1", "v2"}
```

- [ ] **Step 3:** Run → FAIL (`prompt_lab.templates` missing).

- [ ] **Step 4: Implement**

`src/prompt_lab/templates.py`:
```python
"""The two support-reply prompt variants under iteration."""

from __future__ import annotations

from collections.abc import Callable

from lexigram.ai.prompt.template.base import AbstractPromptTemplate
from lexigram.ai.prompt.template.chat import ChatPromptTemplate
from lexigram.ai.prompt.variables import PromptVariable  # pin: exact module at impl

_VARS = [
    PromptVariable(name="issue"),
    PromptVariable(name="tone"),
]

_V2_EXAMPLES = (
    "Customer: My parcel is two weeks late.\n"
    "Agent: I'm so sorry about the delay — I'm happy to help you track "
    "it down right now.\n\n"
    "Customer: This refund process is confusing.\n"
    "Agent: Totally understandable! Happy to help walk you through it "
    "step by step."
)


def build_v1() -> AbstractPromptTemplate:
    """Terse instruction template."""
    return ChatPromptTemplate(
        "support-v1",
        system=(
            "You are a terse support agent. Answer in one sentence."
        ),
        user="Issue: {issue}\nTone: {tone}\nAnswer:",
        variables=_VARS,
        version="1",
    )


def build_v2() -> AbstractPromptTemplate:
    """Empathetic few-shot template."""
    return ChatPromptTemplate(
        "support-v2",
        system=(
            "You are a warm support agent. Acknowledge feelings, then "
            "help. Follow the examples.\n\n" + _V2_EXAMPLES
        ),
        user="Issue: {issue}\nTone: {tone}\nAnswer:",
        variables=_VARS,
        version="1",
    )


TEMPLATES: dict[str, Callable[[], AbstractPromptTemplate]] = {
    "v1": build_v1,
    "v2": build_v2,
}

VARIANT_LABELS = {"v1": "Terse", "v2": "Empathetic"}
```

Pin at implementation: `PromptVariable` import path/signature — check
`experimental/ai/lexigram-ai-prompt/src/lexigram/ai/prompt/variables/`
first; adjust name-only construction accordingly. If v2's inline examples
in `system=` feel wrong once `FewShotPromptTemplate`'s real constructor
is inspected, switch build_v2 to it — behavior contract stays "rendered
text contains example phrases".

- [ ] **Step 5:** Run → PASS (4). **Step 6:** Commit
  `✨ feat(demos): scaffold prompt-lab with prompt variants`

---

### Task 2: Versioning wrapper

**Files:**
- Create: `src/prompt_lab/versioning.py`
- Test: `tests/test_versioning.py`

**Interfaces:**
- Consumes: `VersionedPromptStore(max_versions=N)` from `lexigram.ai.prompt.registry.versioned`.
- Produces: `LabVersions(store)` managing keys `"support-v1"`/`"support-v2"` with `seed() -> None` (pushes v1 rev1, v2 rev2, v2 rev3 wording tweak), `active(variant) -> tuple[int, template]`, `history(variant) -> list[dict]`, `rollback(variant, steps=1) -> int` (returns new active rev), `get_revision(variant, rev) -> AbstractPromptTemplate`.

- [ ] **Step 1: Write the failing test**

```python
"""Tests over the versioned prompt store wrapper."""

from __future__ import annotations

import pytest

from prompt_lab.templates import TEMPLATES
from prompt_lab.versioning import LabVersions


@pytest.fixture
def versions() -> LabVersions:
    lv = LabVersions(max_versions=10)
    lv.seed(TEMPLATES)
    return lv


class TestLabVersions:
    def test_seed_pushes_three_revisions(self, versions) -> None:
        assert len(versions.history("v1")) == 1
        assert len(versions.history("v2")) == 2

    def test_active_defaults_to_latest(self, versions) -> None:
        rev, _tpl = versions.active("v2")
        assert rev == 2

    def test_get_revision_fetches_specific(self, versions) -> None:
        _, first = versions.get_revision("v2", 1)
        assert "even more warmth" not in str(first.render(issue="x", tone="y"))

    def test_rollback_moves_pointer_back(self, versions) -> None:
        new_rev = versions.rollback("v2", steps=1)
        assert new_rev == 1

    def test_history_entries_have_rev_and_version_string(
        self, versions,
    ) -> None:
        entry = versions.history("v2")[0]
        assert {"rev", "version"} <= set(entry)
```

- [ ] **Step 2:** Run → FAIL.

- [ ] **Step 3: Implement**

`src/prompt_lab/versioning.py`:
```python
"""Revision management for the two prompt variants."""

from __future__ import annotations

from typing import Any

from lexigram.ai.prompt.registry.versioned import VersionedPromptStore
from lexigram.ai.prompt.template.base import AbstractPromptTemplate

_STORE_KEY = {"v1": "support-v1", "v2": "support-v2"}


class LabVersions:
    """Variant-keyed façade over VersionedPromptStore."""

    def __init__(self, max_versions: int = 10) -> None:
        self._store = VersionedPromptStore(max_versions=max_versions)

    def seed(self, factories: dict[str, Any]) -> None:
        """Push v1 rev1, v2 rev2 (empathy tweak), keeping rev1 as base."""
        self._store.push(factories["v1"]())
        self._store.push(factories["v2"]())
        warmed = factories["v2"]()
        warmed.description = "adds even more warmth"
        self._store.push(warmed)

    def active(self, variant: str) -> tuple[int, AbstractPromptTemplate]:
        """Current revision number and template for a variant key."""
        tpl = self._store.get(_STORE_KEY[variant])
        entries = self._store.list_versions(_STORE_KEY[variant])
        return int(entries[-1]["rev"]), tpl

    def get_revision(
        self, variant: str, rev: int,
    ) -> tuple[int, AbstractPromptTemplate]:
        entry = self._store.get_version(_STORE_KEY[variant], rev)
        return rev, entry

    def rollback(self, variant: str, steps: int = 1) -> int:
        tpl = self._store.rollback(_STORE_KEY[variant], steps=steps)
        entries = self._store.list_versions(_STORE_KEY[variant])
        return int(entries[-1]["rev"]) if tpl else 0

    def history(self, variant: str) -> list[dict[str, Any]]:
        return list(self._store.list_versions(_STORE_KEY[variant]))
```

**Pin before coding:** `VersionedPromptStore.push/get/get_version/
rollback/list_versions` signatures against
`experimental/ai/lexigram-ai-prompt/src/lexigram/ai/prompt/registry/versioned.py:47/:74/:90/:105/:136` —
adjust call shapes (`rev` field name inside history dicts etc.) to the
actual source; do not guess field names in tests, derive them from
`list_versions()` output during implementation and update assertions to
match reality.

- [ ] **Step 4:** Run → PASS (5). **Step 5:** Commit
  `✨ feat(demos): add prompt-lab versioning wrapper`

---

### Task 3: Responders, cases, ABRunner

**Files:**
- Create: `src/prompt_lab/responders.py`, `cases.py`, `ab_runner.py`
- Test: `tests/test_ab_runner.py`

**Interfaces:**
- Produces: `RESPONDERS: dict[str, Callable[[str], str]]`; `CASES: list[Case]` where `Case(id, question, reference)`; `ABRunner(versions_factory, harness=None)` with `run_all() -> dict` shape `{"variants": {key: {"average_score": float, "passed": int, "total": int}}, "winner": str}` — byte-stable across invocations.

- [ ] **Step 1: Write the failing test**

```python
"""Deterministic A/B scoring tests."""

from __future__ import annotations

from prompt_lab.ab_runner import ABRunner
from prompt_lab.responders import RESPONDERS


class TestResponders:
    def test_v1_clipped_style(self) -> None:
        out = RESPONDERS["v1"]("Where is my order?")
        assert out.startswith("Order issue noted.")
        assert "happy to help" not in out

    def test_v2_warm_style(self) -> None:
        out = RESPONDERS["v2"]("Where is my order?")
        assert "happy to help" in out


class TestABRunner:
    def setup_method(self) -> None:
        from prompt_lab.versioning import LabVersions
        from prompt_lab.templates import TEMPLATES

        versions = LabVersions(max_versions=10)
        versions.seed(TEMPLATES)
        self.runner = ABRunner(versions=versions)

    def test_scores_are_deterministic(self) -> None:
        assert self.runner.run_all() == self.runner.run_all()

    def test_v2_outscores_v1(self) -> None:
        report = self.runner.run_all()
        scores = {k: v["average_score"] for k, v in report["variants"].items()}
        assert scores["v2"] > scores["v1"]

    def test_winner_is_v2(self) -> None:
        assert self.runner.run_all()["winner"] == "v2"

    def test_totals_cover_all_cases(self) -> None:
        report = self.runner.run_all()
        assert all(v["total"] == 4 for v in report["variants"].values())
```

- [ ] **Step 2:** Run → FAIL.

- [ ] **Step 3: Implement**

`responders.py`:
```python
"""Variant-keyed canned completion styles (registry dispatch, no LLM)."""

from __future__ import annotations

from collections.abc import Callable

_RESPONDER_IMPLS: dict[str, Callable[[str], str]] = {
    "v1": lambda question: f"Order issue noted. Ticket filed for: {question}",
    "v2": lambda question: (
        f"I'm so sorry about the trouble — I'm happy to help with: "
        f"{question} Let's sort it together."
    ),
}

RESPONDERS = dict(_RESPONDER_IMPLS)
```

`cases.py`:
```python
"""Seeded evaluation cases; references favor v2 deterministically."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    """One scored scenario."""

    id: str
    question: str
    reference: str


CASES: list[Case] = [
    Case("billing", "My card was charged twice.", "happy to help"),
    Case("shipping", "Where is my order?", "happy to help"),
    Case("bug", "The app crashes on login.", "happy to help"),
    Case("feature", "Can you add dark mode?", "happy to help"),
]

CRITERIA = [{"type": "contains", "expected": "happy to help"}]
```

`ab_runner.py`:
```python
"""Render → respond → evaluate → compare, fully offline."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator
from lexigram.ai.evaluation.harness.runner import EvaluationHarness
from lexigram.contracts.ai.evaluation import EvaluationDataset

from prompt_lab.cases import CASES, CRITERIA


@dataclass(frozen=True)
class ScoredSample:
    """Harness duck-types on attribute presence (runner.py:49)."""

    id: str
    input: str
    output: str
    reference: str
    metadata: dict = None  # type: ignore[assignment]


class ABRunner:
    """Scores both variants over CASES via CriteriaEvaluator."""

    def __init__(self, versions, harness: EvaluationHarness | None = None) -> None:
        self._versions = versions
        self._harness = harness or EvaluationHarness(pass_threshold=0.8)

    async def run_all_async(self) -> dict:
        """Async core used by both the sync wrapper and the API layer."""
        evaluator = CriteriaEvaluator(criteria=CRITERIA)
        variants_report: dict[str, dict] = {}
        for variant in ("v1", "v2"):
            _, template = self._versions.active(variant)
            samples: list[ScoredSample] = []
            for case in CASES:
                rendered = template.render_as_string(issue=case.question, tone="neutral")
                samples.append(
                    ScoredSample(
                        id=case.id,
                        input=rendered,
                        output=RESPONDERS[variant](case.question),
                        reference=case.reference,
                        metadata={},
                    ),
                )
            dataset = EvaluationDataset(
                name=f"ab-{variant}", samples=samples, metadata={},
            )
            result = await self._harness.run(dataset, evaluator)
            if result.is_err():
                raise RuntimeError(f"harness failed: {result.unwrap_err()}")
            report = result.unwrap()
            passed = sum(
                1 for r in report.results if r.score >= report.metadata["pass_threshold"]
            )
            variants_report[variant] = {
                "average_score": round(report.average_score, 4),
                "passed": passed,
                "total": report.total_samples,
            }
        winner = max(
            variants_report, key=lambda k: variants_report[k]["average_score"],
        )
        return {"variants": variants_report, "winner": winner}


# Sync convenience for tests; API layer awaits run_all_async directly.
def run_all_sync_compat(runner: ABRunner) -> dict:  # pragma: no cover
    import asyncio

    return asyncio.run(runner.run_all_async())
```

Test-file adjustment while writing Step 1: make tests async
(`@pytest.mark.asyncio async def ...`) calling `await runner.run_all()`;
rename method to `run_all()` async (drop `_async` suffix and the sync
compat helper entirely — final file has only `async def run_all(self)`).
`ScoredSample.metadata` default must be `field(default_factory=dict)`
with `dataclasses.field`, not `None`.

- [ ] **Step 4:** Run → PASS (6). **Step 5:** Commit
  `✨ feat(demos): add prompt-lab ab scoring`

---

### Task 4: Provider + module + JSON API (boot path)

**Files:**
- Create: `di/__init__.py`, `di/provider.py`, `module.py`, `controllers/__init__.py`, `controllers/api.py`
- Modify: `conftest.py` (append `app`/`client` fixtures — identical pattern to support-agent Task 4 Step 1, substituting `from prompt_lab.module import PromptLabModule`, name `"prompt-lab-test"`).
- Test: `tests/test_api.py`

**Interfaces:**
- Produces: `LabProvider`; `PromptLabModule.configure(port=None)` exports `[ABRunner]`; API `GET /api/templates`, `POST /api/render {variant, rev?, vars{}}`, `GET /api/history/{variant}`, `POST /api/rollback {variant, steps?}`, `POST /api/ab`; `LabApiController(versions: LabVersions, runner: ABRunner)`.

- [ ] **Step 1: Write failing API tests**

```python
"""End-to-end tests over the JSON API."""

from __future__ import annotations

import httpx


async def test_templates_listed(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/templates")).json()
    assert {t["variant"] for t in body} == {"v1", "v2"}
    assert all({"variant", "label", "active_rev"} <= set(t) for t in body)


async def test_render_current(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/render",
        json={"variant": "v1", "vars": {"issue": "late parcel", "tone": "neutral"}},
    )
    body = response.json()
    assert response.status_code == 200
    assert "late parcel" in body["rendered"]


async def test_render_unknown_variable_is_400(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/render",
        json={"variant": "v1", "vars": {"bogus": "x"}},
    )
    assert response.status_code == 400


async def test_history_and_rollback(client: httpx.AsyncClient) -> None:
    history = (await client.get("/api/history/v2")).json()["entries"]
    assert len(history) == 2

    rolled = await client.post("/api/rollback", json={"variant": "v2", "steps": 1})
    assert rolled.json()["active_rev"] == 1

    after = (await client.get("/api/history/v2")).json()["entries"]
    assert len(after) == 2  # history preserved; pointer moved


async def test_ab_endpoint_stable(client: httpx.AsyncClient) -> None:
    first = (await client.post("/api/ab")).json()
    second = (await client.post("/api/ab")).json()
    assert first == second
    assert first["winner"] == "v2"


async def test_unknown_variant_is_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/history/nope")
    assert response.status_code == 404
```

- [ ] **Step 2:** Run → FAIL.

- [ ] **Step 3: Implement provider/module/api**

`di/provider.py`:
```python
"""DI wiring for the prompt-lab demo (internal)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

from prompt_lab.ab_runner import ABRunner
from prompt_lab.templates import TEMPLATES
from prompt_lab.versioning import LabVersions


class LabProvider(Provider):
    """Binds seeded versions and assembles the runner at boot."""

    name = "prompt-lab"

    def __init__(self) -> None:
        super().__init__()
        self._versions = LabVersions(max_versions=10)
        self._runner: ABRunner | None = None

    def _get_runner(self) -> ABRunner:
        if self._runner is None:
            raise RuntimeError("LabProvider has not been booted yet")
        return self._runner

    async def register(
        self, container: ContainerRegistrarProtocol,
    ) -> None:
        """Seed revisions eagerly; the runner resolves in boot()."""
        self._versions.seed(TEMPLATES)
        container.singleton(LabVersions, instance=self._versions)
        container.singleton(ABRunner, factory=self._get_runner)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Assemble the runner over the seeded store."""
        self._runner = ABRunner(versions=self._versions)
```

`module.py`:
```python
"""Root module for the prompt-lab demo."""

from __future__ import annotations

import os

from lexigram.di.module import DynamicModule, Module, module
from lexigram.ai.prompt.module import PromptModule
from lexigram.web import ServerConfig, SecurityConfig, WebConfig, WebModule

from prompt_lab.ab_runner import ABRunner
from prompt_lab.controllers.api import LabApiController
from prompt_lab.di.provider import LabProvider
from prompt_lab.ui.pages import LabPageController


@module()
class PromptLabModule(Module):
    """Prompt authoring lab with deterministic A/B scoring."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        selected_port = port if port is not None else int(
            os.environ.get("PROMPT_LAB_PORT", "8085")
        )
        return DynamicModule(
            module=cls,
            imports=[
                PromptModule.configure(),
                WebModule.configure(
                    controllers=[LabApiController, LabPageController],
                    web_config=WebConfig(
                        server=ServerConfig(host="127.0.0.1", port=selected_port),
                        security=SecurityConfig(enable_csrf=False),
                    ),
                ),
            ],
            providers=[LabProvider],
            exports=[ABRunner],
        )


__all__ = ["PromptLabModule"]
```

`controllers/__init__.py`: docstring only
(`"""JSON API for the prompt lab — no HTML lives here."""`).

`controllers/api.py`:
```python
"""JSON API for the prompt lab console — no HTML lives here."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.ai.prompt.exceptions import (
    PromptNotFoundError,
    PromptRenderError,
    PromptValidationError,
)
from lexigram.web import Controller, get, post

from prompt_lab.ab_runner import ABRunner
from prompt_lab.templates import VARIANT_LABELS
from prompt_lab.versioning import LabVersions

_RENDER_ERRORS = (PromptNotFoundError, PromptRenderError)


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


class LabApiController(Controller):
    """Endpoints consumed by ui/static/app.js."""

    def __init__(self, versions: LabVersions, runner: ABRunner) -> None:
        self._versions = versions
        self._runner = runner

    @get("/api/templates")
    async def templates(self, request: Request) -> JSONResponse:
        rows = []
        for variant in ("v1", "v2"):
            rev, _tpl = self._versions.active(variant)
            rows.append(
                {
                    "variant": variant,
                    "label": VARIANT_LABELS[variant],
                    "active_rev": rev,
                },
            )
        return JSONResponse(rows)

    @post("/api/render")
    async def render(self, request: Request) -> JSONResponse:
        """Render one variant at an optional revision with supplied vars."""
        data = await request.json()
        variant = str(data.get("variant", ""))
        if variant not in ("v1", "v2"):
            return _error(f"unknown variant: {variant!r}", 404)

        vars_in = {str(k): str(v) for k, v in dict(data.get("vars", {})).items()}
        try:
            if "rev" in data and data["rev"] is not None:
                _rev, template = self._versions.get_revision(variant, int(data["rev"]))
            else:
                _rev, template = self._versions.active(variant)
            missing = [v for v in template.get_variables() if v not in vars_in]
            if missing:
                return _error(f"missing variables: {missing}", 400)
            rendered = template.render_as_string(**vars_in)
        except _RENDER_ERRORS as exc:
            return _error(str(exc), 400)
        except PromptValidationError as exc:
            return _error(str(exc), 400)
        return JSONResponse({"rendered": rendered})

    @get("/api/history/{variant}")
    async def history(self, request: Request) -> JSONResponse:
        variant = request.path_params["variant"]
        if variant not in ("v1", "v2"):
            return _error(f"unknown variant: {variant!r}", 404)
        return JSONResponse({"entries": self._versions.history(variant)})

    @post("/api/rollback")
    async def rollback(self, request: Request) -> JSONResponse:
        data = await request.json()
        variant = str(data.get("variant", ""))
        if variant not in ("v1", "v2"):
            return _error(f"unknown variant: {variant!r}", 404)
        steps = int(data.get("steps", 1))
        active_rev = self._versions.rollback(variant, steps=steps)
        return JSONResponse({"active_rev": active_rev})

    @post("/api/ab")
    async def ab(self, request: Request) -> JSONResponse:
        """Score both variants over the seeded cases (byte-stable)."""
        return JSONResponse(await self._runner.run_all())


__all__ = ["LabApiController"]
```

- [ ] **Step 4:** Run full suite → ALL PASS.- [ ] **Step 4:** Run full suite → ALL PASS. **Step 5:** Commit
  `✨ feat(demos): wire prompt-lab module with JSON API`

---

### Task 5: Lab UI (assets + page controller)

**Files:** `src/prompt_lab/ui/{__init__.py, pages.py}`, `src/prompt_lab/ui/views/lab.html`, `src/prompt_lab/ui/static/{app.js,style.css}`, `tests/test_pages.py`

**Interfaces:** `/` view; `/static/*`; ids `preview`, `preview-form` (`issue`,`tone`,`rev` inputs), `variant` buttons `data-variant`, `history-list`, `rollback-btn`, `ab-btn`, `ab-body`, `error`.

- [ ] **Step 1: Failing page tests** — markers `"Prompt Lab"`,
  `data-variant="v1"`, `data-variant="v2"`, ids above; static content
  types (identical shape to prior demos).
- [ ] **Step 2:** Run → FAIL (404s).
- [ ] **Step 3: Assets** — `lab.html`: header, variant buttons, preview form (inputs `#issue` default "late parcel", `#tone` default "neutral", `#rev` placeholder optional), `<pre id="preview">`, `<ul id="history-list">`, `#rollback-btn`, `#ab-btn`, `<table>` with `#ab-body`, `#error`.
  `app.js`: state `variant='v1'`; `loadTemplates()` fills buttons labels+active_rev; `render()` POSTs `/api/render {variant, rev?, vars}` into `#preview`; history GET fills list; rollback POSTs then reloads history+preview; `runAb()` POSTs `/api/ab` rendering per-variant rows + winner line; error path shows `#error`. Same escapeHtml/show/hide helpers as prior demos. CSS reuses support-agent palette (copy base rules, rename comment header).
  `src/prompt_lab/ui/pages.py`: `LabPageController` — byte-shape identical to `ConsolePageController`/`ChatPageController` serving `lab.html` (UI_ROOT parents[1]; three routes).
- [ ] **Step 4:** Full suite → ALL PASS. **Step 5:** Commit
  `✨ feat(demos): add prompt-lab console UI`

---

### Task 6: Server entry point

**Files:** `src/prompt_lab/main.py`, `src/prompt_lab/__main__.py`

- [ ] **Step 1:** `main.py` mirrors support-agent's entry exactly;
  substitutions: name `"prompt-lab"`, `PromptLabModule`, env
  `PROMPT_LAB_PORT`, default `8085`, description "Prompt lab demo".
  `__main__.py` calls `main()` under `sys.exit`.
- [ ] **Step 2: Manual smoke**

```bash
PYTHONPATH=demos/prompt-lab/src timeout 5 uv run python -m prompt_lab --port 8090 &
sleep 3
curl -s http://127.0.0.1:8090/api/templates
curl -s -X POST http://127.0.0.1:8090/api/render -H 'Content-Type: application/json' -d '{"variant":"v1","vars":{"issue":"late parcel","tone":"neutral"}}'
curl -s -X POST http://127.0.0.1:8090/api/ab | head -c 400
curl -s http://127.0.0.1:8090/ | head -3
```
Expected: two variants listed; rendered contains "late parcel"; ab JSON
winner v2; HTML head.

- [ ] **Step 3:** Full suite green. **Step 4:** Commit
  `✨ feat(demos): add prompt-lab server entry point`

---

### Task 7: README + Makefile gating + gates

**Files:** `demos/prompt-lab/README.md`, `Makefile:114-115`, `demos/README.md`

- [ ] **Step 1:** Makefile append `demos/prompt-lab/tests` / `demos/prompt-lab` (diff-first).
- [ ] **Step 2:** `demos/README.md` section:

```markdown
### ✍️ [prompt-lab](prompt-lab/) — prompt authoring & A/B, zero LLM

Iterate on a support-reply prompt like a scientist:

- 🧬 **Two variants** — terse v1 vs empathetic few-shot v2
- 🕘 **Real versioning** — push revisions, inspect history, roll back live
- 🎯 **Deterministic A/B** — criteria-scored over four seeded cases, byte-stable
- 🖥️ **Lab console** — render previews at any revision side-by-side with scores
```

Demo-local README expands layout/run (:8085)/gotchas.

- [ ] **Step 3:** Gates:

```bash
uv run ruff check demos/prompt-lab && uv run ruff format --check demos/prompt-lab
make test-demos && make verify-demos
find demos/prompt-lab -name "*.py" | xargs wc -l | sort -n   # all <500
git status --short
```

- [ ] **Step 4:** Commit `📝 docs(demos): document prompt-lab and gate make targets` (pathspec: demos/README.md demos/prompt-lab/README.md Makefile).

---

## Self-Review Notes

- Spec coverage: flat layout ✓; templates incl. declared-variable validation ✓(T1); VersionedPromptStore wrapper w/ seed 3-revisions + rollback pointer ✓(T2); scripted responders + 4 cases + duck-typed ScoredSample + deterministic winner ✓(T3); API surface matches spec §4 table ✓(T4); ui/pages named-by-page ✓(T5); ports/env ✓(T6); Makefile/README ✓(T7).
- Type consistency: `Case(id,question,reference)` shared by cases/runner/tests; `ScoredSample` local dataclass per verified duck-typing; `LabVersions.active/get_revision/rollback/history` consistent between service, API, UI flows.
- Intentional traps flagged inline (delete-before-save): `run_all_sync_compat` helper and `metadata: None` default — final code uses async `run_all()` and `field(default_factory=dict)`.
- Known risks pinned: `PromptVariable` ctor/import path (variables/ pkg); `VersionedPromptStore` signatures + history-dict fields (versioned.py:47/:74/:90/:105/:136); `FewShotPromptTemplate` optional swap for build_v2; `ChatPromptTemplate.render_as_string` availability (chat.py:138).
