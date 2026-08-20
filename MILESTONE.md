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

## Current cycle — Week of 2026-08-17 → 2026-08-23 (Security audit execution)

Rounds executed to completion this week, verified and committed (tracker:
`docs/audit/AUDIT_SECURITY.md` — verified-clean surfaces + open risk table):

- **Rounds 1–2:** P0 session-secret, SQL injection, XSS, Tenancy, Secrets, SSRF, Deserialization, Web-CSRF — complete
- **Round 3:** AI-guard (§11), GraphQL (§12), Media-upload (§13) — complete
- **Round 4:** §16 AI-memory owner-scoping, §17 logging, §18 relay/worker/MCP trust, §19 HTTP client, §20 non-SQL query injection — complete
- **Round 5:** §21–25 RBAC super-admin, password-reset, CORS, MFA, impersonation — complete
- **Round 6:** admin-surface fixes — setup-wizard takeover, atomic first-admin claim, mandatory setup token, login/profile fixes, open-redirect — complete
- **Round 7:** §31–36 SQL identifiers, auth-guard bypass, Alpine JS, search escaping, session-fallback TTL, login roles bug — complete
- **Round 8:** §37–39 relations XSS/authz/Excel export, §40 Meilisearch/Typesense filter injection, §41–42 settings/command-palette — complete
- **Round 9:** §45 pgvector, §46 storage KV traversal, §47 MCP handshake, §48 agent tool-visibility, §49 OAuth2 email-verified binding — complete
- **Deserialization deep-dive (§3.9):** pickle deserializers removed or restricted, `@cacheable` registry-only reconstruction (zero `importlib`), SkillLoader fail-closed sandbox, CLI MySQL backup/restore argv-only — complete
- **Round 10:** §50–60 (governance, observability, ai-workers, prompt, features, monitor, resilience) — complete
- **Round 11:** §61–79 (ai core/evaluation/feedback, audit, events, queue, tasks, workflow) — complete

Transport hygiene QA this week (verified locally, committed to `main`):

- `dev/check_env_example.py` passes: 1796 documented vars, 44 referenced vars, 0 missing
- `docs/reference/DEPENDENCY_TREE.md` committed (full `uv tree --locked` graph)
- Workspace-config test now enforces direct dependency declarations per member
- Error-tracking wiring integration scenario tests the provider boot → Sentry → excepthook chain (faked SDK, no infra)

In progress:

- **Reactive layer** — progressive enhancement: wiring end events — started
- **Admin dashboard** — polish continuation (open-ended)

## Next week

- **Reactive layer** — wiring end events (continuation)
- **Admin dashboard** — polish continuation
- **Release `v0.1.4`** — cut once the reactive-layer milestone lands (planned)

## Backlog (proposed, not scheduled)

- AI subsystem GA: routing / governance / observability conformance sweeps
- Multimedia pipeline milestones (TTS, music, video, image)
- CLI 1.0: 42-generator coverage completion and docs
- Platform: OpenTelemetry exporter GA, deploy-stage CI job

## Process commitments

- Features and fixes ship with their tests in the same commit (verifiable per commit)
- Conventional commits with task-type emoji; small atomic changes
- Env / dependency / security gates green before push (`dev/check_*.py`, pip-audit)
- Milestone file updated weekly with verified status