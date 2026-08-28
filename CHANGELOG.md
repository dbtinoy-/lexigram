# Changelog

All notable changes to the Lexigram Framework are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `ai-evaluation` guide documenting the LLM evaluation and reproducibility subsystem — evaluators, harness, seed-stable experiment tracking, digest-verified checkpoints, ablations, and error analysis.

### Changed
- `lexigram-web` `PermissionGuard` now requires **all** listed permissions by default; `require_all=False` opts into the previous any-of behavior.
- `lexigram-auth` `use_guards` / `require_auth` / `require_admin` now fail closed with a `ValueError` when no request context can be discovered instead of silently running the handler unguarded.
- Local `make ci` / `make test-cov` coverage gate aligned with CI at a 70% floor.
- Workspace version alignment: all 54 packages now carry `0.1.5007` (was a mix of `0.1.5003`–`0.1.5006`); `uv.lock` regenerated.

### Fixed
- `APIKey.is_active()` no longer crashes with `TypeError` on aware-UTC timestamps (SQL-backed keys): naive values are assumed UTC, matching the rest of the auth package.
- `MigrationScheduler.schedule_migration()` accepts naive `run_at` values (its documented `datetime.now() + timedelta(...)` usage) without raising on the naive-vs-aware subtraction.
- CLI database bootstrap no longer crashes with `LEX_ERR_CFG_001` when run outside a full framework container: the bare-CLI providers are marked config-from-factory so the orchestrator skips the `LexigramConfig` lookup (`lexigram db setup` / direct migration runner paths).
- `lexigram-cli` `ConfigManager.save()` no longer drops unset (`None`) fields incorrectly: the `tomli_w` path raised `TypeError` on `None`, and the manual TOML fallback wrote the corrupting string `"None"`; omitted keys now fall back to their defaults on load.
- `lexigram-multimedia-video` and CLI registry tests no longer depend on runner binaries (`ffmpeg`/`psql`/`mysql` on `PATH`) — availability is patched so tests are deterministic.
- `lexigram-sql` `QueryEngine` now returns normalized `list[dict]` rows and correct scalar values against real backends (`aiosqlite`, `asyncpg`, `aiomysql`) instead of assuming a driver result exposes `.fetchall()` / dict rows.
- `ConnectionProtocol` now reflects the actual `DatabaseConnection` surface (`execute`/`execute_many`/`fetch_one`/`fetch_all`/`close`).
- CLI migration command formatting passes the locked ruff format gate.
- README `in progres` typos.
- Import-boundary enforcement repaired: `dev/checks/lint_imports.py` now works with grimp 3.13 (`determine_package_directories` API) and both it and the import-depth gate run in CI; `lexigram.graphql` no longer imports `lexigram.security` (SHA-256 cache keys now use stdlib `hashlib`).
- `lexigram.contracts.ai.relay.dto.items` moved up one level so the relay DTO family stays within the 6-segment import-depth gate (`openai_responses` still re-exports `ResponsesItem`).

## [0.1.3] — 2026-08-19

### Added
- Admin live widgets: `activity` now pushes live updates over a single shared `EventSource`; widgets declaring `live_resource_types` skip their poll trigger and re-render on matching SSE messages.
- RBAC-gated widget stream at `/admin/_sse/widgets` — filters by `resource_type` via the `resources` query parameter, checked against `PermissionService.can_list`.

### Changed
- `/admin/_sse/events` retired in favor of `/admin/_sse/widgets` (breaking for external clients polling the old path); live-widget dispatch reads nested `resource_type` with a fail-closed RBAC gate.
- `SubjectAdminEventHub` gained tenant scoping (`subscribe(tenant_id=...)`), `drop_latest` subscriber overflow (publishing never blocks on a slow subscriber), and `publish_notification()`; `ActionExecutor.event_hub` is now typed `SubjectAdminEventHub | None` so `@inject` can auto-resolve it.
- `WidgetParams` and `AdminEvent` carry an optional `tenant_id` for tenant-scoped streams.

## [0.1.2] — 2026-08-18

### Added
- Settings sidebar categories now derive dynamically from each spec's `package_source`, replacing the fixed 3-category taxonomy; every `ConfigSpec` can choose its own store, and readonly fields are enforced server-side.
- Read-only `DeploymentInfoSpec` (sourced from `EnvStore`) and a System Info settings panel.
- Per-request `tenant_id` resolution: threaded through `ConfigRegistry.get_values/save` and `TenantConfigStore` for tenant-scoped settings.
- `lexigram-ai-prompt` gained a `max_variable_length` config flag.
- Structured management pages in `lexigram-contracts` — the host renders all management page HTML.

### Changed
- Verified-only JWTs everywhere: the `allow_unverified_dev` option is dropped.
- Secrets are never rendered in settings form HTML; blank secret submissions leave the stored value unchanged.
- Dashboard content tables got consistent tabular visuals; the queue admin contributor now registers unnamed so admin boot resolves it.
- Migration status widget now wires to real migration data.
- Dead throttle decorator removed; idempotency is now dialect-aware.

### Security
- Publish gate blocks sensitive wheel content; `required_audience` is now mandatory in strict environments.
- 305 verified low-risk SAST findings remediated family-by-family; the security report tracks area status instead of individual specs.
- Structured error detail in blind-except log/query paths.

## [0.1.1] — 2026-04-22

### Added
- Initial framework release: 42 packages integrated and tested, DI/IoC container with provider pattern, and Result[T, E] error handling.
- Full audit framework with 8 audit types (tests, quality, security, protocols, etc.).
- Docker Compose infrastructure for integration testing (PostgreSQL, Redis, Kafka, MongoDB, Elasticsearch, MinIO, Qdrant, Neo4j).
- Import boundary enforcement with 6 architectural contracts.
- Multi-backend support for all data layers (no vendor lock-in).

### Fixed
- Version alignment across all packages.

### Infrastructure
- PyPI-ready distribution for all 42 packages; root files reviewed.

---

## Version History Template

### For Future Releases

Use this template when creating new releases:

```markdown
## [X.Y.Z] — YYYY-MM-DD

### Added
- Feature descriptions
- New modules
- API additions

### Changed
- Behavior changes
- API modifications
- Documentation updates

### Fixed
- Bug fixes
- Issue resolutions

### Security
- Security patches
- Vulnerability fixes

### Deprecated
- Features marked for removal

### Removed
- Features removed
- Modules deleted

### Migration Guide
- Steps for upgrading
- Breaking change details
- Code examples
```

---

## Release Timeline

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| 0.1.3 | 2026-08-19 | ✅ Current | Admin live widgets, tenant-scoped streams |
| 0.1.2 | 2026-08-18 | ✅ Released | Settings taxonomy, verified-only JWTs, security hardening |
| 0.1.1 | 2026-04-22 | ✅ Released | Initial framework |

---

## Upcoming

### Planned (No Specific Timeline)
- [ ] Deloying Production grade applications
- [ ] Completing CLI
- [ ] Completing Admin
- [ ] Completing UI

### Research Phase
- [ ] Additional AI/ML capabilities
- [ ] Performance optimizations

---

## Contributing Changes

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on reporting bugs, requesting features, and submitting changes.

## Security

For security issues, see [SECURITY.md](SECURITY.md).

---

**Last Updated**: 2026-08-19  
**Current Version**: 0.1.3  
**Python Support**: 3.11+
