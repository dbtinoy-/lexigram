# Plan: `lexigram.codegen` uplift

> **Status: COMPLETE (2026-08-26).** Tasks 1–6 committed
> (`✨ feat(contracts)…`, `✨ feat(codegen): staged…`, `✨ feat(codegen):
> stub override…`, `✨ feat(testing): golden-tree…`,
> `♻️ refactor(cli-generators)…`, `✨ feat(cli): declared options…`);
> Task 7 gates green (80 tests, ruff/mypy clean, versions AHEAD,
> lint-loc clear for touched files).

> Spec: [`specs/2026-08-26-codegen-uplift-design.md`](../specs/2026-08-26-codegen-uplift-design.md).
> Conventions: AGENTS.md — TDD per task (tests in the same commit),
> offline only, files < 500 LOC, Result for domain failures, emoji
> conventional commits, pathspec commits (shared tree).

> **Task 0 — recon:**
> - Confirm whether `CommandAssembler` (lexigram-cli) consumes
>   `GeneratorDefinition.options` today; record finding in Task 6 commit
>   body. If ignored → implement help-text rendering only.
> - Count distinct `generate()` signature variants across the ~39
>   generators (for §4 back-compat claim evidence).
> - Check loc baseline entries for every file this plan touches.
>
> **Sequencing:** Tasks 1–3 must merge before the builder program's
> Task 3 (builder writer consumes `StagedGeneration`).

**Goal:** Schematics-grade atomic staging, Rails-grade options/collision
policy, Laravel-grade stub overrides, Phoenix-grade post-write seam,
Schematics-grade option descriptors, plus a shared golden-tree test util.
**Architecture:** contracts gain pure types (`CollisionPolicy`,
`GenerationOptions`, manifest); core gains `StagedGeneration` + override
precedence + `finalize()`; sql/web generators adopt as reference;
`lexigram-testing` gains `assert_generated_tree`.

### Task 1: Contracts — options, policy, manifest
- [ ] Tests: normalization matrix (explicit policy beats force; force ⇒
      OVERWRITE; dry_run orthogonal), StrEnum semantics, manifest maps
      actions per path, CollidingFileError is InfrastructureError leaf.
- [ ] Implement in `contracts/cli/generators.py` +
      `exceptions/infra.py`. Commit
      `✨ feat(contracts): generation options, collision policy, manifests`.

### Task 2: Core — StagedGeneration + finalize seam
- [ ] Tests: stage→commit writes sorted tree byte-exact; duplicate stage
      raises immediately; staged-vs-disk collision honored per policy;
      FAIL policy raises CollidingFileError without partial writes;
      dry-run computes result touching nothing (fs snapshot compare);
      traversal guard fires at stage time; write_file legacy kwargs
      unchanged behavior; finalize() default identity.
- [ ] Implement in `codegen/base.py` (+ small `_staging.py` if base.py
      would cross 500 LOC). Commit
      `✨ feat(codegen): atomic staged generation with collision policies`.

### Task 3: Core — stub override precedence
- [ ] Tests: anchor stubs dir wins over package templates; missing stubs
      dir falls back; dotted-package layout isolates packages; explicit
      template_root still absolute-wins.
- [ ] Implement `_resolve_template_root` precedence chain. Commit
      `✨ feat(codegen): user-owned stub override layer`.

### Task 4: lexigram-testing — assert_generated_tree
- [ ] Tests for the util itself (pass/fail modes, tmp-dir isolation,
      returns GenerationResult). Implemented as `lexigram/testing/generators.py`.
- [ ] Commit `✨ feat(testing): golden-tree generator test util`.

### Task 5: Reference adoption (web ×2, sql ×1)
- [ ] Migrate `ControllerGenerator`, `ResourceGenerator`,
      `DatabaseRepositoryGenerator` to stage/commit/options/finalize.
- [ ] Extend their tests with Task 4's util: policy matrix + dry-run +
      duplicate-stage coverage. Golden content assertions stay
      byte-stable.
- [ ] Commit `♻️ refactor(cli-generators): adopt staged generation API`.

### Task 6: GeneratorOption population
- [ ] Per Task 0 finding: populate options on all six sql+web definitions
      and (if needed) render help text from them in assembler.
- [ ] Tests: definitions carry expected option names/types; help smoke.
- [ ] Commit `✨ feat(cli): declared generator options`.

### Task 7: Gates + registration
- [ ] Full chain scoped to touched pkgs: ruff format/check, mypy
      (contracts, core/codegen, testing, web/sql cli trees), pytest
      offline suites of touched pkgs, lint-loc 0 new/stale.
- [ ] Version bumps via `make version-bump PKG=<touched>` APPLY=--apply;
      `uv lock`; update `.superpowers/README.md` program index row.
- [ ] Commit `🔧 chore(codegen): versions, lock, program index`.
