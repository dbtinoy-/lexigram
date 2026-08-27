# Spec — `lexigram.codegen` uplift (framework-pattern parity pass)

**Date:** 2026-08-26
**Status:** Draft for review
**Location:** existing packages only — `lexigram-contracts`, `lexigram`, plus adoption in `lexigram-sql`, `lexigram-web`; test util lands in `lexigram-testing`
**Kind:** Subsystem enhancement. No new packages, no new dependencies (stdlib-only additions), contribution system untouched.

**Sequencing contract:** this uplift lands BEFORE the lexigram-builder program's codegen task — the builder's project writer consumes `StagedGeneration` + `GenerationOptions`/`CollisionPolicy` + `finalize()` directly (see builder spec §5).

---

## 1. Purpose

Bring the freshly de-stubbed `lexigram.codegen` to feature parity with the
mechanisms proven by mature frameworks, selected deliberately:

| # | Mechanism | Learned from | Gap today |
|---|---|---|---|
| 1 | Atomic multi-file staging | Angular Schematics virtual tree | `write_file` commits per file; multi-file generators can leave partial output |
| 2 | Standardized options + collision policy | Rails `--pretend/--force/--skip` | ad-hoc `dry_run`/`force` kwargs re-declared in ~39 signatures |
| 3 | User-owned template overrides | Laravel `stub:publish` | templates locked to package internals |
| 4 | Post-write hook seam | Phoenix compile-after-generate | no formatting/verification point after commit |
| 5 | First-class `GeneratorOption` | Schematics `schema.json` | contract exists but contributors never populate it |
| 6 | Golden-tree test util | all mature frameworks ship one | every package hand-rolls assertions |
| 7 | Manifest output | Schematics reports / Copier | `GenerationResult` has paths only |

Explicitly **deferred** (recorded so nobody rediscovers them): AST-based
injection primitives (`inject_into_file` analogues) and round-trip project
updates (Copier-style) — the latter contradicts the builder program's
locked one-way decision.

## 2. Contract surface additions (`lexigram-contracts/cli/generators.py`)

```python
class CollisionPolicy(StrEnum):
    SKIP = "skip"            # existing file wins (default — current behavior)
    OVERWRITE = "overwrite"  # replace existing file
    FAIL = "fail"            # raise CollidingFileError


@dataclass(frozen=True, slots=True)
class GenerationOptions:
    dry_run: bool = False
    force: bool = False      # convenience alias → policy=OVERWRITE when set
    quiet: bool = False
    policy: CollisionPolicy | None = None   # explicit policy beats force
```

Normalization rule (single function, tested): explicit `policy` wins;
else `force=True` ⇒ OVERWRITE; else SKIP. `dry_run` is orthogonal and
never mutates disk.

`GenerationResult.to_manifest() -> dict[str, str]` — `{path: action}`
where action ∈ {created, skipped, overwritten}. Pure data; no I/O, no
hashing (content hashing belongs to callers/builders).

New leaf exception `CollidingFileError(InfrastructureError)` in contracts
`exceptions/infra.py`.

## 3. Core changes (`lexigram/codegen/base.py`)

### 3.1 StagedGeneration (atomicity)

```python
gen.stage("models/user.py", rendered_content)   # validates only
result = gen.commit(options)                    # writes everything-or-first-error
```

- `stage(rel_path, content)`: resolves against `output_dir`, runs the
  existing traversal guard, checks collisions against **disk and against
  earlier stages** (duplicate stage = bug, raises immediately).
- `commit(options)`: re-validates all staged paths, then writes in
  **sorted path order** (deterministic byte-order of the tree). `dry_run`
  computes the full would-be `GenerationResult` touching nothing.
- Semantics: *validate-all-then-write-all* (Rails-grade atomicity:
  no partial trees from validation failures; mid-write OS failure remains
  possible and is documented — true transactional swap is YAGNI).

### 3.2 Options normalization + finalize seam

- `write_file` keeps its legacy kwargs (documented convenience form);
  internally routes through `_resolve_options(...)`.
- New overridable `finalize(result) -> GenerationResult` — called by
  generators as the last step of `generate()`; default is identity.
  Post-commit transforms (ruff format, import sort) hook here later from
  the CLI layer; the seam itself stays stdlib-only.

### 3.3 Stub override precedence

`_resolve_template_root(None)` becomes:

1. `<project_anchor>/stubs/<dotted-package-as-path>/` — e.g.
   `./stubs/lexigram/web/controller.py.jinja2` overrides
   `lexigram.web.cli.templates/controller.py.jinja2`
2. package-local `templates/` (unchanged fallback)

Dotted-namespace layout prevents cross-package filename collisions.
A future `lexigram gen stubs` publisher verb may materialize (1) — out of
scope here.

## 4. Adoption (proof in real generators)

Reference adopters, migrated to `StagedGeneration` +
`GenerationOptions` + `finalize`:

- `lexigram-web`: `ControllerGenerator`, `ResourceGenerator`
- `lexigram-sql`: `DatabaseRepositoryGenerator`

Their unit tests extend to cover: staged duplicate rejection, policy
SKIP/OVERWRITE/FAIL matrix, dry-run touches nothing. Remaining ~36
generators migrate opportunistically (no forced churn — the legacy
kwargs keep working indefinitely).

## 5. `GeneratorOption` population

Recon first: confirm `CommandAssembler` actually consumes
`definition.options` for help/prompt/validation. Then populate for the
six sql+web definitions (`fields_str`, `force`, `dry_run`, `path`,
`doc` …). If the assembler ignores options today, wire rendering for
help text only (prompts deferred — interactive flows belong to the
builder-era CLI).

## 6. Test utility (`lexigram-testing`)

New `lexigram/testing/generators.py`:

```python
def assert_generated_tree(
    generator: GeneratorProtocol,
    name: str,
    *,
    expected_files: dict[str, str],     # relpath → exact expected content
    output_dir: Path,
    **kwargs: object,
) -> GenerationResult:
```

Runs in a caller-provided tmp dir, asserts exact tree + byte content,
returns the result for further assertions. Adopted immediately by the
web/sql reference-generator tests as the usage example.

## 7. Non-goals

- No migration of the remaining ~36 generators (legacy API stable).
- No interactive prompting, no injection primitives, no round-trip.
- No behavioral change to any existing passing test.

## 8. Acceptance criteria

- [ ] All existing generator tests green unchanged (back-compat proven)
- [ ] New units: options-normalization matrix, staging duplicate/collision/
      dry-run/atomicity, override precedence, manifest shape
- [ ] Reference generators (web ×2, sql ×1) on the new API with extended tests
- [ ] `assert_generated_tree` used by ≥3 real tests
- [ ] ruff/mypy clean; lint-loc 0 new; versions bumped per touched pkg; lock updated
