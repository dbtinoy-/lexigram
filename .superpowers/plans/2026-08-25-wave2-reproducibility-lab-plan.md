# Plan: Reproducibility Lab retrofit (`demos/llm-reproducibility`)

> Conventions: wave-2 overview. New port 7076, pkg unchanged
> (`llm_reproducibility`). Spec: `specs/2026-08-25-demo-reproducibility-lab.md`.
> **Blueprint:** the acceptance checklist in `specs/2026-08-25-demos-code-alignment.md` §6 applies to this retrofit end-to-end.

> **Task 0 — recon:** read current `run_experiment.py` end-to-end and map its
> sections → service methods; confirm which parts already live in
> `src/llm_reproducibility/`; check `.github/workflows/ci.yml` for script
> references. Record mapping table in
> `src/llm_reproducibility/experiment_service.py` docstring.

### Task 1: Extract DigestExperimentService — TDD
- [ ] Failing tests: `run(seed)` returns RunRecord with golden digest fixtures (seed 42 baseline, seed 7, seed 42+ablate); different seeds → different digests; `verify(seed)` returns Ok(identical) on match and Err(DigestDrift{expected, actual}) when tampered; config.yaml loads through service.
- [ ] Extract service from script (no stdout/stdin); script keeps working during transition by delegating.
- [ ] Gates green. Commit feature+tests together: `✨ feat(demos): experiment service with golden digests`.

### Task 2: Web wiring (module/main/controllers) — TDD
- [ ] Tests: ASGI POST /api/runs twice same seed → equal digest chips; GET /api/runs lists both; verify endpoint Ok path; unknown run id → problem detail; module boots on REPRO_PORT with CSRF off.
- [ ] Implement InMemoryRunsStore + RunsController + `module.py` + `main.py` (`serve` default :7076 via env `REPRO_PORT`, `demo` subcommand delegating to old walkthrough output). Existing 4 tests migrated off script internals. Gates. Commit `✨ feat(demos): reproducibility lab API`.

### Task 3: Notebook + script removal, reference sweep
- [ ] `git rm reproducibility.ipynb run_experiment.py`.
- [ ] Update: Makefile smoke line → `python -m llm_reproducibility demo`; `eval-reproduce` target → module invocation preserving `--out`; ci.yml script call if present; demos README bullet/command rows; docs `demos/index.md` row link → live URL; hub registry entry cli→web port 7076 (+ update hub tests asserting 13→14 web services).
- [ ] `make check-demos` green (hub counts included). Commit `🔥 refactor(demos): reproducibility joins the fleet pattern`.

### Task 4: Console UI
- [ ] `ui/pages.py` + views/static per spec: run form (seed, ablate toggle), runs table with digest chips (monospace, click-copy), Verify button per row → green/red badge with drift diff, Ablation compare pane (control vs ablated totals + delta arrows), error-analysis pane rendering analysis.json fields, config panel readout.
- [ ] Boot smoke via `make demos-up`: run 42, verify ✓, ablate → deltas render; card links from hub land on `/demos/llm-reproducibility/`. Commit `✨ feat(demos): determinism lab console`.

### Task 5: Docs closeout
- [ ] Demo README rewrite (Lab usage, guided tour replacing notebook, standalone + embedded modes, ports).
- [ ] Full gates + `make check-demos`. Commit `📝 docs(demos): reproducibility lab guide`.
