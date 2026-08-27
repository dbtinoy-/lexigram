# Plan: Lexigram Builder (`experimental/apps/lexigram-builder`)

> Spec: [`specs/2026-08-25-lexigram-builder-design.md`](../specs/2026-08-25-lexigram-builder-design.md).
> Pkg `lexigram-builder`, ns `lexigram.builder`, v0.1.7001, server port 7200.
> Conventions: AGENTS.md throughout — TDD per task (tests in the same
> commit), offline tests only (`-m "not integration"`), files < 500 LOC,
> absolute imports via package `__init__.py`, Result for domain failures.

> **Task 0 — recon: DONE (2026-08-25, findings pinned in spec rev 2).**
> Key verified facts the tasks below rely on:
> - `WebModule.configure(controllers=, discover=, host=, port=, **kwargs)`
>   — no prefix/middlewares kwargs; extras forward to `WebProvider`
>   (`web/module.py:13-41`).
> - Controllers: plain class + `@get/@post/...` storing `_route_config`;
>   params bound by annotation (path params by name), DI-by-annotation,
>   explicit markers in `web/routing/parameters.py`; canonical demo:
>   `demos/event-driven-orders/src/orders/controllers/api.py`.
> - Result→HTTP is automatic (`Err` ⇒ ProblemDetail via result bridge;
>   registry statuses; override via `@error_status`,
>   `web/routing/result_bridge.py`). `ProblemDetail` exported from
>   `lexigram.web`.
> - SSE: use `lexigram.web.sse.EventSourceResponse` /
>   `SSEHeartbeatScheduler` (admin's hand-rolled StreamingResponse is the
>   fallback shape, `experimental/apps/lexigram-admin/.../progress.py:140`).
> - SQL: entities are **Pydantic** models; repositories subclass
>   `GenericRepository[Entity, K]`
>   (`lexigram.sql.repositories.generic_repository`) over
>   `DatabaseProviderProtocol`; `DatabaseModule.configure(config=<url|DatabaseConfig>)`;
>   alembic dirs are consumer-owned; dual-URL rule
>   (runtime `sqlite:///`, migrations `sqlite+aiosqlite:///`);
>   reference trio: `shorts-creator/src/shorts_creator/{models,repositories,controllers}`.
> - `lexigram.codegen` IDENTIFIED (2026-08-25), CLEANED 2026-08-26
>   (commits `63b98ca`, `8c08a56`): jinja2 is now an optional extra,
>   pure helpers live in contracts, and `ModelGenerator`/`ServiceGenerator`
>   plus the sql re-export shims were RETIRED. The codegen-uplift program
>   (`specs/2026-08-26-codegen-uplift-design.md`) adds `StagedGeneration`,
>   `GenerationOptions`/`CollisionPolicy`, `finalize()` and
>   `assert_generated_tree`. Builder consumes all of these — **uplift
>   Tasks 1–3 must land before builder Task 3**.
> - Scaffold: hatchling; ruff `extend = "../../../pyproject.toml"`
>   (apps depth); per-package pytest ini re-declares markers
>   (`--strict-markers` at root) with own scoped cov addopts;
>   namespace shim + py.typed at both levels; version via
>   `importlib.metadata.version("lexigram-builder")` in constants.py.
> - Root registration REQUIRED: root pyproject `testpaths` +
>   `pythonpath` enumerated lists; importlinter enumerates members
>   explicitly (no wildcard for apps).

**Goal:** canvas graph → generated standalone Lexigram CRUD project →
subprocess-tested and preview-booted, streamed over native SSE; SSR UI.
**Architecture:** BuilderModule (WebModule + BuilderProvider) · fs-backed
ProjectService · GenerationService pipeline behind a SubprocessRunner
protocol · PreviewService process/SSE owner (EventSourceResponse) ·
lexigram-ui SSR pages + vanilla canvas island (`static/canvas.js`).

### Task 1: Package scaffold
- [ ] pyproject (deps bare-name floors: `lexigram>=0.1.4`,
      `lexigram-contracts>=0.1.4`, `lexigram-web>=0.1.x`,
      `lexigram-sql>=0.1.x`), entry point
      `[project.entry-points."lexigram.modules"] builder = …`,
      ruff/mypy sections per cli precedent, pytest ini
      (`asyncio_mode="auto"`, markers incl. integration, cov addopts),
      wheel packages = ["src/lexigram"], namespace shim + py.typed.
- [ ] Root registration: `[tool.uv.sources]` line, root `testpaths` +
      `pythonpath` entries, `.gitignore`.
- [ ] Tests first: importing `BuilderModule`, `configure()` returns
      DynamicModule exporting controller contract; `/builder/health`
      returns 200 (TestClient on WebProvider.starlette pattern).
- [ ] Implement module.py, di/provider.py (`config_key="builder"`),
      constants.py (+`__version__`), exceptions.py, types.py, controller
      stub. Gates. Commit `✨ feat(builder): scaffold lexigram-builder package`.

