# LOC Debt Register

Files accepted as debt under Recipe D. Each entry documents the file,
its current LOC, the 500-LOC limit, and rationale for accepting it.

Regenerate after review: `uv run python dev/check_loc_limit.py --root . --write-baseline`

---

## auth/guards.py — 523 LOC

Rationale: Focused auth guard middleware. All functions serve a single
concern (request authentication/authorization). Decomposing would add
indirection without reducing complexity.

## auth/services/auth_service.py — 559 LOC

Rationale: Auth orchestrator with tightly-coupled RBAC, session, and
token logic. The methods share state (user lookup, permission checks)
making extraction artificial. Accept as coherent service.

Rationale: SQL user store implementing a single data-access interface.
All methods operate on the same table schema. Decomposing per-method
would scatter a cohesive store across files.

## controllers/base.py — 519 LOC

Rationale: Base controller class with lifecycle hooks and routing
helpers. All methods serve the same abstract controller role.
Subclasses depend on the full interface.

Rationale: Widget controller routing HTMX requests. All endpoints share
the same registry, permission checks, and settings service. The
controller is the natural unit for this concern. Consider splitting
when widget types grow beyond current scope.

## dashboard/widgets.py — 577 LOC

Rationale: Dashboard widget type definitions and infrastructure.
Coherent type hierarchy with shared rendering patterns. Accept as
single module.

## data/query.py — 533 LOC

Rationale: QuerySpec/PagedResult value types. These are data carriers
used together across the codebase. Separating would break import
ergonomics without reducing complexity.

Rationale: Admin DI provider orchestrator. Registers all sub-providers
in a single coherent boot sequence. Splitting would scatter the
registration graph.

## di/sub_providers/auth.py — 562 LOC

Rationale: Auth sub-provider. Registers auth-related services in a
single coherent unit. Accept as DI infrastructure.

## forms/builder.py — 515 LOC

Rationale: Form builder with Pydantic integration. Single responsibility
of building form schemas from models. Accept as focused module.

## forms/components.py — 512 LOC

Rationale: Form schema/component types. Coherent type definitions used
together. Accept as type module.

## lib/template/auth.py — 559 LOC

Rationale: Standalone auth template rendering. Self-contained module
with no internal collaborators to extract. Accept as leaf module.

Rationale: Tabular data view rendering. All methods serve the single
concern of rendering table rows/cells. The complexity is inherent to
the rendering logic. Accept as focused renderer.

Rationale: Admin shell template renderer. The render() method builds
the full page layout including sidebar, topbar, search overlay, and
HTMX scripts. This is a template file — the HTML/JS is inherently
verbose. Accept as template debt.
