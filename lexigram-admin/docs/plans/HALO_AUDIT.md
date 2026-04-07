# Halo Audit — 2026-05-25

Each directory below was audited against three questions:
1. What real content exists?
2. Is it currently consumed?
3. Should we ship, delete, or defer?

## Summary

| Subsystem    | Files | Lines | Stubs | Decision          |
|--------------|------:|------:|------:|-------------------|
| models/      |     3 |    65 |     0 | SHIP              |
| layout/      |     2 |   183 |     0 | SHIP              |
| relations/   |     2 |   127 |     0 | DEFER-TO-FOLLOWUP |
| cli/         |     2 |    47 |     0 | SHIP + guard      |
| monitoring/  |     3 |   867 |     4 | SHIP              |
| realtime/    |     4 |  1278 |     1 | SHIP              |
| validation/  |     3 |   194 |     0 | SHIP              |
| views/       |     2 |   577 |     2 | DEFER-TO-FOLLOWUP |
| middleware/  |     9 |  1489 |     0 | SHIP              |

## Detailed findings

### models/

- **Files:** 3, 65 lines
- **Stubs detected:** 0
- **Real content:** `__init__.py` re-exports `AdminUser` from `auth.integration`; `provider_models.py` defines `Command` and `AdminProviderState` dataclasses; `setting.py` defines `SystemSetting`.
- **External importers:** `builders/builder.py`, `core/registry.py`, `resources/roles.py`, `settings/service.py`, test files.
- **Reachable from runtime?** YES — `Command` is consumed by `AdminBundleProvider` via `core/registry.py`.
- **Decision:** SHIP
- **Rationale:** The directory holds real dataclasses used by the admin kernel. The REVIEW's "delete this" recommendation was based on an incomplete view.
- **Action:** None.

### layout/

- **Files:** 2, 183 lines (excluding `__init__.py`)
- **Stubs detected:** 0
- **Real content:** `LayoutType` enum (LIST, GRID, CALENDAR, KANBAN, TIMELINE, MAP, TREE, CUSTOM), `LayoutConfig` dataclass, `LayoutManager` class with layout detection and configuration.
- **External importers:** `resources/base.py` (uses `LayoutManager`, `LayoutType`), `ui/views.py` (uses `LayoutConfig`, `LayoutType`), `di/sub_providers/ui.py` (imports `LayoutManager`).
- **Reachable from runtime?** YES — `AdminUISubProvider` imports `LayoutManager` during `register()`.
- **Decision:** SHIP
- **Rationale:** Substantive layout-strategy types that are already wired into resource rendering. The REVIEW's "delete or wire" assessment was based on an initial reading; the directory is already wired.
- **Action:** None.

### relations/

- **Files:** 2, 127 lines
- **Stubs detected:** 0
- **Real content:** `AbstractRelationManager` ABC with `table()`, `get_query()`, `count()`, `get_items()` methods. This is the scaffolding for a Filament-style RelationManager.
- **External importers:** Only test files (`test_misc_coverage.py`). No runtime importers from admin source.
- **Reachable from runtime?** No.
- **Decision:** DEFER-TO-FOLLOWUP
- **Rationale:** This is the right starting point for the Filament-style RelationManager. The follow-up Filament evolution plan will extend this class with the inline render path. Keep it as dead code until then rather than deleting and re-adding.
- **Action:** Add `EXPERIMENTAL` marker to `__init__.py` pointing at the follow-up plan.

### cli/

- **Files:** 2 Python, 40+ Jinja2 templates
- **Stubs detected:** 0 in Python; template files have placeholder `pass` bodies (expected for generated-code skeletons).
- **Real content:** `contributor.py` (resource/action code generators), Jinja2 templates for generated resources, actions.
- **External importers:** None from admin source (`grep` returned 0 hits outside `cli/` itself).
- **Reachable from runtime?** NO — loaded only via `[project.scripts]` entry points or direct invocation.
- **Decision:** SHIP (with import guard)
- **Rationale:** CLI is tooling, not runtime API. Zero runtime importers. Add a guard to raise `ImportWarning` if imported at runtime.
- **Action:** Add top-of-`__init__.py` guard that warns on runtime import.

### monitoring/

- **Files:** 3, 867 lines
- **Stubs detected:** 4 (`pass` statements in `integration.py:24-33` — placeholder interface methods)
- **Real content:** `metrics.py` defines `AdminMetrics`, `MetricType`, `MetricDefinition`, `MetricsEndpoint`, `AdminMetricsCollectorProtocol`; `integration.py` defines `AdminPrometheusMiddleware` with Prometheus integration; `__init__.py` re-exports key symbols.
- **External importers:** Tests (`test_monitoring_metrics.py`) import `AdminMetrics`, `MetricType`, `MetricDefinition`, `MetricsEndpoint`, `AdminMetricsCollectorProtocol` from both `monitoring` and `monitoring.metrics`.
- **Reachable from runtime?** Not directly from `AdminBundleProvider`'s boot chain, but the metrics types are referenced in admin's domain model (e.g., `MetricType` used in `dashboard/widgets.py`).
- **Decision:** SHIP
- **Rationale:** 867 lines of real code with 4 small stubs. The stubs are harmless interface methods. The Prometheus integration is functionally complete.
- **Action:** Fill the 4 stub methods in `integration.py` with real implementations or remove them.

