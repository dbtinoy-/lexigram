# Lexigram — Repository Engineering Guidelines

> **Scope**: Repository-wide engineering workflow. Framework implementation standards (contracts, DI, code style, providers, modules, testing) live in [AGENTS.md](./AGENTS.md).

> All rules here are mandatory unless explicitly marked otherwise. Where a rule conflicts with [CONTRIBUTING.md](./CONTRIBUTING.md), the stricter rule wins.

---

## 3. Build, Lint & Test Commands

### 3.1 Package Management (UV)

```bash
uv sync                # Install all dependencies
uv add <package>       # Add a dependency
uv lock                # Regenerate lockfile
```

### 3.2 Linting & Formatting

```bash
uv run ruff check .              # Lint (report only)
uv run ruff check . --fix        # Lint + auto-fix
uv run ruff format .             # Format
uv run ruff format --check .     # Format check (CI mode, no writes)
```

### 3.3 Type Checking

```bash
# Type-check core, web, and the curated set of packages that currently
# pass mypy. This is exactly what CI runs (`make type`).
make type

# Type-check a single package with its own pyproject config.
make type-pkg PKG=lexigram-web

# Core-only quick check (the historical minimal gate).
uv run mypy core/lexigram/src/
```

> Reminder: prevent common mypy failures by always declaring return types, typing function arguments and attributes, avoiding `Any` return values, keeping overrides type-compatible, fixing missing imports, and keeping methods reachable and correctly named. This helps avoid `attr-defined`, `no-untyped-def`, `no-any-return`, `arg-type`, `override`, `unreachable`, `name-defined`, `assignment`, `return-value`, `call-arg`, `type-arg`, `union-attr`, `str`, and `import-not-found` errors.

### 3.4 Testing

```bash
# Full suite — unit surface by default (integration-marked tests are
# deselected unless explicitly opted in)
uv run pytest

# Scoped runs
uv run pytest packages/lexigram-web/tests/                                        # One package
uv run pytest packages/lexigram-web/tests/unit/test_controller.py -v              # One file
uv run pytest packages/lexigram-web/tests/unit/test_controller.py::test_create -v # One test
uv run pytest -k "test_user"                                                     # Pattern match

# Integration opt-in / explicit exclusion
uv run pytest -m integration          # Only integration tests
uv run pytest -m "not integration"    # Explicit exclusion (same as the default)

# Coverage
uv run pytest --cov --cov-report=html
uv run pytest --cov-fail-under=80
```

> **Development testing rule:** during development, run **narrow** tests
> scoped to your changed files/packages (see "Scoped runs" above). Plain
> `uv run pytest` already excludes integration-marked tests; to exercise
> integration, pass `-m integration` or name an `integration` path. Run
> the full framework suite only when really needed (e.g. pre-PR /
> `make ci` aggregate or a change with cross-package ripples).

> **Note:** `--cov-fail-under=80` above applies to the **aggregate**
> suite run from the repo root (`make test` / `make ci`). Individual
> packages set their own, often lower, floor in their own
> `pyproject.toml` `addopts` for scoped/local runs (e.g.
> `lexigram-ai-mcp` at 35%, most `lexigram-ai-*` packages at 60%,
> `lexigram-ai-agents` at 80%). A package below 80% locally is not a
> violation as long as the root aggregate run stays ≥80%.

### 3.5 Full CI Pipeline (Run Before Every PR)

```bash
uv run ruff check . \
  && uv run ruff format --check . \
  && make type \
  && uv run pytest --tb=short --cov-fail-under=80
```

### 3.6 Versioning

```bash
# Scheme: 0.<minor>.<patch><build>   e.g. 0.1.2001, 0.1.3002
#   minor = release branch
#   patch = semver patch (2, 3, ...)
#   build = monotonically increasing build number
#
# After publishing 0.Y.Z, next version is 0.Y.<Z+1>001.
# Example: 0.1.2 → 0.1.3001 → 0.1.3002
#
# Within an ACTIVE series, bump ONLY the build segment:
#   0.1.5001 → 0.1.5002 → 0.1.5003 …
# (never jump patches, never reset the series)
# A new patch digit starts a fresh build series at 001: 0.1.4 → 0.1.4001.
#
# Version bumps are ALWAYS PER-PACKAGE:
#   make version-bump PKG=<pkg> APPLY=--apply
# Bulk bumps across packages are prohibited — a package's version moves
# only when that package changes.

# Set version (pyproject.toml only — __init__.py reads it from metadata)
uvx yj set version "0.1.3001" < core/lexigram/pyproject.toml

# Build & publish (from the package being released)
cd core/lexigram && uv build
uv publish dist/lexigram-*.whl dist/lexigram-*.tar.gz --token pypi-xxxx
```

