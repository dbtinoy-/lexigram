# Milestones

Rolling roadmap for the Lexigram Framework monorepo. Release dates follow the
annotated `v0.1.x` tags published on `dbtinoy-/lexigram` (authoritative);
`CHANGELOG.md` sections may carry their own, older dates.

---

## Releases

| Version | Released | Summary |
| --- | --- | --- |
| `v0.1.0` | 2026-04-07 | Repository start. Initial framework release: 42 packages integrated and tested, DI/IoC container with provider pattern, `Result[T, E]` error handling, full audit framework (8 audit types), Docker Compose integration infrastructure (PostgreSQL, Redis, Kafka, MongoDB, Elasticsearch, MinIO, Qdrant, Neo4j), import-boundary enforcement, multi-backend data layers, PyPI-ready distributions. |
| `v0.1.1` | 2026-05-15 | Release on the 0.1 line: version alignment across all packages; workspace split into core / packages / experimental tiers. |
| `v0.1.2` | 2026-06-21 | Hardening release: dynamic settings categories with per-spec stores, tenant-scoped settings, verified-only JWTs, secrets never rendered in settings HTML, publish gate blocks sensitive wheel content, `required_audience` enforced, 305 low-risk SAST findings remediated family-by-family, structured error detail in blind-except paths. |
| `v0.1.3` | 2026-08-21 | Admin live widgets over a shared `EventSource`, RBAC-gated widget stream (`/admin/_sse/widgets`), tenant-scoped `SubjectAdminEventHub`; around this release: docs restructure (`docs/{audit,ecosystem,fundamentals,getting-started,guides,reference}`), fullstack-demo extracted to its own repository, `DEPENDENCY_TREE.md` committed, CI step names aligned for scanner detection. |
| `v0.1.4` | 2026-08-23 | Generator system overhaul: 26 packages contribute generators via entry points; stub-to-real conversion for auth, events, features, monitor, notification, tenancy, vector, workflow, queue, cache, tasks; generator contract harness with per-package tests. Dual-mode config with late-binding injection (clusters A–D). Import depth lint gate (max 6 segments). MFA config dataclass. Auth-Rbac demo rewritten as teaching exemplar. |

---

## Current cycle — Week of 2026-08-24 → 2026-08-30 (Coverage push + doc cleanup)

Focus: push aggregate test coverage from 75.6% toward 80% target; resolve documentation claims; update roadmap to reflect actual status.

> Coverage gate reference: the CI aggregate gate is `--cov-fail-under=70`
> (`.github/workflows/ci.yml` → coverage job); the 80% figure is the
> milestone target, and per-package floors live in each package's
> `pyproject.toml` `addopts` (e.g. `lexigram` core uses 38%). These are
> three different numbers by design: floor ≠ target ≠ per-package floor.

### Completed this week

- **v0.1.4 released** (2026-08-23) — generator system overhaul, dual-mode config, import depth gate
- **YAML config generator** — `dev/generators/yaml_config_example.py` produces `application.full.example.yaml` from catalog; all 43 catalog packages covered
- **Dev tooling rename** — `dev/core/` → `dev/_lib/` (internal shared library); `tools/lint_imports.py` → `dev/checks/lint_imports.py`
- **MFA config** — `MFAConfig` dataclass with TOTP, backup codes, and issuer settings
- **Import depth lint gate** — new CI check enforcing max 6-segment import depth

### In progress

- **Coverage push** — targeting low-coverage packages: secrets (58%), sql (62%), events (63%), storage (62%), auth (68%)

---

## Next week — 2026-09-03 → 2026-09-09 (Coverage + release)

| Day | Focus | Target |
|-----|-------|--------|
| Mon–Tue | Coverage: `lexigram-auth` + `lexigram` (core) | 68%→75%, 39%→45% |
| Wed | Aggregate coverage check | verify ~78–79% |
| Thu–Fri | Cut v0.1.5 release | bump + tag |
| Sat | Update MILESTONE.md with v0.1.5 status | sync |
| Sun | Buffer / overflow | — |

---

## Backlog (proposed, not scheduled)

- Additional backend support (Q2 roadmap item — not yet started)
- Performance optimizations (Q3-Q4 roadmap item)
- AI subsystem GA: routing / governance / observability conformance sweeps
- Multimedia pipeline milestones (TTS, music, video, image)
- CLI 1.0: 42-generator coverage completion and docs
- Platform: OpenTelemetry exporter GA, deploy-stage CI job
- Reach 70% test coverage overall (unit + integration; integration-only baseline ~35%)
- Enterprise features, distributed tracing, advanced monitoring (2027)

---

## Status snapshot

| Area | Status | Notes |
|------|--------|-------|
| Test coverage | **75.6%** | Target 80%; gap in core packages |
| AI subsystem | **Done** | 17 packages, all passing, 51–97% coverage |
| CLI | **Done** | 22 commands, 26 generators, 80% coverage |
| Demos | **Done** | 14 demos, all with tests |
| Security audit | **Done** | 11 rounds, clean, 0 open items |
| Admin dashboard | **In progress** | Polish ongoing (SSE widgets, RBAC) |
| Documentation | **Done** | 3 minor unresolved claims (in progress) |
| Dev tooling | **Done** | 12 checks, 6 generators, import depth gate |

---

## Process commitments

- Features and fixes ship with their tests in the same commit (verifiable per commit)
- Conventional commits with task-type emoji; small atomic changes
- Env / dependency / security gates green before push (`dev/check_*.py`, pip-audit)
- Milestone file updated weekly with verified status