### Task 2: Graph domain
- [ ] Tests: model construction; every validation rule from spec §4
      (dup entity name, dup field, bad identifier/type/port, route w/o
      edge, missing/multiple app_settings) asserts diagnostic
      {node_id, code}; happy minimal graph validates clean.
- [ ] Implement graph/models.py (frozen dataclasses),
      graph/palette.py (kind registry + port rules),
      graph/validation.py returning `Result[ValidatedGraph, …]`.
      Commit `✨ feat(builder): graph domain + node-scoped validation`.

### Task 3: Codegen engine
> Prerequisite: codegen-uplift Tasks 1–3 merged (StagedGeneration,
> GenerationOptions/CollisionPolicy, finalize seam available in core).

- [ ] Golden-file snapshot tests: minimal User graph → exact project tree
      (byte-stable); per-emitter units (pydantic entity model,
      GenericRepository wrapper pair, @error_status controller,
      alembic dir + revision, pyproject with relative uv.sources,
      main/module wiring using DatabaseModule.configure(config=…));
      determinism test (generate twice, compare bytes); GenerationResult
      folding test (created/skipped files → node diagnostics). Reuse
      `lexigram-testing.assert_generated_tree` at the project-writer level
      via a thin GeneratorProtocol adapter if it fits; otherwise local
      snapshots.
- [ ] Implement gen/emitters/* + gen/templates/* + writer.py as a thin
      orchestrator over core `StagedGeneration`: stage per node →
      `commit(GenerationOptions(policy=CollisionPolicy.OVERWRITE))`;
      ruff-format written files via `finalize()`. Commit
      `✨ feat(builder): staged project codegen`.

### Task 4: Services
- [ ] Tests w/ fake SubprocessRunner (scripted outcomes): ProjectService
      fs CRUD + atomic save; GenerationService step ordering
      writing→syncing→testing→booting→live, failure ⇒ preview killed +
      diagnostics surfaced; PreviewService broadcast fan-out + heartbeat +
      idempotent stop. Package-local `protocols.py` for SubprocessRunner
      seam (importlinter-scoped per house contract).
- [ ] Implement services/{projects,generation,preview}.py (logging via
      `get_logger`, structured kvs). Commit
      `✨ feat(builder): project/generation/preview services`.

### Task 5: HTTP API
- [ ] Controller tests (AsyncClient + ASGITransport / TestClient shapes):
      palette schema shape; project CRUD; PUT invalid graph → 422
      ProblemDetail + diagnostics body (result bridge maps Err
      automatically; `@error_status` where registry default differs);
      generate kicks async pipeline (fake runner); SSE stream emits phase
      events end-to-end via EventSourceResponse; proxy request forwards
      method/path/body to live preview URL; stop endpoint.
- [ ] Wire controllers into BuilderModule exports. Commit
      `✨ feat(builder): /builder REST + SSE API`.

### Task 6: End-to-end proof (marker `integration`, offline)
- [ ] Real subprocesses into tmp projects dir: generate sample User
      project → `uv run pytest -q` inside it green → preview boots →
      `/health` ok → proxied `POST /users` → 201 → stop kills tree
      (assert pid gone). Runs via `-m integration`; never in the
      default `-m "not integration"` gate.
- [ ] Commit `✅ test(builder): generation e2e proof`.

### Task 7: SSR UI — lexigram-ui pages + canvas island
> Revised 2026-08-26: Vite SPA replaced by admin-style SSR after the
> lexigram-ui/admin recon (spec §2, §3, §7b). No Node/npm anywhere.

- [ ] Recon: pin lexigram-ui exports actually used (el/render_to_string,
      layouts shell, form_field/modal/badge organisms, realtime/SSE
      console helper) + how admin structures page controllers.
- [ ] Tests first: GET `/builder` index and
      `/builder/projects/{name}/app` return 200 with markers (layout
      shell, island script tag, palette entries); htmx create-project
      form flow; canvas-page renders inspector forms per kind from the
      §4 schema.
- [ ] Implement ui/{pages,panels}.py (lexigram-ui component builders),
      controllers/pages_controller.py, static/canvas.js island
      (drag/wire/pan for 3 kinds; fetch sync to graph API; zero deps,
      no build), static route registration; wire BuilderModule imports +
      UiModule? (per lexigram-ui module usage in admin).
- [ ] Manual loop check per spec acceptance criteria. Commit
      `✨ feat(builder): ssr canvas ui`.

### Task 8: Governance + gates
- [ ] README.md (run instructions, screenshots deferred);
      `.importlinter`: enumerate `lexigram.builder` in Contract 4
      composite/app-style exclusion doc + `local-protocols-scoped` entry
      (forbidden `lexigram.builder.protocols` cross-package, owner
      exemption); optional root `TYPED_PKGS` += builder.
- [ ] Full chain: `ruff format --check .` + `ruff check .` + mypy on new
      src + `uv run pytest experimental/apps/lexigram-builder/tests -m "not integration"`
      from repo root AND package dir; integration e2e once locally;
      `make lint-loc` green.
- [ ] `make version-check` → bump pkg if drifted; update
      `.superpowers/README.md` program index with builder row. Commit
      `🔧 chore(builder): register governance + docs`.