---

## Development Guide

> This section targets **shared/agent working trees** inside this repository.
> Human contributors should follow [CONTRIBUTING.md](./CONTRIBUTING.md) for the
> normal feature-branch flow; the safety rules below still apply to any tree
> shared by concurrent sessions.

**Do not create Worktrees** Do not create worktrees during development unless ask.
**Do not create Branch** Do not create branch during development unless ask.
**No Co-authored in commit message** Strictly no Co-authored-by: Copilot <xxx+Copilot@users.noreply.github.com>

### Commit Message Convention (MANDATORY)

Every commit message must carry the emoji matching its task type, placed **before**
the conventional-commit prefix: `git commit -m "<emoji> <type>(<scope>): <summary>"`.

| Type       | Emoji | Meaning                          | Example                                          |
|------------|-------|----------------------------------|--------------------------------------------------|
| `feat`     | ✨    | New user-visible feature         | `✨ feat(monitor): capture unhandled exceptions` |
| `fix`      | 🐛    | Bug fix                          | `🐛 fix(auth): refresh token expiry race`        |
| `perf`     | ⚡    | Performance improvement          | `⚡ perf(cache): single-flight stampede guards`  |
| `refactor` | ♻️    | Code restructure, no behavior change | `♻️ refactor(scripts): delegate discovery`    |
| `test`     | ✅    | Tests added or updated           | `✅ test(sql): assert tier boundary violations`  |
| `docs`     | 📝    | Documentation only               | `📝 docs(monitor): Sentry fallback behavior`     |
| `style`    | 🎨    | Format/whitespace, no logic change | `🎨 style(web): normalize quotes`              |
| `chore`    | 🔧    | Maintenance/tooling              | `🔧 chore(git): allowlist tiered paths`          |
| `ci`       | 👷    | CI workflows and config          | `👷 ci: derive members from shared inventory`    |
| `build`    | 📦    | Build system / packaging         | `📦 build: publish lexigram 0.1.3008`            |
| `deps`     | ⬆️    | Dependency upgrade               | `⬆️ deps: uv sync to 0.8.14`                     |
| `security` | 🔒    | Security hardening fix           | `🔒 security(auth): pin JWT algorithm`           |
| `revert`   | ⏪    | Reverts a previous commit        | `⏪ revert: undo glob members experiment`        |
| `wip`      | 🚧    | Checkpoint / in-progress         | `🚧 wip(auth-lane): checkpoint 2026-08-20`       |

Rules:

- One emoji only; the type always matches the emoji. No bare `chore:` or `feat:` without
  the prefix emoji.
- `wip` is reserved for shared-tree checkpoint commits (Safe Sync below) and must be in
  the format `🚧 wip(<lane>): checkpoint <date>`.
- Scope (`<scope>`) is optional and names the affected package, e.g. `feat(monitor)`.
- The public-mirror `make publish-* m="<message>"` commands accept the same
  emoji-prefixed message; plain descriptions are still allowed there.

### History Discipline (MANDATORY)

Build a **longer, verifiable commit history** with tests alongside features.

1. **Ship features together with their tests, in small focused commits.** Each
   new feature or bugfix commit includes its test file in the same change —
   e.g. `lexigram-features/src` plus `lexigram-features/tests/unit/test_*.py`
   together — so every commit is independently verifiable.
2. **Push commits over multiple days/sessions** instead of one continuous
   window, keeping the conventional commit prefixes.
3. **Tag intermediate releases** (`v0.1.4`, `v0.1.5`), to show cadence over time.
4. **Version every package incrementally and independently.** Each
   `lexigram-*` package carries its own version (`0.<minor>.<patch><build>`
   per §3.6) and bumps only when *that* package changes — a fix in
   `lexigram-cache` never moves `lexigram-web` or `lexigram`. After a
   package's feature/fix lands (with its tests, rule 1), bump it in the same
   or immediately-following commit with `make version-bump PKG=<pkg>`
   (`APPLY=--apply` to write; `make version-check` to see which packages
   drifted). Bulk bumps (`version-bump-all`) are **prohibited** — versions
   move per-package only, via `make version-bump PKG=<pkg>`. Never hand-edit versions outside this flow.