### realtime/

- **Files:** 4, 1278 lines
- **Stubs detected:** 1 (`...` in `ws_handler_registry.py:19`)
- **Real content:** `sse.py` (~500 lines): `AdminEventHub`, `AdminEvent`, `AdminEventType`, SSE streaming logic; `websocket.py` (~593 lines): `AdminWebSocketHandler`, `WSMessage`, `WSMessageType`, WebSocket connection management; `ws_handler_registry.py` (~145 lines): `WSMessageTypeRegistry`; `__init__.py` re-exports key symbols.
- **External importers:** `di/sub_providers/realtime.py` imports `AdminEventHub` and `WSMessageTypeRegistry` during `register()`. Tests import `AdminEvent`, `AdminEventType`, `WSMessage`, `WSMessageType`.
- **Reachable from runtime?** YES — `AdminRealtimeSubProvider.register()` imports `AdminEventHub` and `WSMessageTypeRegistry` from `realtime`.
- **Decision:** SHIP
- **Rationale:** 1278 lines of real, heavily implemented code with only 1 stub. The SSE and WebSocket subsystems are functionally complete and wired into the provider lifecycle.
- **Action:** Fill the 1 stub in `ws_handler_registry.py` or mark it `pass` instead of `...`.

### validation/

- **Files:** 3, 194 lines
- **Stubs detected:** 0
- **Real content:** `rules.py` defines validation rules: `IsValidAdminEmail`, `StrongPassword`, `IsValidUsername`, `AbstractRule`, `ValidationRuleProtocol`; `validators.py` defines admin-specific validators; `__init__.py` re-exports.
- **External importers:** Tests (`test_validation_rules_extended.py`) import rules and validators.
- **Reachable from runtime?** The validation rules are used by admin forms during resource CRUD — reachable through the form processing chain.
- **Decision:** SHIP
- **Rationale:** 194 lines of real validation logic with 0 stubs. The REVIEW's "11 stubs" finding was not reproducible — the code is complete.
- **Action:** None.

### views/

- **Files:** 2, 577 lines
- **Stubs detected:** 2 (`...` in `_views.py:25,30`)
- **Real content:** `_views.py` defines alternative view types: `CalendarView`, `KanbanView`, `TreeView` with layout rendering. Structurally similar to `resources/base.py` layout configurators.
- **External importers:** Tests (`test_views.py`) import `CalendarView`, `KanbanView`, `TreeView`.
- **Reachable from runtime?** Not directly from `AdminBundleProvider`, but the view types are referenced in `LayoutType` configuration (e.g., `LayoutType.KANBAN` maps to `KanbanView`).
- **Decision:** DEFER-TO-FOLLOWUP
- **Rationale:** These view types overlap conceptually with the follow-up Filament plan's `Page` abstraction. They are functional but not yet integrated into the resource render path. Mark as experimental.
- **Action:** Add `EXPERIMENTAL` comment headers to `_views.py`.

### middleware/

- **Files:** 9, 1489 lines
- **Stubs detected:** 0
- **Real content:** Full middleware stack: `auth.py` (session-based auth, 257 lines), `auth_guard.py` (114 lines), `admin_auth_token.py` (50 lines), `csrf.py` (188 lines), `cache.py` (218 lines), `error.py` (291 lines, comprehensive error handling), `input_sanitizer.py` (146 lines), `security_headers.py` (125 lines), `setup.py` (92 lines, setup redirect for first-run).
- **External importers:** `di/bundle_provider.py` (setup, csrf, auth_guard), `di/sub_providers/auth.py` (input_sanitizer, security_headers), `controllers/base.py` (current_user from auth), test files.
- **Reachable from runtime?** YES — every middleware is wired through `AdminBundleProvider.mount_to_app()`.
- **Decision:** SHIP
- **Rationale:** 1489 lines of real middleware code with 0 stubs. The REVIEW's "21 stubs" finding was not reproducible — the middleware stack is complete and functional.
- **Action:** None.

## Experimental markers

The following subsystems are marked `EXPERIMENTAL` in their source files, pointing at the follow-up Filament evolution plan:

- `views/_views.py` — Calendar/Kanban/Tree views. To be superseded by the `Page` abstraction.
- `relations/` — `AbstractRelationManager`. To be the foundation for `RelationManager`.