### Git Working-Tree Safety (MANDATORY)

This is a *shared* working tree used by concurrent agent sessions. Destructive
git commands from one session have previously wiped another session's
uncommitted edits (incident: 2026-08-16, stash `tmp-admin-conflict-restore`
orphaned by a `git stash` + `git checkout .` dance).

**Never** run these while ANY uncommitted change exists in the tree
(interrupt in-flight work first; if you must sync, see the Safe Sync below):

```
git checkout .            git checkout -- .        git reset --hard <ref>
git clean -f              git clean -fdx            git stash drop
```

Safe Sync (when you need a clean tree to pull/rebase):

1. `git add -A && git commit -m "🚧 wip(<lane>): checkpoint <date>"` — prefer a
   checkpoint commit over stashing; it is crash-proof and keeps the reflog.
2. Only if a commit is impossible (mid-edit secrets, huge diff):
   `git stash push -u -m "<lane>-<date>"` then IMMEDIATELY `git stash pop`
   in the same command chain — never leave an orphaned stash behind.
3. Sync: `git pull --ff-only` (never `--rebase` on a dirty tree).
4. If `git stash pop` conflicts: RESOLVE the conflicts in place. Never
   discard with `git checkout .` / `git reset --hard`; recover via
   `git checkout stash@{0} -- <path>` instead.
 5. `git status --short` before and after any sync; uncommitted work you did
    not recognize as yours belongs to another lane — do not touch it.

**Avoid `git stash pop` whenever other agents are working** (MANDATORY):
a stash pop mutates the shared working tree and index mid-flight, so any
concurrent session's edits can collide with yours while the pop applies —
and a conflicted pop leaves both lanes with mixed, half-applied state until
someone resolves it manually. The stash push/pop dance above is a last
resort for a single-owner tree, not a routine move:

- Prefer checkpoint commits (rule 1) over stash round-trips in all cases.
- If you must stash while other agents are active: scope it (`git stash
  push -u -- <your-paths>`), keep the window as short as possible, announce
  the lane + expected duration if a team channel exists, and re-run
  `git status --short` immediately before popping to confirm no foreign
  edits landed meanwhile.
- If anything unexpected appears at pop time, abort: leave the stash intact
  (`git stash list` to confirm) and coordinate instead of force-resolving.

### Staging & Commit Isolation (MANDATORY)

The shared index is shared state too. Two incidents on 2026-08-21:

- A lane's `git commit` swept **another lane's pre-staged files** into its
  commit (2 unrelated admin files landed under a demos test message).
- A lane's uncommitted edits were **wiped from the working tree** by a
  concurrent lane running a forbidden command above.

Rules:

1. **Never leave changes pre-staged.** Stage and commit in one chain,
   immediately after your verification passes. The window between
   `git add` and `git commit` is where cross-lane contamination happens.
2. **Inspect the index before every commit:** `git status --short`. Staged
   entries (`M `/`A ` in the first column) you did not create belong to
   another lane — never include them, never unstage them either.
3. **Commit by pathspec**, not by bare `git commit`: 
   `git commit <your-paths> -m "<emoji> <type>(<scope>): <summary>"`.
   A pathspec commit takes exactly those paths from the working tree and
   leaves the rest of the index untouched. Untracked files must be
   `git add`ed first or the pathspec will not match them.
4. **Commit early, commit small.** Uncommitted work in this tree is
   vulnerable to other lanes' violations, not just your own mistakes. The
   moment a task's tests pass, commit it before starting the next task.
5. **If foreign files land in your just-created commit:** fix immediately —
   `git reset --soft HEAD~1`, `git restore --staged .`, re-`git add` the
   foreign files to restore their prior staged state, then re-commit only
   your paths per rule 3. Never amend over it, never discard their changes.




---

## See also

- [AGENTS.md](./AGENTS.md) — framework implementation standards
- [CONTRIBUTING.md](./CONTRIBUTING.md) — human-facing contribution workflow
- [.github/workflows/ci.yml](./.github/workflows/ci.yml) — the CI pipeline
